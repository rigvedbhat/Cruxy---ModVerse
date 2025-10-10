# cogs/moderation.py
import discord
from discord.ext import commands
import re
import aiosqlite
from database import PersistentDB

# --- CORRECTED: Import the new profanity library ---
from better_profanity import profanity

# Import global variables/classes from bot.py
from globals import PROFANITY_WORDS

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = PersistentDB()

    async def cog_load(self):
        """Called when the cog is loaded."""
        await self.db.connect()
        print("Moderation DB connected.")
        
        # --- NEW: Load the default profanity list from the library ---
        profanity.load_censor_words()


    async def cog_unload(self):
        """Called when the cog is unloaded."""
        await self.db.close()
        print("Moderation DB closed.")

    # --- UPDATED: Use the better-profanity library to detect profanity ---
    async def is_profane(self, text: str) -> bool:
        """
        Checks if the given text contains any profanity using the better-profanity library.
        """
        if not text.strip():
            return False
        
        return profanity.contains_profanity(text)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Handles profanity detection and warnings for every message.
        """
        if message.author.bot:
            return

        content = message.content
        user_id = message.author.id
        guild_id = message.guild.id

        if await self.is_profane(content):
            warnings = await self.db.get_warnings(guild_id, user_id)

            if warnings >= 2:
                try:
                    await message.guild.kick(message.author, reason="Too many warnings for profanity.")
                    await self.db.reset_warnings(guild_id, user_id)
                    await message.channel.send(f"{message.author.mention} has been kicked for repeated profanity.")
                except discord.Forbidden:
                    await message.channel.send(f"⚠️ I don't have permission to kick {message.author.mention}.")
                except Exception as e:
                    print(f"Error kicking user {message.author}: {e}")
                    await message.channel.send(f"An unexpected error occurred while trying to kick {message.author.mention}.")
            else:
                await self.db.add_warning(guild_id, user_id)
                await message.channel.send(f"{message.author.mention}, watch your language. Warning {warnings + 1}/3. Repeated offenses may lead to a kick.")

            try:
                await message.delete()
            except discord.Forbidden:
                await message.channel.send(f"⚠️ I don't have permission to delete messages.")
            except Exception as e:
                print(f"Error deleting message: {e}")

    @commands.command(name="warnings", description="Check a user's warnings.")
    @commands.has_permissions(kick_members=True)
    async def get_user_warnings(self, ctx: commands.Context, member: discord.Member):
        guild_id = ctx.guild.id
        user_id = member.id
        warnings = await self.db.get_warnings(guild_id, user_id)
        await ctx.send(f"{member.display_name} has {warnings} warning(s).")

    @commands.command(name="resetwarnings", description="Reset a user's warnings.")
    @commands.has_permissions(kick_members=True)
    async def reset_user_warnings(self, ctx: commands.Context, member: discord.Member):
        guild_id = ctx.guild.id
        user_id = member.id
        await self.db.reset_warnings(guild_id, user_id)
        await ctx.send(f"Warnings for {member.display_name} have been reset.")

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))