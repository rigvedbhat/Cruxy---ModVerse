import aiosqlite

class PersistentDB:
    def __init__(self, path="bot_data.db"):
        self.path = path
        self.conn = None

    async def connect(self):
        # The timeout parameter helps prevent 'database is locked' errors
        self.conn = await aiosqlite.connect(self.path, timeout=10)
        await self.conn.execute('PRAGMA foreign_keys = ON;')
        await self.conn.execute('PRAGMA journal_mode=WAL;') # Improves concurrency

        # --- Updated automod_settings schema ---
        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS automod_settings (
                guild_id INTEGER PRIMARY KEY,
                profanity_filter_enabled BOOLEAN DEFAULT 1,
                warning_limit INTEGER DEFAULT 3,
                punishment_type TEXT DEFAULT 'kick',
                mute_duration INTEGER DEFAULT 10
            )
        ''')

        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS warnings (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                count INTEGER DEFAULT 1,
                PRIMARY KEY (guild_id, user_id)
            )
        ''')

        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS user_data (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        ''')

        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS afk_users (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                message TEXT,
                PRIMARY KEY (guild_id, user_id)
            )
        ''')

        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS reaction_roles (
                message_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL
            )
        ''')

        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS reaction_role_mappings (
                message_id INTEGER NOT NULL,
                emoji TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                PRIMARY KEY (message_id, emoji),
                FOREIGN KEY (message_id) REFERENCES reaction_roles(message_id) ON DELETE CASCADE
            )
        ''')

        await self.conn.commit()

    async def close(self):
        if self.conn:
            await self.conn.close()

    # ---------- Warning System ----------
    async def add_warning(self, guild_id, user_id):
        await self.conn.execute(
            "INSERT INTO warnings (guild_id, user_id, count) VALUES (?, ?, 1) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET count = count + 1",
            (guild_id, user_id)
        )
        await self.conn.commit()

        async with self.conn.execute(
            "SELECT count FROM warnings WHERE guild_id=? AND user_id=?", (guild_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_warnings(self, guild_id, user_id):
        async with self.conn.execute(
            "SELECT count FROM warnings WHERE guild_id=? AND user_id=?", (guild_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def reset_warnings(self, guild_id, user_id):
        await self.conn.execute("DELETE FROM warnings WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        await self.conn.commit()

    # ---------- AutoMod Settings (Updated) ----------
    async def get_automod_settings(self, guild_id):
        async with self.conn.execute(
            "SELECT profanity_filter_enabled, warning_limit, punishment_type, mute_duration FROM automod_settings WHERE guild_id=?",
            (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "profanityFilter": bool(row[0]),
                    "warningLimit": row[1],
                    "limitAction": row[2],
                    "muteDuration": row[3]
                }
        # Return default settings if none are found
        return {
            "profanityFilter": True,
            "warningLimit": 3,
            "limitAction": 'kick',
            "muteDuration": 10
        }

    async def set_automod_settings(self, guild_id, profanity_filter, limit, punishment, mute_duration):
        await self.conn.execute(
            "INSERT OR REPLACE INTO automod_settings (guild_id, profanity_filter_enabled, warning_limit, punishment_type, mute_duration) VALUES (?, ?, ?, ?, ?)",
            (guild_id, profanity_filter, limit, punishment, mute_duration)
        )
        await self.conn.commit()


    # ---------- XP System ----------
    async def add_xp(self, guild_id, user_id, xp_to_add):
        await self.conn.execute(
            "INSERT OR IGNORE INTO user_data (guild_id, user_id, xp, level) VALUES (?, ?, 0, 0)",
            (guild_id, user_id)
        )
        await self.conn.execute(
            "UPDATE user_data SET xp = xp + ? WHERE guild_id = ? AND user_id = ?",
            (xp_to_add, guild_id, user_id)
        )

        async with self.conn.execute(
            "SELECT xp, level FROM user_data WHERE guild_id=? AND user_id=?", (guild_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            xp, level = row if row else (0, 0)

        required_xp = (level + 1) * 100
        if xp >= required_xp:
            new_level = level + 1
            new_xp = xp - required_xp
            await self.conn.execute(
                "UPDATE user_data SET level = ?, xp = ? WHERE guild_id = ? AND user_id = ?",
                (new_level, new_xp, guild_id, user_id)
            )
            await self.conn.commit()
            return new_level

        await self.conn.commit()
        return None

    async def get_xp_and_level(self, guild_id, user_id):
        async with self.conn.execute(
            "SELECT xp, level FROM user_data WHERE guild_id=? AND user_id=?", (guild_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            return (row[0], row[1]) if row else (0, 0)

    # ---------- AFK ----------
    async def set_afk(self, guild_id, user_id, message):
        await self.conn.execute(
            "INSERT OR REPLACE INTO afk_users (guild_id, user_id, message) VALUES (?, ?, ?)",
            (guild_id, user_id, message)
        )
        await self.conn.commit()

    async def remove_afk(self, guild_id, user_id):
        await self.conn.execute("DELETE FROM afk_users WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        await self.conn.commit()

    async def get_afk_user(self, guild_id, user_id):
        async with self.conn.execute(
            "SELECT message FROM afk_users WHERE guild_id=? AND user_id=?", (guild_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

    # ---------- Reaction Roles ----------
    async def add_reaction_role(self, message_id, guild_id, channel_id, emoji, role_id):
        await self.conn.execute(
            "INSERT OR IGNORE INTO reaction_roles (message_id, guild_id, channel_id) VALUES (?, ?, ?)",
            (message_id, guild_id, channel_id)
        )
        await self.conn.execute(
            "INSERT OR REPLACE INTO reaction_role_mappings (message_id, emoji, role_id) VALUES (?, ?, ?)",
            (message_id, emoji, role_id)
        )
        await self.conn.commit()

    async def get_reaction_role(self, message_id, emoji):
        async with self.conn.execute(
            "SELECT role_id FROM reaction_role_mappings WHERE message_id=? AND emoji=?",
            (message_id, str(emoji))
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

    async def get_all_reaction_roles(self):
        roles = {}
        query = "SELECT message_id, emoji, role_id FROM reaction_role_mappings"
        async with self.conn.execute(query) as cursor:
            async for message_id, emoji, role_id in cursor:
                if message_id not in roles:
                    roles[message_id] = {}
                roles[message_id][emoji] = role_id
        return roles
