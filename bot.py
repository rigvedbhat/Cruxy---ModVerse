# bot.py
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import json
import re
import aiosqlite
import random
from datetime import datetime, timedelta, timezone
from globals import afk_users, user_xp, user_levels, LEVELS_FILE

# --- Import the Gemini Library ---
import google.generativeai as genai

# Load token and key from .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Initialize the Gemini AI model ---
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not found in .env file. AI chat functionality will be disabled.")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# Define intents
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.reactions = True
intents.message_content = True

# --- CORRECTED: Create the bot object BEFORE adding attributes to it ---
bot = commands.Bot(command_prefix="!", intents=intents)

# This dictionary will now be attached to the bot object for the new AI cog to access.
bot.chats = {}

# Attach global variables/data structures to the bot object
bot.LEVELS_FILE = 'levels.json'
bot.user_xp = {}
bot.user_levels = {}
bot.afk_users = {}
# --- NEW: Add a list to keep track of AI-related keywords ---


# Global constants for Admin cog
bot.REQUIRED_ROLES = ["Administrator", "Member"]
bot.MODERATOR_PERMISSIONS = [
    "kick_members", "ban_members", "manage_messages", "manage_channels",
    "manage_roles", "administrator", "view_audit_log"
]
bot.reaction_role_messages = {}
bot.reaction_role_mapping = {}

# --- WarningDB Class (UPDATED TO BE ASYNC) ---
class WarningDB:
    def __init__(self, path="warnings.db"):
        self.path = path
        self.conn = None # Connection will be established asynchronously

    async def connect(self): # <--- ASYNC CONNECT METHOD
        self.conn = await aiosqlite.connect(self.path)
        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS warnings (
                guild_id INTEGER,
                user_id INTEGER,
                count INTEGER,
                PRIMARY KEY (guild_id, user_id)
            )
        ''')
        await self.conn.commit()

    async def close(self): # <--- ASYNC CLOSE METHOD (Good practice for cleanup)
        if self.conn:
            await self.conn.close()

    async def get_warnings(self, guild_id, user_id): # <--- ASYNC METHODS
        async with self.conn.execute("SELECT count FROM warnings WHERE guild_id=? AND user_id=?", (guild_id, user_id)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def add_warning(self, guild_id, user_id): # <--- ASYNC METHODS
        count = await self.get_warnings(guild_id, user_id)
        if count:
            await self.conn.execute("UPDATE warnings SET count=? WHERE guild_id=? AND user_id=?", (count + 1, guild_id, user_id))
        else:
            await self.conn.execute("INSERT INTO warnings VALUES (?, ?, 1)", (guild_id, user_id))
        await self.conn.commit()

    async def reset_warnings(self, guild_id, user_id): # <--- ASYNC METHODS
        await self.conn.execute("DELETE FROM warnings WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        await self.conn.commit()

# --- Profanity Configuration ---
# This is now handled by the moderation cog using the `profanity-check` library.
bot.PROFANITY_WORDS = [] # No longer needed, but keeping the list avoids errors for now.

# --- XP Leveling Functions ---
def get_level(xp):
    level = 0
    required_xp = 100
    while xp >= required_xp:
        level += 1
        required_xp = 100 * (level + 1)
    return level

async def add_xp(message):
    if message.author.bot:
        return
    print(f"Adding XP for user {message.author} in guild {message.guild}")

    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    if guild_id not in bot.user_xp:
        bot.user_xp[guild_id] = {}
        bot.user_levels[guild_id] = {}

    if user_id not in bot.user_xp[guild_id]:
        bot.user_xp[guild_id][user_id] = 0
        bot.user_levels[guild_id][user_id] = 0

    gained_xp = random.randint(5, 15)
    bot.user_xp[guild_id][user_id] += gained_xp

    current_level = bot.user_levels[guild_id][user_id]
    new_level = get_level(bot.user_xp[guild_id][user_id])

    if new_level > current_level:
        bot.user_levels[guild_id][user_id] = new_level
        await message.channel.send(
            f"🎉 {message.author.mention}, you leveled up to **Level {new_level}**! Keep it up! 🚀"
        )
# --- End XP Leveling Functions ---

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # --- AFK Logic (remains here as it's a core bot event) ---
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    if guild_id in bot.afk_users and user_id in bot.afk_users[guild_id]:
        bot.afk_users[guild_id].pop(user_id)
        try:
            await message.channel.send(f"👋 Welcome back, {message.author.mention}! I've removed your AFK status.")
        except discord.Forbidden:
            pass

    if guild_id in bot.afk_users:
        for user in message.mentions:
            mentioned_id = str(user.id)
            if mentioned_id in bot.afk_users[guild_id]:
                afk_msg = bot.afk_users[guild_id][mentioned_id]
                await message.channel.send(f"⚠️ {user.display_name} is currently AFK: {afk_msg}")

    await add_xp(message)
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"Bot is ready. Logged in as {bot.user}")

    # Load levels once at startup
    if os.path.exists(bot.LEVELS_FILE):
        try:
            with open(bot.LEVELS_FILE, 'r') as f:
                data = json.load(f)
                bot.user_xp.update(data.get('user_xp', {}))
                bot.user_levels.update(data.get('user_levels', {}))
            print("Loaded user XP and levels from file.")
        except Exception as e:
            print(f"Failed to load levels file: {e}")
    else:
        print("No existing levels file found, starting fresh.")


    # Load cogs
    initial_extensions = [
        'cogs.admin',
        'cogs.general',
        'cogs.events',
        'cogs.scheduled_tasks',
        'cogs.moderation',
        # --- NEW: Load the new AI cog ---
        'cogs.ai_commands'
    ]
    for extension in initial_extensions:
        print(f"Attempting to load extension: {extension}")
        try:
            await bot.load_extension(extension)
            print(f"Loaded extension: {extension}")
        except Exception as e:
            print(f"Failed to load extension {extension}: {e}")

    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} command(s) globally.")
    except Exception as e:
        print(f"❌ Global sync failed: {e}")

# --- NEW: Add a manual sync command for convenience ---
@commands.command(name="sync", description="Manually sync application commands.")
@commands.is_owner()
async def sync(ctx):
    try:
        await ctx.bot.tree.sync()
        await ctx.send("✅ Application commands have been synced!")
    except Exception as e:
        await ctx.send(f"❌ Failed to sync commands: {e}")

# Add the sync command to the bot
bot.add_command(sync)

bot.run(TOKEN)