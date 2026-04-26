import asyncio
import os
import signal
import sys
import threading

import discord
import google.generativeai as genai
from cachetools import LRUCache
from discord.ext import commands
from dotenv import load_dotenv
from waitress import serve as waitress_serve

from api_server import app, run_api_server
from database import PersistentDB
from utils.logger import log

load_dotenv()

FLASK_DEBUG = os.getenv("FLASK_ENV", "production") == "development"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")


def _get_env_int(name: str, default: int, minimum: int = 0) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        log.warning("Invalid integer for %s: %s. Falling back to %s.", name, raw_value, default)
        return default
    return max(minimum, parsed)


class SeromodBot(commands.Bot):
    async def setup_hook(self):
        await self.db.connect()

        initial_extensions = [
            "cogs.admin",
            "cogs.general",
            "cogs.events",
            "cogs.moderation",
            "cogs.ai_commands",
            "cogs.server_edit",
            "cogs.scheduled_tasks",
        ]

        for extension in initial_extensions:
            try:
                await self.load_extension(extension)
                log.info("Loaded extension: %s", extension)
            except Exception as e:
                log.error("Failed to load extension %s: %s", extension, e)

        if os.getenv("SYNC_COMMANDS", "false").lower() == "true":
            try:
                synced = await self.tree.sync()
                log.info("Synced %s command(s) globally.", len(synced))
            except Exception as e:
                log.error("Global sync failed: %s", e)
        else:
            log.info("Command sync skipped. Set SYNC_COMMANDS=true to sync.")

    async def close(self):
        try:
            await super().close()
        finally:
            if hasattr(self, "db"):
                await self.db.close()


def run_bot():
    token = os.getenv("DISCORD_TOKEN", "").strip()
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
    api_secret_key = os.getenv("API_SECRET_KEY", "").strip()
    database_url = os.getenv("DATABASE_URL", "").strip()

    missing = []
    if not token:
        missing.append("DISCORD_TOKEN")
    if not gemini_api_key:
        missing.append("GEMINI_API_KEY")
    if not api_secret_key:
        missing.append("API_SECRET_KEY")
    if not database_url:
        missing.append("DATABASE_URL")

    if missing:
        log.error(
            "Missing required environment variables: %s",
            ", ".join(missing),
        )
        sys.exit(1)

    genai.configure(api_key=gemini_api_key)
    log.info("Using Gemini model: %s", GEMINI_MODEL)

    intents = discord.Intents.default()
    intents.guilds = True
    intents.members = True
    intents.message_content = True
    intents.reactions = True

    bot = SeromodBot(command_prefix="!", intents=intents)
    bot.remove_command("help")
    bot.chats = LRUCache(maxsize=500)
    bot.reaction_role_mapping = {}
    bot.gemini_semaphore = asyncio.Semaphore(2)
    bot.dashboard_operations_in_progress = set()
    bot.guild_operation_locks = {}
    bot.db = PersistentDB()

    def _run_api():
        port = int(os.getenv("PORT", 5000))
        waitress_kwargs = {
            "host": "0.0.0.0",
            "port": port,
            "threads": _get_env_int("WAITRESS_THREADS", 4, minimum=1),
            "connection_limit": _get_env_int("WAITRESS_CONNECTION_LIMIT", 100, minimum=10),
            "channel_timeout": _get_env_int("WAITRESS_CHANNEL_TIMEOUT", 30, minimum=5),
            "cleanup_interval": _get_env_int("WAITRESS_CLEANUP_INTERVAL", 30, minimum=5),
            "max_request_body_size": 16 * 1024,
            "max_request_header_size": _get_env_int(
                "WAITRESS_MAX_REQUEST_HEADER_SIZE",
                16384,
                minimum=1024,
            ),
            "server_name": "seromod",
            "clear_untrusted_proxy_headers": True,
            "log_untrusted_proxy_headers": True,
        }
        trusted_proxy = os.getenv("TRUSTED_PROXY", "").strip()
        if trusted_proxy:
            waitress_kwargs.update(
                {
                    "trusted_proxy": trusted_proxy,
                    "trusted_proxy_count": _get_env_int("TRUST_PROXY_COUNT", 1, minimum=1),
                    "trusted_proxy_headers": "x-forwarded-for x-forwarded-proto x-forwarded-host x-forwarded-port",
                }
            )
        log.info("API server starting on port %s", port)
        waitress_serve(app, **waitress_kwargs)

    api_thread = threading.Thread(target=_run_api, daemon=True)

    run_api_server(bot)
    api_thread.start()
    log.info("API server thread started.")

    @bot.event
    async def on_ready():
        log.info("Bot is ready. Logged in as %s", bot.user)
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="over servers",
            )
        )

        for guild in bot.guilds:
            if not discord.utils.get(guild.text_channels, name="seromod-instructions"):
                try:
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(view_channel=False),
                        guild.me: discord.PermissionOverwrite(view_channel=True)
                    }
                    await guild.create_text_channel("seromod-instructions", overwrites=overwrites)
                except Exception as e:
                    log.warning("Could not create instructions channel in %s: %s", guild.name, e)

    @bot.event
    async def on_disconnect():
        log.warning("Disconnected from the Discord gateway.")

    @bot.event
    async def on_resumed():
        log.info("Discord gateway session resumed.")

    @bot.event
    async def on_message(message):
        if message.author.bot or not message.guild:
            return

        moderation_cog = bot.get_cog("Moderation")
        if moderation_cog and await moderation_cog.check_message_for_profanity(message):
            return

        ai_cog = bot.get_cog("AICommands")
        if ai_cog and await ai_cog.handle_bot_mention(message):
            return

        general_cog = bot.get_cog("General")
        if general_cog:
            await general_cog.handle_afk_and_xp(message)

        await bot.process_commands(message)

    def _shutdown_handler(signum, frame):
        log.info("Shutdown signal received. Closing bot...")
        bot.loop.create_task(bot.close())

    signal.signal(signal.SIGTERM, _shutdown_handler)
    signal.signal(signal.SIGINT, _shutdown_handler)

    bot.run(token)


if __name__ == "__main__":
    run_bot()
