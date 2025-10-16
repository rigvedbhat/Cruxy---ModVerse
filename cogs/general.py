# cogs/general.py
import discord
from discord.ext import commands
from discord import app_commands
import random
from database import PersistentDB

class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = PersistentDB()

    async def cog_load(self):
        await self.db.connect()
        print("General cog connected to the database.")

    async def cog_unload(self):
        await self.db.close()
        print("General cog disconnected from the database.")
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        
        guild_id = message.guild.id
        user_id = message.author.id

        # --- Handle AFK Status ---
        # 1. Check if the user was AFK and remove their status
        if await self.db.get_afk_user(guild_id, user_id):
            await self.db.remove_afk(guild_id, user_id)
            await message.channel.send(f"👋 Welcome back, {message.author.mention}! I've removed your AFK status.", delete_after=10)

        # 2. Check if the user mentioned anyone who is AFK
        for member in message.mentions:
            afk_message = await self.db.get_afk_user(guild_id, member.id)
            if afk_message:
                await message.channel.send(f"💤 {member.display_name} is currently AFK: `{afk_message}`")

        # --- Handle XP Gain ---
        new_level = await self.db.add_xp(guild_id, user_id, random.randint(5, 15))
        if new_level is not None:
            await message.channel.send(f"🎉 Congrats {message.author.mention}, you leveled up to **Level {new_level}**!")
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # Find the welcome channel
        welcome_channel = discord.utils.get(member.guild.text_channels, name='welcome')
        if not welcome_channel:
            return

        embed = discord.Embed(
            title=f"Welcome to {member.guild.name}!",
            description=f"Hey {member.mention}, we're so glad you're here! Make sure to check out the rules.",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"You are member #{member.guild.member_count}")
        
        await welcome_channel.send(embed=embed)

    @app_commands.command(name="level", description="Check your current level and XP.")
    async def level(self, interaction: discord.Interaction):
        xp, level = await self.db.get_xp_and_level(interaction.guild.id, interaction.user.id)
        
        xp_needed = (level + 1) * 100
        xp_to_next = xp_needed - xp

        embed = discord.Embed(title=f"👑 Level Stats for {interaction.user.display_name}", color=discord.Color.og_blurple())
        embed.add_field(name="Level", value=f"**{level}**", inline=True)
        embed.add_field(name="XP", value=f"**{xp} / {xp_needed}**", inline=True)
        embed.set_footer(text=f"{xp_to_next} XP remaining until next level.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="afk", description="Set your AFK message. Will be removed when you next speak.")
    @app_commands.describe(message="Your AFK message (optional)")
    async def afk(self, interaction: discord.Interaction, message: str = "I'm currently away."):
        await self.db.set_afk(interaction.guild.id, interaction.user.id, message)
        await interaction.response.send_message(f"✅ Your AFK message is set: `{message}`", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))