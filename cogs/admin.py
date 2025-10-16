# cogs/admin.py
import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction
from database import PersistentDB

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = PersistentDB()

    async def cog_load(self):
        await self.db.connect()
        # Load all reaction roles from DB into the bot's cache for quick access
        self.bot.reaction_role_mapping = await self.db.get_all_reaction_roles()
        print(f"Admin cog connected and loaded {len(self.bot.reaction_role_mapping)} reaction role message(s) from DB.")

    async def cog_unload(self):
        await self.db.close()
        print("Admin cog disconnected from the database.")

    @app_commands.command(name="serverinfo", description="Shows server statistics and info.")
    async def server_info(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title=f"📊 Server Info for {guild.name}", color=discord.Color.blue())
        embed.add_field(name="👥 Total Members", value=f"{guild.member_count}", inline=True)
        embed.add_field(name="🗓️ Created On", value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=True)
        embed.add_field(name="👑 Owner", value=f"{guild.owner.mention}", inline=True)
        embed.add_field(name="💎 Boost Level", value=f"Level {guild.premium_tier} ({guild.premium_subscription_count} boosts)", inline=False)
        embed.add_field(name="📚 Channels", value=f"{len(guild.text_channels)} Text | {len(guild.voice_channels)} Voice", inline=True)
        embed.add_field(name="🔑 Roles", value=f"{len(guild.roles)}", inline=True)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="reactionrole", description="Set up a new reaction role message.")
    @app_commands.describe(
        channel="The channel to send the reaction role message in.",
        message="The text to display in the message.",
        emoji="The emoji for the reaction.",
        role="The role to assign for this reaction."
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def reactionrole(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str, emoji: str, role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if bot can manage the role
            if interaction.guild.me.top_role <= role:
                await interaction.followup.send("❌ I cannot assign this role because it is higher than or equal to my own top role.", ephemeral=True)
                return

            embed = discord.Embed(title="React for a Role!", description=message, color=discord.Color.blurple())
            embed.add_field(name="Role", value=f"{emoji}  →  {role.mention}")
            
            sent_message = await channel.send(embed=embed)
            await sent_message.add_reaction(emoji)

            # Save to the database
            await self.db.add_reaction_role(sent_message.id, interaction.guild.id, channel.id, emoji, role.id)
            
            # Update the in-memory cache
            if sent_message.id not in self.bot.reaction_role_mapping:
                self.bot.reaction_role_mapping[sent_message.id] = {}
            self.bot.reaction_role_mapping[sent_message.id][emoji] = role.id

            await interaction.followup.send("✅ Reaction role created successfully!", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self._handle_reaction(payload, add_role=True)
        
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self._handle_reaction(payload, add_role=False)
        
    async def _handle_reaction(self, payload: discord.RawReactionActionEvent, add_role: bool):
        if payload.user_id == self.bot.user.id:
            return

        # Check if the message is a reaction role message from our cache
        if payload.message_id not in self.bot.reaction_role_mapping:
            return

        emoji = str(payload.emoji)
        # Check if the emoji is part of the mapping for this message
        role_id = self.bot.reaction_role_mapping[payload.message_id].get(emoji)
        if not role_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        
        role = guild.get_role(role_id)
        if not role: return

        member = guild.get_member(payload.user_id)
        if not member: return

        try:
            if add_role:
                await member.add_roles(role, reason="Reaction Role")
            else:
                await member.remove_roles(role, reason="Reaction Role")
        except discord.Forbidden:
            print(f"Failed to add/remove role {role.name} for {member.name} in {guild.name} - Missing Permissions.")
        except Exception as e:
            print(f"An error occurred handling reaction role: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))