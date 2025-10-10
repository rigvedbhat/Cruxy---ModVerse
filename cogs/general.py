# cogs/general.py
import discord
from discord.ext import commands
from discord import app_commands
import random

# Import the new PersistentDB class
from database import PersistentDB

class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Initialize the database connection
        self.db = PersistentDB()

    async def cog_load(self):
        """Connect to the database when the cog loads."""
        await self.db.connect()
        print("General cog connected to the database.")

    async def cog_unload(self):
        """Close the database connection when the cog unloads."""
        await self.db.close()
        print("General cog disconnected from the database.")

    @app_commands.command(name="fakeittillyoumakeit", description="Gives you a confidence boost!")
    async def fake_it_till_you_make_it(self, interaction: discord.Interaction):
        messages = [
            "You're not just going to make it, you're going to OWN it! 💥",
            "Who needs luck when you have willpower? 😎",
            "You're the question everyone is asking. 🤔💡",
            "Confidence is your superpower. Use it! 💪",
            "Fake it till you make it—and soon, you'll *be* it. 🚀"
        ]
        await interaction.response.send_message(random.choice(messages), ephemeral=True)

    @app_commands.command(name="feedback", description="Send feedback to the feedback channel!")
    @app_commands.describe(feedback_message="What feedback would you like to share?")
    async def feedback(self, interaction: discord.Interaction, feedback_message: str):
        guild = interaction.guild
        feedback_channel = discord.utils.get(guild.text_channels, name="feedback")

        if feedback_channel:
            await feedback_channel.send(f"📝 Feedback from {interaction.user.mention}: {feedback_message}")
            await interaction.response.send_message("✅ Feedback submitted!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Feedback channel not found.", ephemeral=True)

    @app_commands.command(name="afk", description="Set your AFK message.")
    @app_commands.describe(message="Your AFK message (optional)")
    async def afk(self, interaction: discord.Interaction, message: str = "I'm currently away. I'll get back to you soon!"):
        guild_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)

        # The AFK logic still relies on the in-memory global dictionary
        if guild_id not in self.bot.afk_users:
            self.bot.afk_users[guild_id] = {}
        self.bot.afk_users[guild_id][user_id] = message
        
        await interaction.response.send_message(f"✅ Your AFK message is set: {message}", ephemeral=True)

    @app_commands.command(name="level", description="Check your current level and XP.")
    async def level(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        user_id = interaction.user.id

        # Retrieve XP and level from the new database
        xp, level = await self.db.get_xp_and_level(guild_id, user_id)
        
        # Calculate XP needed for next level
        xp_needed_for_next_level_total = (level + 1) * 100
        xp_to_next_level = xp_needed_for_next_level_total - xp

        await interaction.response.send_message(
            f"👑 {interaction.user.mention}, you are currently Level **{level}** with **{xp} XP**.\n"
            f"Only {xp_to_next_level} XP to reach Level {level + 1}!",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))