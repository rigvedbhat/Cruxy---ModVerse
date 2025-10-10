# cogs/admin.py
import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction, Permissions, SelectOption

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        print("Admin.__init__ called")
        self.bot = bot

    async def get_moderator_roles(self, guild: discord.Guild):
        mod_roles = []
        for role in guild.roles:
            perms = role.permissions
            if any(getattr(perms, perm, False) for perm in self.bot.MODERATOR_PERMISSIONS):
                mod_roles.append(role)
        return mod_roles

    # --- UPDATED: Add a more robust check for bot permissions ---
    @app_commands.command(name="setup", description="Sets up the server structure.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        guild = interaction.guild
        
        # Check if the bot has the necessary permissions
        bot_member = guild.me
        if not bot_member.guild_permissions.manage_channels or not bot_member.guild_permissions.manage_roles:
            await interaction.response.send_message("❌ I do not have the required permissions to run this command. Please give me 'Manage Channels' and 'Manage Roles'.", ephemeral=True)
            return

        await interaction.response.send_message("🔧 Starting setup...", ephemeral=True)

        existing_roles = [role.name for role in guild.roles]
        for role_name in self.bot.REQUIRED_ROLES:
            if role_name not in existing_roles:
                try:
                    await guild.create_role(name=role_name)
                except discord.Forbidden:
                    await interaction.followup.send(f"⚠️ I couldn't create the '{role_name}' role. Please check my permissions.", ephemeral=True)

        mod_roles = await self.get_moderator_roles(guild)
        if not mod_roles:
            new_mod_role = await guild.create_role(
                name="Moderator",
                permissions=discord.Permissions(
                    kick_members=True, ban_members=True, manage_messages=True,
                    manage_channels=True, manage_roles=True, view_audit_log=True,
                    administrator=True
                )
            )
            mod_roles.append(new_mod_role)

        async def create_category(name, restrict_everyone=False, allow_view=True):
            overwrites = {guild.me: discord.PermissionOverwrite(read_messages=True)}
            if restrict_everyone:
                overwrites[guild.default_role] = discord.PermissionOverwrite(
                    read_messages=False, send_messages=False
                )
            else:
                overwrites[guild.default_role] = discord.PermissionOverwrite(
                    read_messages=allow_view, send_messages=False
                )
            for mod_role in mod_roles:
                overwrites[mod_role] = discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, manage_channels=True,
                    manage_roles=True, add_reactions=True
                )
            return await guild.create_category(name, overwrites=overwrites)

        welcome_cat = discord.utils.get(guild.categories, name="👋 Welcome and Rules")
        if not welcome_cat:
            welcome_cat = await create_category("👋 Welcome and Rules", restrict_everyone=False, allow_view=True)
            rules_channel = await guild.create_text_channel("rules", category=welcome_cat)
            await rules_channel.send("📜 **Server Rules**\n1. Be kind\n2. No spam\n3. Respect others\n4. Follow Discord ToS")
            await guild.create_text_channel("welcome", category=welcome_cat)
            await guild.create_text_channel("choose-your-roles", category=welcome_cat)

        announce_cat = discord.utils.get(guild.categories, name="📢 Announcements")
        if not announce_cat:
            announce_cat = await create_category("📢 Announcements", restrict_everyone=False, allow_view=True)
            await guild.create_text_channel("announcements", category=announce_cat)
            await guild.create_text_channel("events", category=announce_cat)

        general_cat = discord.utils.get(guild.categories, name="💬 General")
        if not general_cat:
            general_cat = await create_category("💬 General")
            await guild.create_text_channel("general-chats", category=general_cat)
            await guild.create_text_channel("clips-and-highlights", category=general_cat)

        voice_cat = discord.utils.get(guild.categories, name="🔊 Voice")
        if not voice_cat:
            voice_cat = await create_category("🔊 Voice")
            await guild.create_voice_channel("General Voice 1", category=voice_cat)
            await guild.create_voice_channel("General Voice 2", category=voice_cat)
            await guild.create_voice_channel("AFK", category=voice_cat)

        mod_cat = discord.utils.get(guild.categories, name="🔒 Moderators Only")
        if not mod_cat:
            mod_cat = await create_category("🔒 Moderators Only", restrict_everyone=True)
            await guild.create_text_channel("mods-only", category=mod_cat)
            await guild.create_voice_channel("mods-only-vc", category=mod_cat)

        feedback_channel = discord.utils.get(guild.text_channels, name="feedback")
        if not feedback_channel:
            feedback_channel = await guild.create_text_channel("feedback")

        if guild.text_channels:
            first_channel = guild.text_channels[0]
            async for message in first_channel.history(limit=1):
                if "Upgrade to Premium" not in message.content:
                    await first_channel.send("🚀 **Upgrade to Premium** to access more commands and features. *(Under Progress)*")
                    break
            else:
                await first_channel.send("🚀 **Upgrade to Premium** to access more commands and features. *(Under Progress)*")

        await interaction.followup.send("✅ Server setup complete!", ephemeral=True)

    @setup.error
    async def setup_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("❌ Admin permissions required.", ephemeral=True)
        else:
            await interaction.followup.send(f"⚠️ Setup failed: {error}", ephemeral=True)

    @app_commands.command(name="serverinfo", description="Shows server statistics and info.")
    async def server_info(self, interaction: discord.Interaction):
        guild = interaction.guild
        total_members = len(guild.members)
        total_bots = len([member for member in guild.members if member.bot])
        online_members = len([member for member in guild.members if member.status != discord.Status.offline])
        created_at = guild.created_at.strftime("%Y-%m-%d %H:%M:%S")
        preferred_locale = guild.preferred_locale
        boost_level = guild.premium_tier
        boost_count = guild.premium_subscription_count
        roles_count = len(guild.roles)
        text_channels_count = len(guild.text_channels)
        voice_channels_count = len(guild.voice_channels)
        categories_count = len(guild.categories)

        embed = discord.Embed(
            title=f"📊 Server Info for {guild.name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="👥 Total Members", value=f"{total_members} (Bots: {total_bots})", inline=False)
        embed.add_field(name="💬 Online Members", value=f"{online_members}", inline=False)
        embed.add_field(name="🗓️ Server Created", value=f"{created_at}", inline=False)
        embed.add_field(name="🌍 Server Locale", value=f"{preferred_locale}", inline=False)
        embed.add_field(name="💎 Server Boost Level", value=f"Level {boost_level} ({boost_count} boosts)", inline=False)
        embed.add_field(name="🔑 Roles Count", value=f"{roles_count}", inline=True)
        embed.add_field(name="📂 Text Channels Count", value=f"{text_channels_count}", inline=True)
        embed.add_field(name="🔊 Voice Channels Count", value=f"{voice_channels_count}", inline=True)
        embed.add_field(name="📚 Categories Count", value=f"{categories_count}", inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="reactionrole", description="Set up reaction role. Format: emoji:RoleName (comma-separated)")
    @app_commands.describe(pairs="Enter emoji:RoleName pairs separated by commas.")
    async def reactionrole(self, interaction: discord.Interaction, pairs: str):
        guild = interaction.guild
        channel = discord.utils.get(guild.text_channels, name="choose-your-roles")
        if not channel:
            return await interaction.response.send_message("❌ 'choose-your-roles' channel not found. Please run `/setup` first.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        emoji_role_map = {}
        lines = []

        for pair in pairs.split(","):
            try:
                emoji, role_name = pair.strip().split(":")
                role = discord.utils.get(guild.roles, name=role_name.strip())
                if not role:
                    role = await guild.create_role(name=role_name.strip())
                    await interaction.followup.send(f"✅ Created role: {role.name}", ephemeral=True)
                emoji_role_map[emoji.strip()] = role
                lines.append(f"{emoji.strip()} - {role.name}")
            except ValueError:
                await interaction.followup.send(f"❌ Invalid format for pair `{pair}`. Use `emoji:RoleName`.", ephemeral=True)
                continue
            except Exception as e:
                await interaction.followup.send(f"❌ Error with pair `{pair}`: {e}", ephemeral=True)
                continue

        if not lines:
            return await interaction.followup.send("❌ No valid reaction role pairs were provided or processed.", ephemeral=True)

        message_text = "**React to get a role:**\n" + "\n".join(lines)
        message = await channel.send(message_text)

        for emoji in emoji_role_map:
            try:
                await message.add_reaction(emoji)
            except discord.HTTPException:
                await interaction.followup.send(f"⚠️ Could not add reaction for emoji: {emoji}. It might be invalid.", ephemeral=True)
            except Exception:
                pass

        self.bot.reaction_role_messages[guild.id] = message.id
        self.bot.reaction_role_mapping[message.id] = {emoji: role.id for emoji, role in emoji_role_map.items()}

        await interaction.followup.send("🎭 Reaction role message created!", ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        message_id = payload.message_id
        if message_id not in self.bot.reaction_role_mapping:
            return

        emoji = str(payload.emoji)
        role_id = self.bot.reaction_role_mapping[message_id].get(emoji)
        if not role_id:
            return

        role = guild.get_role(role_id)
        member = guild.get_member(payload.user_id)

        if role and member:
            try:
                await member.add_roles(role)
            except discord.Forbidden:
                pass
            except Exception as e:
                print(f"Error adding role {role.name} to {member.name}: {e}")

    class PermissionButtons(ui.View):
        def __init__(self, guild, channel_name, requester, category=None, private_role=None):
            super().__init__(timeout=60)
            self.guild = guild
            self.channel_name = channel_name
            self.category = category
            self.requester = requester
            self.private_role = private_role

        async def create_channel_logic(self, interaction: Interaction, overwrites):
            target_category = None
            if self.category:
                target_category = discord.utils.get(self.guild.categories, name=self.category)
                if not target_category:
                    category_overwrites = {self.guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False)}
                    target_category = await self.guild.create_category(self.category, overwrites=category_overwrites)

            channel = await self.guild.create_text_channel(
                self.channel_name, category=target_category, overwrites=overwrites
            )

            category_display = f"in `{target_category.name}`" if target_category else "without a category"
            await interaction.response.send_message(
                f"✅ Created channel `{channel.name}` {category_display} with selected permissions!",
                ephemeral=True
            )

        @ui.button(label="🔒 Private (You + Role)", style=discord.ButtonStyle.red)
        async def private_button(self, interaction: Interaction, button: ui.Button):
            overwrites = {
                self.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                self.requester: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            }
            if self.private_role:
                overwrites[self.private_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            await self.create_channel_logic(interaction, overwrites)

        @ui.button(label="🌐 Public (Everyone)", style=discord.ButtonStyle.green)
        async def public_button(self, interaction: Interaction, button: ui.Button):
            overwrites = {
                self.guild.default_role: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, manage_channels=False,
                    manage_roles=False, mention_everyone=False,
                )
            }
            await self.create_channel_logic(interaction, overwrites)

        @ui.button(label="🛑 Cancel", style=discord.ButtonStyle.grey)
        async def cancel_button(self, interaction: Interaction, button: ui.Button):
            await interaction.response.send_message("❌ Channel creation cancelled.", ephemeral=True)
            self.stop()

    class RoleSelect(ui.View):
        def __init__(self, guild, channel_name, requester, category=None):
            super().__init__(timeout=60)
            self.guild = guild
            self.channel_name = channel_name
            self.category = category
            self.requester = requester

            options = [
                SelectOption(label=role.name, value=str(role.id))
                for role in guild.roles if role.name != "@everyone"
            ][:25]

            self.select = ui.Select(placeholder="Select a role for private access", options=options)
            self.select.callback = self.select_callback
            self.add_item(self.select)

        async def select_callback(self, interaction: Interaction):
            role_id = int(self.select.values[0])
            role = self.guild.get_role(role_id)
            view = Admin.PermissionButtons(self.guild, self.channel_name, self.requester, category=self.category, private_role=role)
            await interaction.response.edit_message(
                content=f"Choose permission setting for `{self.channel_name}`"
                         f"{f' under `{self.category}`' if self.category else ''}:",
                view=view
            )

    @app_commands.command(name="createchannel", description="Create a channel with optional category and permission control.")
    @app_commands.describe(
        category_name="Name of the category (leave blank for no category or to use existing one)",
        channel_name="Name of the new text channel"
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def create_channel_command(self, interaction: discord.Interaction, channel_name: str, category_name: str = None):
        category_name = category_name.strip() if category_name else None
        view = self.RoleSelect(interaction.guild, channel_name, interaction.user, category=category_name)
        await interaction.response.send_message(
            f"🔐 Choose a role to give access with you (for private channel):",
            view=view,
            ephemeral=True
        )

    @create_channel_command.error
    async def create_channel_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("❌ You need **'Manage Channels'** permission to use this command.", ephemeral=True)
        else:
            print(f"Error in create_channel_command: {error}")
            await interaction.response.send_message(f"An unexpected error occurred: {error}", ephemeral=True)


async def setup(bot: commands.Bot):
    print("Admin.setup called")
    await bot.add_cog(Admin(bot))