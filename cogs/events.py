# cogs/events.py
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta, timezone
import asyncio

class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="event", description="Schedule an upcoming event.")
    @app_commands.describe(
        name="Name of the event",
        date="Date of the event (YYYY-MM-DD)",
        time="Time of the event (HH:MM in 24hr format)",
        description="Short description of the event",
        reminder_minutes="How many minutes before to send reminder?",
        ping_role="Role to ping (optional)"
    )
    async def schedule_event(
        self,
        interaction: discord.Interaction,
        name: str,
        date: str,
        time: str,
        description: str,
        reminder_minutes: int = 15,
        ping_role: discord.Role = None
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            guild = interaction.guild
            event_channel = None
            for category in guild.categories:
                if "announcement" in category.name.lower():
                    for channel in category.text_channels:
                        if channel.name.lower() == "events":
                            event_channel = channel
                            break
                    if event_channel:
                        break

            if not event_channel:
                event_channel = interaction.channel
                await interaction.followup.send("⚠️ Couldn't find a dedicated 'events' channel. Scheduling in this channel instead.", ephemeral=True)

            event_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
            event_datetime = event_datetime.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)

            if event_datetime <= now:
                await interaction.followup.send("⚠️ The event time must be in the future!")
                return

            reminder_time = event_datetime - timedelta(minutes=reminder_minutes)
            if reminder_time <= now:
                await interaction.followup.send("⚠️ The reminder time must also be in the future! Please set a lower reminder time.")
                return

            embed = discord.Embed(
                title=f"📅 Upcoming Event: {name}",
                description=description,
                color=discord.Color.blue()
            )
            embed.add_field(name="🕒 When", value=f"<t:{int(event_datetime.timestamp())}:F>", inline=False)
            embed.add_field(name="🔔 Reminder", value=f"{reminder_minutes} minutes before", inline=True)
            embed.set_footer(text=f"Scheduled by {interaction.user.name}")

            ping = ping_role.mention if ping_role else ""
            
            await event_channel.send(content=ping, embed=embed)
            await interaction.followup.send("✅ Event scheduled!")

            async def send_reminder():
                # Correctly calculate sleep duration
                sleep_duration = (reminder_time - datetime.now(timezone.utc)).total_seconds()
                
                # If the bot was offline and missed the reminder, don't try to sleep
                if sleep_duration > 0:
                    await asyncio.sleep(sleep_duration)
                    reminder_embed = discord.Embed(
                        title=f"🔔 Reminder: {name}",
                        description=f"{description}\nThis event is happening now!",
                        color=discord.Color.gold()
                    )
                    await event_channel.send(content=ping, embed=reminder_embed)
                else:
                    print(f"Reminder for event '{name}' was set in the past and will be sent immediately.")
                    reminder_embed = discord.Embed(
                        title=f"🔔 Reminder: {name}",
                        description=f"{description}\nThis event is happening now!",
                        color=discord.Color.gold()
                    )
                    await event_channel.send(content=ping, embed=reminder_embed)


            self.bot.loop.create_task(send_reminder())

        except ValueError:
            await interaction.followup.send("❌ **Invalid date or time format.** Please use `YYYY-MM-DD` and `HH:MM` (24hr).")
        except Exception as e:
            print(f"Error scheduling event: {e}")
            await interaction.followup.send(f"An unexpected error occurred while scheduling the event: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))