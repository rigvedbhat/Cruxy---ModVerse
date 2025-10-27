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

    async def check_message_for_profanity(self, message: discord.Message) -> bool:
        """
        Handles profanity detection and applies moderation actions.
        Returns True if profanity was found and handled, False otherwise.
        """
        print(f"\n[DEBUG] Running profanity check for user: {message.author.name}")

        if message.author.guild_permissions.administrator:
            print("[DEBUG] User is an administrator. Skipping profanity check.")
            return False

        settings = await self.db.get_automod_settings(message.guild.id)
        print(f"[DEBUG] Fetched AutoMod settings: {settings}")
        
        if not settings.get("profanityFilter", False):
            print("[DEBUG] Profanity filter is disabled in settings. Skipping check.")
            return False

        contains_profanity = profanity.contains_profanity(message.content)
        print(f"[DEBUG] `better_profanity` check returned: {contains_profanity}")

        if contains_profanity:
            try:
                await message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass 

            guild_id = message.guild.id
            user_id = message.author.id
            
            new_warnings = await self.db.add_warning(guild_id, user_id)
            warning_limit = settings.get("warningLimit", 3)
            punishment_type = settings.get("limitAction", "kick").lower()

            await message.channel.send(
                f"⚠️ {message.author.mention}, watch your language! "
                f"You now have **{new_warnings}/{warning_limit}** warnings.",
                delete_after=15
            )

            if new_warnings >= warning_limit:
                try:
                    if punishment_type == "kick":
                        await message.author.kick(reason="Exceeded profanity warning limit")
                        await message.channel.send(f"👢 {message.author.mention} has been kicked for repeated profanity.")
                    elif punishment_type == "ban":
                        await message.guild.ban(message.author, reason="Exceeded profanity warning limit")
                        await message.channel.send(f"🔨 {message.author.mention} has been banned for repeated profanity.")
                    
                    await self.db.reset_warnings(guild_id, user_id)
                except discord.Forbidden:
                    await message.channel.send(f"❌ **Permissions Error:** I tried to punish {message.author.mention} but I don't have the required permissions.")
                except Exception as e:
                    await message.channel.send(f"An error occurred while applying punishment: {e}")
            
            print("[DEBUG] Profanity was handled.")
            return True # Profanity was handled
        
        print("[DEBUG] No profanity found.")
        return False # No profanity found

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