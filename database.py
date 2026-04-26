import json
import logging
import os
import time
from typing import Optional

import asyncpg

from utils.cache import cache_del, cache_get, cache_set

log = logging.getLogger(__name__)

_SUBSCRIPTION_TIER_TTL_SECONDS = 60
_subscription_tier_cache: dict[int, tuple[float, str]] = {}


class PersistentDB:
    def __init__(self, path="bot_data.db"):
        self.path = path
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        if self.pool is not None:
            try:
                async with self.pool.acquire() as conn:
                    await conn.execute("SELECT 1")
                return
            except Exception:
                log.warning("Existing PostgreSQL pool is unhealthy. Reconnecting...")
                await self.close()

        database_url = os.getenv("DATABASE_URL", "").strip()
        if not database_url and str(self.path).startswith(("postgresql://", "postgres://")):
            database_url = str(self.path)
        if not database_url:
            raise RuntimeError("DATABASE_URL is required for PostgreSQL.")

        self.pool = await asyncpg.create_pool(
            dsn=database_url,
            min_size=2,
            max_size=10,
            command_timeout=10,
        )

        try:
            async with self.pool.acquire() as conn:
                await self._initialize_schema(conn)
        except Exception:
            await self.close()
            raise

    async def _initialize_schema(self, conn: asyncpg.Connection):
        schema_statements = [
            """
            CREATE TABLE IF NOT EXISTS _migrations (
                name TEXT PRIMARY KEY,
                applied_at BIGINT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS automod_settings (
                guild_id BIGINT PRIMARY KEY,
                profanity_filter_enabled BOOLEAN DEFAULT TRUE,
                warning_limit INTEGER DEFAULT 3,
                punishment_type TEXT DEFAULT 'kick'
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS warnings (
                guild_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                count INTEGER DEFAULT 1,
                PRIMARY KEY (guild_id, user_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS user_data (
                guild_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS afk_users (
                guild_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                message TEXT,
                PRIMARY KEY (guild_id, user_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS reaction_roles (
                message_id BIGINT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS reaction_role_mappings (
                message_id BIGINT NOT NULL,
                emoji TEXT NOT NULL,
                role_id BIGINT NOT NULL,
                PRIMARY KEY (message_id, emoji),
                FOREIGN KEY (message_id) REFERENCES reaction_roles(message_id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS scheduled_events (
                id BIGSERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                event_name TEXT NOT NULL,
                description TEXT,
                event_time BIGINT NOT NULL,
                reminder_time BIGINT NOT NULL,
                ping_role_id BIGINT,
                reminder_sent BOOLEAN DEFAULT FALSE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                guild_id BIGINT PRIMARY KEY,
                tier TEXT NOT NULL DEFAULT 'free',
                stripe_subscription_id TEXT,
                expires_at BIGINT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS build_jobs (
                id TEXT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                result_message TEXT,
                created_at BIGINT NOT NULL,
                updated_at BIGINT NOT NULL
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_warnings_guild_user
            ON warnings(guild_id, user_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_user_data_guild_user
            ON user_data(guild_id, user_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_scheduled_events_reminder
            ON scheduled_events(reminder_time, reminder_sent)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_automod_guild
            ON automod_settings(guild_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_build_jobs_guild
            ON build_jobs(guild_id)
            """,
        ]

        async with conn.transaction():
            for statement in schema_statements:
                await conn.execute(statement)

            await self._run_migration(
                conn,
                "add_automod_settings_punishment_type",
                "ALTER TABLE automod_settings "
                "ADD COLUMN IF NOT EXISTS punishment_type TEXT DEFAULT 'kick'",
            )

    async def _run_migration(
        self,
        conn: asyncpg.Connection,
        name: str,
        statement: str,
    ):
        exists = await conn.fetchval(
            "SELECT 1 FROM _migrations WHERE name = $1",
            name,
        )
        if exists:
            return

        await conn.execute(statement)
        await conn.execute(
            "INSERT INTO _migrations (name, applied_at) VALUES ($1, $2)",
            name,
            int(time.time()),
        )

    async def _ensure_connected(self):
        if self.pool is None:
            await self.connect()
            return
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
        except Exception:
            log.warning("PostgreSQL pool check failed. Reconnecting...")
            await self.close()
            await self.connect()

    async def close(self):
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    async def add_warning(self, guild_id, user_id):
        await self._ensure_connected()
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO warnings (guild_id, user_id, count)
                    VALUES ($1, $2, 1)
                    ON CONFLICT (guild_id, user_id)
                    DO UPDATE SET count = warnings.count + 1
                    """,
                    guild_id,
                    user_id,
                )
                return await conn.fetchval(
                    "SELECT count FROM warnings WHERE guild_id = $1 AND user_id = $2",
                    guild_id,
                    user_id,
                ) or 0

    async def get_warnings(self, guild_id, user_id):
        await self._ensure_connected()
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT count FROM warnings WHERE guild_id = $1 AND user_id = $2",
                guild_id,
                user_id,
            ) or 0

    async def reset_warnings(self, guild_id, user_id):
        await self._ensure_connected()
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM warnings WHERE guild_id = $1 AND user_id = $2",
                guild_id,
                user_id,
            )

    async def get_automod_settings(self, guild_id):
        await self._ensure_connected()
        cache_key = f"automod:{guild_id}"
        cached = cache_get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                pass

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT profanity_filter_enabled, warning_limit, punishment_type
                FROM automod_settings
                WHERE guild_id = $1
                """,
                guild_id,
            )

        settings = (
            {
                "profanityFilter": bool(row["profanity_filter_enabled"]),
                "warningLimit": row["warning_limit"],
                "limitAction": row["punishment_type"],
            }
            if row
            else {
                "profanityFilter": True,
                "warningLimit": 3,
                "limitAction": "kick",
            }
        )
        cache_set(cache_key, json.dumps(settings), ex=60)
        return settings

    async def set_automod_settings(self, guild_id, profanity_filter, limit, punishment):
        await self._ensure_connected()
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO automod_settings (
                    guild_id,
                    profanity_filter_enabled,
                    warning_limit,
                    punishment_type
                )
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (guild_id)
                DO UPDATE SET
                    profanity_filter_enabled = EXCLUDED.profanity_filter_enabled,
                    warning_limit = EXCLUDED.warning_limit,
                    punishment_type = EXCLUDED.punishment_type
                """,
                guild_id,
                bool(profanity_filter),
                int(limit),
                str(punishment),
            )
        cache_del(f"automod:{guild_id}")

    async def add_xp(self, guild_id, user_id, xp_to_add):
        await self._ensure_connected()
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO user_data (guild_id, user_id, xp, level)
                    VALUES ($1, $2, 0, 0)
                    ON CONFLICT (guild_id, user_id) DO NOTHING
                    """,
                    guild_id,
                    user_id,
                )
                await conn.execute(
                    """
                    UPDATE user_data
                    SET xp = xp + $1
                    WHERE guild_id = $2 AND user_id = $3
                    """,
                    xp_to_add,
                    guild_id,
                    user_id,
                )

                row = await conn.fetchrow(
                    "SELECT xp, level FROM user_data WHERE guild_id = $1 AND user_id = $2",
                    guild_id,
                    user_id,
                )
                xp, level = (row["xp"], row["level"]) if row else (0, 0)

                required_xp = (level + 1) * 100
                if xp >= required_xp:
                    new_level = level + 1
                    new_xp = xp - required_xp
                    await conn.execute(
                        """
                        UPDATE user_data
                        SET level = $1, xp = $2
                        WHERE guild_id = $3 AND user_id = $4
                        """,
                        new_level,
                        new_xp,
                        guild_id,
                        user_id,
                    )
                    return new_level
                return None

    async def get_xp_and_level(self, guild_id, user_id):
        await self._ensure_connected()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT xp, level FROM user_data WHERE guild_id = $1 AND user_id = $2",
                guild_id,
                user_id,
            )
            return (row["xp"], row["level"]) if row else (0, 0)

    async def set_afk(self, guild_id, user_id, message):
        await self._ensure_connected()
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO afk_users (guild_id, user_id, message)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id, user_id)
                DO UPDATE SET message = EXCLUDED.message
                """,
                guild_id,
                user_id,
                message,
            )

    async def remove_afk(self, guild_id, user_id):
        await self._ensure_connected()
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM afk_users WHERE guild_id = $1 AND user_id = $2",
                guild_id,
                user_id,
            )

    async def get_afk_user(self, guild_id, user_id):
        await self._ensure_connected()
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT message FROM afk_users WHERE guild_id = $1 AND user_id = $2",
                guild_id,
                user_id,
            )

    async def add_reaction_role(self, message_id, guild_id, channel_id, emoji, role_id):
        await self._ensure_connected()
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO reaction_roles (message_id, guild_id, channel_id)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (message_id) DO NOTHING
                    """,
                    message_id,
                    guild_id,
                    channel_id,
                )
                await conn.execute(
                    """
                    INSERT INTO reaction_role_mappings (message_id, emoji, role_id)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (message_id, emoji)
                    DO UPDATE SET role_id = EXCLUDED.role_id
                    """,
                    message_id,
                    str(emoji),
                    role_id,
                )

    async def get_reaction_role(self, message_id, emoji):
        await self._ensure_connected()
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT role_id
                FROM reaction_role_mappings
                WHERE message_id = $1 AND emoji = $2
                """,
                message_id,
                str(emoji),
            )

    async def get_all_reaction_roles(self):
        await self._ensure_connected()
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT message_id, emoji, role_id FROM reaction_role_mappings"
            )

        roles = {}
        for row in rows:
            message_id = row["message_id"]
            if message_id not in roles:
                roles[message_id] = {}
            roles[message_id][row["emoji"]] = row["role_id"]
        return roles

    async def add_event(
        self,
        guild_id,
        channel_id,
        name,
        description,
        event_ts,
        reminder_ts,
        ping_role_id=None,
    ):
        await self._ensure_connected()
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO scheduled_events (
                    guild_id,
                    channel_id,
                    event_name,
                    description,
                    event_time,
                    reminder_time,
                    ping_role_id
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                guild_id,
                channel_id,
                name,
                description,
                int(event_ts),
                int(reminder_ts),
                ping_role_id,
            )

    async def get_active_event_count(self, guild_id: int) -> int:
        await self._ensure_connected()
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM scheduled_events
                WHERE guild_id = $1 AND reminder_sent = FALSE
                """,
                guild_id,
            ) or 0

    async def get_pending_reminders(self, now_ts):
        await self._ensure_connected()
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, guild_id, channel_id, event_name, description, event_time, ping_role_id
                FROM scheduled_events
                WHERE reminder_time <= $1 AND reminder_sent = FALSE
                ORDER BY reminder_time ASC
                """,
                int(now_ts),
            )
        return [
            (
                row["id"],
                row["guild_id"],
                row["channel_id"],
                row["event_name"],
                row["description"],
                row["event_time"],
                row["ping_role_id"],
            )
            for row in rows
        ]

    async def mark_reminder_sent(self, event_id):
        await self._ensure_connected()
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE scheduled_events SET reminder_sent = TRUE WHERE id = $1",
                event_id,
            )

    async def get_subscription_tier(self, guild_id: int) -> str:
        now = time.monotonic()
        cached = _subscription_tier_cache.get(guild_id)
        if cached and cached[0] > now:
            return cached[1]

        cache_key = f"sub:{guild_id}"
        cached_tier = cache_get(cache_key)
        if isinstance(cached_tier, str) and cached_tier:
            _subscription_tier_cache[guild_id] = (
                now + _SUBSCRIPTION_TIER_TTL_SECONDS,
                cached_tier,
            )
            return cached_tier

        await self._ensure_connected()
        async with self.pool.acquire() as conn:
            tier = await conn.fetchval(
                "SELECT tier FROM subscriptions WHERE guild_id = $1",
                guild_id,
            )

        resolved_tier = tier or "free"
        _subscription_tier_cache[guild_id] = (
            now + _SUBSCRIPTION_TIER_TTL_SECONDS,
            resolved_tier,
        )
        cache_set(cache_key, resolved_tier, ex=60)
        return resolved_tier

    async def get_guild_members(self, guild_id: int) -> list[dict]:
        await self._ensure_connected()
        return []

    async def create_build_job(
        self,
        job_id: str,
        guild_id: int,
        status: str = "pending",
        result_message: Optional[str] = None,
    ):
        await self._ensure_connected()
        now = int(time.time())
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO build_jobs (id, guild_id, status, result_message, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $5)
                """,
                job_id,
                guild_id,
                status,
                result_message,
                now,
            )

    async def update_build_job(
        self,
        job_id: str,
        status: str,
        result_message: Optional[str] = None,
    ):
        await self._ensure_connected()
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE build_jobs
                SET status = $2, result_message = $3, updated_at = $4
                WHERE id = $1
                """,
                job_id,
                status,
                result_message,
                int(time.time()),
            )

    async def get_build_job(self, job_id: str):
        await self._ensure_connected()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, guild_id, status, result_message, created_at, updated_at
                FROM build_jobs
                WHERE id = $1
                """,
                job_id,
            )
        return dict(row) if row else None
