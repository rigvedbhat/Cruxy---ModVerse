import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import google.generativeai as genai

def run_bot():
    # --- Configuration ---
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    if not TOKEN or not GEMINI_API_KEY:
        print("ERROR: DISCORD_TOKEN and GEMINI_API_KEY must be set in the .env file.")
        return

    genai.configure(api_key=GEMINI_API_KEY)

    # --- Bot Setup ---
    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True
    intents.reactions = True

    bot = commands.Bot(command_prefix="!", intents=intents)
    
    # --- Remove the default help command ---
    bot.remove_command('help')

    # --- Attach data structures for runtime caching ---
    bot.chats = {}
    # Reaction role mapping will now be loaded from the DB into this cache on startup
    bot.reaction_role_mapping = {}

    # --- Global constants for Admin cog ---
    bot.REQUIRED_ROLES = ["Administrator", "Member"]
    bot.MODERATOR_PERMISSIONS = [
        "kick_members", "ban_members", "manage_messages", "manage_channels",
        "manage_roles", "administrator", "view_audit_log"
    ]

    @bot.event
    async def on_ready():
        print(f"Bot is ready. Logged in as {bot.user}")
        
        # Set the bot's presence
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="over servers"))

        # Load cogs
        initial_extensions = [
            'cogs.admin',
            'cogs.general',
            'cogs.events',
            'cogs.moderation',
            'cogs.ai_commands',
            'cogs.server_edit'  # <-- CHANGE: Added the new server_edit cog
        ]
        for extension in initial_extensions:
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

    @commands.command(name="sync", description="Manually sync application commands.")
    @commands.is_owner()
    async def sync(ctx):
        try:
            await ctx.bot.tree.sync()
            await ctx.send("✅ Application commands have been synced!")
        except Exception as e:
            await ctx.send(f"❌ Failed to sync commands: {e}")
    
    bot.add_command(sync)
    
    bot.run(TOKEN)

if __name__ == '__main__':
    run_bot()
