import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import google.generativeai as genai
from api_server import app, run_api_server  # Import both app and the function
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
    intents.guilds = True  # Explicitly enable guilds intent
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

    # --- Start API Server in a separate thread ---
    api_thread = threading.Thread(target=app.run, kwargs={'debug': True, 'use_reloader': False, 'port': 5000})
    api_thread.daemon = True
    
    @bot.listen()
    async def on_ready_for_api():
        # A simple event to signal that the bot is ready before starting the API
        if not api_thread.is_alive():
            run_api_server(bot) # Attach bot object to the app
            api_thread.start()
            print("API server thread started.")

    # We need to manually add this listener for on_ready_for_api
    bot.add_listener(on_ready_for_api, 'on_ready')

    bot.run(TOKEN)

if __name__ == '__main__':
    run_bot()

