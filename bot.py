import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import google.generativeai as genai
from api_server import app, run_api_server
import threading

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
    intents.guilds = True
    intents.members = True
    intents.message_content = True
    intents.reactions = True

    bot = commands.Bot(command_prefix="!", intents=intents)
    
    bot.remove_command('help')

    bot.chats = {}
    bot.reaction_role_mapping = {}

    @bot.event
    async def on_ready():
        print(f"Bot is ready. Logged in as {bot.user}")
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="over servers"))

        initial_extensions = [
            'cogs.admin', 'cogs.general', 'cogs.events', 
            'cogs.moderation', 'cogs.ai_commands', 'cogs.server_edit'
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

    @bot.event
    async def on_message(message):
        if message.author.bot or not message.guild:
            return

        # --- MODERATION ---
        # Run profanity check first. If it returns True, it means the message was deleted.
        moderation_cog = bot.get_cog('Moderation')
        if moderation_cog:
            if await moderation_cog.check_message_for_profanity(message):
                return # Stop processing if message is profane

        # --- AI CHAT ---
        # Check if the bot was mentioned. If so, handle the chat and stop processing.
        ai_cog = bot.get_cog('AICommands')
        if ai_cog:
            if await ai_cog.handle_bot_mention(message):
                return # Stop processing if it was an AI chat interaction

        # --- GENERAL ---
        # Handle AFK status and XP gain
        general_cog = bot.get_cog('General')
        if general_cog:
            await general_cog.handle_afk_and_xp(message)

        # Allow processing of traditional commands like !help
        await bot.process_commands(message)

    # --- Start API Server in a separate thread ---
    api_thread = threading.Thread(target=app.run, kwargs={'debug': True, 'use_reloader': False, 'port': 5000})
    api_thread.daemon = True
    
    @bot.listen()
    async def on_ready_for_api():
        if not api_thread.is_alive():
            run_api_server(bot)
            api_thread.start()
            print("API server thread started.")

    bot.add_listener(on_ready_for_api, 'on_ready')

    bot.run(TOKEN)

if __name__ == '__main__':
    run_bot()