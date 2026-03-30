import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)


class ScheduledTasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.check_reminders.start()

    def cog_unload(self):
        self.check_reminders.cancel()

    @tasks.loop(seconds=60)
    async def check_reminders(self):
        now = datetime.now(timezone.utc).timestamp()
        pending = await self.bot.db.get_pending_reminders(now)
        for row in pending:
            event_id, guild_id, channel_id, name, desc, event_ts, role_id = row
            channel = self.bot.get_channel(channel_id)
            if not channel:
                continue

            ping = f"<@&{role_id}>" if role_id else ""
            embed = discord.Embed(
                title=f"Reminder: {name}",
                description=desc,
                color=discord.Color.gold(),
            )
            try:
                await channel.send(content=ping, embed=embed)
            except Exception as e:
                log.warning("Failed to send reminder for event %s: %s", event_id, e)
            await self.bot.db.mark_reminder_sent(event_id)

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(ScheduledTasks(bot))
