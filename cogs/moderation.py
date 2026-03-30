import logging

import discord
from better_profanity import profanity
from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db
        profanity.load_censor_words()

    async def check_message_for_profanity(self, message: discord.Message) -> bool:
        log.debug("Running profanity check for user: %s", message.author.name)

        if message.author.guild_permissions.administrator:
            log.debug("User is an administrator. Skipping profanity check.")
            return False

        settings = await self.db.get_automod_settings(message.guild.id)
        log.debug("Fetched AutoMod settings: %s", settings)

        if not settings.get("profanityFilter", False):
            log.debug("Profanity filter is disabled in settings. Skipping check.")
            return False

        contains_profanity = profanity.contains_profanity(message.content)
        log.debug("better_profanity returned: %s", contains_profanity)

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
                f"{message.author.mention}, watch your language! "
                f"You now have **{new_warnings}/{warning_limit}** warnings.",
                delete_after=15,
            )

            if new_warnings >= warning_limit:
                try:
                    if punishment_type == "kick":
                        await message.author.kick(reason="Exceeded profanity warning limit")
                        await message.channel.send(
                            f"{message.author.mention} has been kicked for repeated profanity."
                        )
                    elif punishment_type == "ban":
                        await message.guild.ban(
                            message.author,
                            reason="Exceeded profanity warning limit",
                        )
                        await message.channel.send(
                            f"{message.author.mention} has been banned for repeated profanity."
                        )

                    await self.db.reset_warnings(guild_id, user_id)
                except discord.Forbidden:
                    await message.channel.send(
                        "Permissions error: I tried to punish "
                        f"{message.author.mention} but I don't have the required permissions."
                    )
                except Exception as e:
                    await message.channel.send(f"An error occurred while applying punishment: {e}")

            log.debug("Profanity was handled.")
            return True

        log.debug("No profanity found.")
        return False

    @commands.command(name="warnings")
    @commands.has_permissions(kick_members=True)
    async def check_warnings(self, ctx, member: discord.Member):
        count = await self.db.get_warnings(ctx.guild.id, member.id)
        await ctx.send(f"{member.display_name} has **{count} warning(s)**.")

    @commands.command(name="resetwarnings")
    @commands.has_permissions(kick_members=True)
    async def reset_warnings(self, ctx, member: discord.Member):
        await self.db.reset_warnings(ctx.guild.id, member.id)
        await ctx.send(f"Warnings for {member.display_name} have been reset.")


async def setup(bot):
    await bot.add_cog(Moderation(bot))
