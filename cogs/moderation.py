import discord
from discord.ext import commands
from discord import app_commands
from database import PersistentDB
from better_profanity import profanity
import asyncio

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = PersistentDB()
        profanity.load_censor_words()

    async def cog_load(self):
        """Connect to the database when the cog loads."""
        await self.db.connect()
        print("Moderation cog connected to the database.")

    async def cog_unload(self):
        """Close the database connection when the cog unloads."""
        await self.db.close()
        print("Moderation cog disconnected from the database.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handles profanity detection and applies moderation actions."""
        # Skip bots, DMs, and admins
        if message.author.bot or not message.guild or message.author.guild_permissions.administrator:
            return

        settings = await self.db.get_automod_settings(message.guild.id)
        
        # Check if profanity filter is enabled
        if not settings.get("profanityFilter", False):
            return

        # Check for profanity
        if profanity.contains_profanity(message.content):
            try:
                await message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass 

            guild_id = message.guild.id
            user_id = message.author.id
            
            # Add warning and get new count
            new_warnings = await self.db.add_warning(guild_id, user_id)
            warning_limit = settings.get("warningLimit", 3)
            punishment_type = settings.get("limitAction", "kick").lower()

            await message.channel.send(
                f"⚠️ {message.author.mention}, watch your language! "
                f"You now have **{new_warnings}/{warning_limit}** warnings."
            , delete_after=15)

            # Apply punishment if limit reached
            if new_warnings >= warning_limit:
                try:
                    if punishment_type == "kick":
                        await message.author.kick(reason="Exceeded profanity warning limit")
                        await message.channel.send(f"👢 {message.author.mention} has been kicked for repeated profanity.")
                    
                    elif punishment_type == "ban":
                        await message.guild.ban(message.author, reason="Exceeded profanity warning limit")
                        await message.channel.send(f"🔨 {message.author.mention} has been banned for repeated profanity.")

                    # Only reset warnings AFTER a successful punishment
                    await self.db.reset_warnings(guild_id, user_id)

                except discord.Forbidden:
                    await message.channel.send(f"❌ **Permissions Error:** I tried to punish {message.author.mention} but I don't have the required permissions. Please check my role hierarchy and permissions.")
                except Exception as e:
                    await message.channel.send(f"An error occurred while applying punishment: {e}")

    # ---------- Text Commands for manual moderation ----------
    @commands.command(name="warnings")
    @commands.has_permissions(kick_members=True)
    async def check_warnings(self, ctx, member: discord.Member):
        """Check the number of warnings for a specific member."""
        count = await self.db.get_warnings(ctx.guild.id, member.id)
        await ctx.send(f"{member.display_name} has **{count} warning(s)**.")

    @commands.command(name="resetwarnings")
    @commands.has_permissions(kick_members=True)
    async def reset_warnings(self, ctx, member: discord.Member):
        """Reset the warnings for a specific member."""
        await self.db.reset_warnings(ctx.guild.id, member.id)
        await ctx.send(f"✅ Warnings for {member.display_name} have been reset.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))