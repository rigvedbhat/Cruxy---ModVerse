import asyncio
import json
import logging
import os
import re

import discord
import google.api_core.exceptions as google_exceptions
import google.generativeai as genai
from discord import app_commands, ui
from discord.ext import commands

from utils.sanitize import sanitize_prompt

log = logging.getLogger(__name__)
model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"))


class DeleteChannelView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Delete This Channel",
        style=discord.ButtonStyle.danger,
        custom_id="delete_setup_channel",
    )
    async def delete_channel(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message(
                "You need 'Manage Channels' permission to do this.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(
            f"Deleting channel `{interaction.channel.name}` in 5 seconds...",
            ephemeral=True,
        )
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason="Seromod setup complete.")
        except (discord.NotFound, discord.HTTPException):
            pass


class ConfirmBuildView(ui.View):
    def __init__(self, interaction: discord.Interaction, setup_plan: dict, cog, reset: bool):
        super().__init__(timeout=180)
        self.interaction = interaction
        self.setup_plan = setup_plan
        self.cog = cog
        self.reset = reset

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.interaction.edit_original_response(
                content="Timed out. The build has been cancelled.",
                view=self,
            )
        except discord.NotFound:
            pass

    @ui.button(label="Confirm & Build", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True

        original_content = "Plan confirmed. Starting the build process..."
        if self.reset:
            original_content += "\n**Server reset in progress. This may take a moment.**"

        await self.interaction.edit_original_response(content=original_content, view=self)
        await self.cog._execute_build_plan(
            interaction.guild,
            interaction.channel,
            self.setup_plan,
            self.reset,
        )
        self.stop()

    @ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        await self.interaction.edit_original_response(
            content="Build cancelled by user.",
            view=self,
        )
        self.stop()


class AICommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(DeleteChannelView())
        self.max_messages_to_keep = 10

    async def _manage_history(self, chat_session):
        history_length = len(chat_session.history)
        if history_length > self.max_messages_to_keep + 1:
            chat_session.history = [chat_session.history[0]] + chat_session.history[
                -self.max_messages_to_keep :
            ]
            log.info("Pruned chat history to %s messages.", len(chat_session.history) - 1)

    def _extract_json_object(self, text: str):
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if not json_match:
            return None
        return json.loads(json_match.group(0))

    def _find_feedback_channel(self, guild: discord.Guild):
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                return channel
        return None

    async def generate_build_plan(self, theme: str, variation_hint: str = ""):
        clean_theme = sanitize_prompt(theme)
        clean_variation_hint = sanitize_prompt(str(variation_hint), max_length=80)
        setup_prompt = self._get_setup_prompt(clean_theme, clean_variation_hint)

        async with self.bot.gemini_semaphore:
            response = await model.generate_content_async(setup_prompt)

        if not response.parts:
            block_reason = (
                response.prompt_feedback.block_reason.name
                if response.prompt_feedback.block_reason
                else "Unknown"
            )
            raise ValueError(
                f"Request blocked by AI safety filter.\nReason: `{block_reason}`"
            )

        if not response.text:
            raise ValueError("The AI generated an empty response. Please try again.")

        setup_plan = self._extract_json_object(response.text)
        if not setup_plan or not setup_plan.get("plan"):
            raise ValueError("The AI chose not to generate a server plan for that theme.")

        return setup_plan

    async def execute_api_build_plan(
        self,
        guild: discord.Guild,
        setup_plan: dict,
        reset_server: bool,
        theme: str = "",
    ):
        feedback_channel = self._find_feedback_channel(guild)
        if not feedback_channel:
            log.error(
                "API build execution failed: bot could not find a channel in guild %s",
                guild.id,
            )
            return

        if theme:
            await feedback_channel.send(
                "Received approved server build from the dashboard for theme: "
                f"**'{sanitize_prompt(theme)}'**"
            )
        else:
            await feedback_channel.send("Received an approved server build from the dashboard.")

        await self._execute_build_plan(guild, feedback_channel, setup_plan, reset_server)

    async def handle_bot_mention(self, message: discord.Message) -> bool:
        if self.bot.user in message.mentions:
            cleaned_message = message.content.replace(f"<@{self.bot.user.id}>", "").strip()
            if not cleaned_message:
                await message.channel.send(
                    "Hello there! How can I help you today?",
                    reference=message,
                )
                return True

            await self.handle_chat_request(message, cleaned_message)
            return True

        return False

    async def handle_chat_request(self, message: discord.Message, prompt: str):
        channel_id = message.channel.id
        if channel_id not in self.bot.chats:
            self.bot.chats[channel_id] = model.start_chat(
                history=[
                    {
                        "role": "user",
                        "parts": [
                            "You are a friendly and helpful Discord bot named Seromod."
                        ],
                    }
                ]
            )

        async with message.channel.typing():
            try:
                chat = self.bot.chats[channel_id]
                await self._manage_history(chat)
                response = await chat.send_message_async(prompt)
                await message.channel.send(response.text, reference=message)
            except google_exceptions.ResourceExhausted:
                msg = (
                    "The AI service is currently rate-limited. "
                    "Please wait 60 seconds and try again."
                )
                await message.channel.send(msg, reference=message)
            except google_exceptions.GoogleAPICallError as e:
                msg = f"AI service returned an error: {getattr(e, 'message', str(e))}"
                await message.channel.send(msg, reference=message)
            except Exception as e:
                log.error("An error occurred with the AI chat: %s", e)
                await message.channel.send(
                    "Sorry, I'm having trouble with the AI service right now.",
                    reference=message,
                )

    def _format_plan_embed(self, theme: str, setup_plan: dict) -> discord.Embed:
        initial_description = (
            f"Here is the plan my AI generated for the theme: **'{theme}'**.\n"
            "Please review the changes below and confirm to proceed."
        )
        embed = discord.Embed(
            title="Server Build Plan Preview",
            description=initial_description,
            color=discord.Color.blue(),
        )

        roles = setup_plan.get("roles", [])
        if roles:
            embed.add_field(
                name="Roles to be Created",
                value="> " + "\n> ".join(f"`{role}`" for role in roles),
                inline=False,
            )
        else:
            embed.add_field(name="Roles to be Created", value="> None", inline=False)

        structure_text = ""
        for task in setup_plan.get("plan", []):
            if task["task"] == "create_category":
                structure_text += f"\n[Category] **{task['name']}**\n"
            elif task["task"] == "create_channel":
                channel_type = task.get("channel_type", "text")
                icon = "[Voice]" if channel_type == "voice" else "#"
                perms = task.get("permissions", "public")
                perm_text = ""
                if isinstance(perms, dict) and perms.get("type") == "restricted":
                    allowed = perms.get("allow", [])
                    perm_text = f" (Restricted to: {', '.join(f'`{role}`' for role in allowed)})"
                elif perms == "read-only":
                    perm_text = " (Read-Only)"
                structure_text += f"  - {icon} {task['name']}{perm_text}\n"

        if structure_text:
            final_description = embed.description + "\n\n**Server Structure**" + structure_text
            if len(final_description) > 4096:
                final_description = final_description[:4090] + "\n..."
            embed.description = final_description

        embed.set_footer(
            text="The build will be cancelled automatically in 3 minutes if you don't respond."
        )
        return embed

    async def _execute_build_plan(
        self,
        guild: discord.Guild,
        feedback_channel: discord.TextChannel,
        setup_plan: dict,
        reset: bool,
    ):
        if not feedback_channel:
            return

        if reset:
            await feedback_channel.send("**Step 1/3:** Wiping existing server structure...")
            for channel in guild.channels:
                if channel.id != feedback_channel.id:
                    try:
                        await channel.delete(reason="Seromod server reset")
                    except Exception as e:
                        log.warning("Failed to delete channel %s: %s", channel.name, e)

            for role in guild.roles:
                if role.name != "@everyone" and not role.managed and role < guild.me.top_role:
                    try:
                        await role.delete(reason="Seromod server reset")
                    except Exception as e:
                        log.warning("Failed to delete role %s: %s", role.name, e)

            await asyncio.sleep(2)

        created_roles = {}
        created_categories = {}

        try:
            role_step = "Step 2/3" if reset else "Step 1/2"
            await feedback_channel.send(f"**{role_step}:** Creating roles...")
            role_names_to_create = setup_plan.get("roles", [])
            if role_names_to_create:
                for role_name in role_names_to_create:
                    existing_role = discord.utils.get(guild.roles, name=role_name)
                    if existing_role:
                        created_roles[role_name] = existing_role
                    else:
                        created_roles[role_name] = await guild.create_role(
                            name=role_name,
                            reason="Seromod Server Build",
                        )

            channel_step = "Step 3/3" if reset else "Step 2/2"
            await feedback_channel.send(f"**{channel_step}:** Creating categories and channels...")

            for task in setup_plan.get("plan", []):
                task_name = task.get("task")
                name = task.get("name")

                if task_name == "create_category":
                    created_categories[name] = await guild.create_category(
                        name,
                        reason="Seromod Server Build",
                    )
                    continue

                if task_name != "create_channel":
                    continue

                category = created_categories.get(task.get("category"))
                overwrites = {}
                perms_type = task.get("permissions", "public")

                if perms_type == "read-only":
                    overwrites[guild.default_role] = discord.PermissionOverwrite(
                        send_messages=False
                    )
                elif isinstance(perms_type, dict) and perms_type.get("type") == "restricted":
                    overwrites[guild.default_role] = discord.PermissionOverwrite(
                        view_channel=False
                    )
                    overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True)
                    for role_name in perms_type.get("allow", []):
                        role_obj = created_roles.get(role_name)
                        if role_obj:
                            overwrites[role_obj] = discord.PermissionOverwrite(
                                view_channel=True
                            )

                channel_type = task.get("channel_type", "text")
                if channel_type == "voice":
                    await guild.create_voice_channel(
                        name,
                        category=category,
                        overwrites=overwrites,
                        reason="Seromod Server Build",
                    )
                    continue

                channel_topic = task.get("topic")
                initial_message = task.get("message")
                new_channel = await guild.create_text_channel(
                    name,
                    category=category,
                    overwrites=overwrites,
                    topic=channel_topic,
                    reason="Seromod Server Build",
                )
                if initial_message:
                    try:
                        await new_channel.send(initial_message)
                    except discord.Forbidden:
                        pass

            await feedback_channel.send("**Server setup complete!**")
            if reset:
                await feedback_channel.send(
                    "Build complete! You can now delete this setup channel.",
                    view=DeleteChannelView(),
                )
        except Exception as e:
            await feedback_channel.send(f"An unexpected error occurred during build: {e}")

    async def handle_api_build_request(self, guild: discord.Guild, theme: str, reset_server: bool):
        theme = sanitize_prompt(theme)
        feedback_channel = self._find_feedback_channel(guild)

        if not feedback_channel:
            log.error("API build request failed: bot could not find a channel in guild %s", guild.id)
            return

        await feedback_channel.send(
            f"Received `/buildserver` request from the web dashboard for theme: **'{theme}'**"
        )

        try:
            setup_plan = await self.generate_build_plan(theme)
            await self._execute_build_plan(guild, feedback_channel, setup_plan, reset_server)
        except google_exceptions.ResourceExhausted:
            msg = (
                "The AI service is currently rate-limited. "
                "Please wait 60 seconds and try again."
            )
            await feedback_channel.send(f"[Warning] {msg}")
        except google_exceptions.GoogleAPICallError as e:
            msg = f"AI service returned an error: {getattr(e, 'message', str(e))}"
            await feedback_channel.send(f"[Warning] {msg}")
        except ValueError as e:
            await feedback_channel.send(str(e))
        except Exception as e:
            log.error("An unexpected error occurred in API build request: %s", e)
            await feedback_channel.send(f"An unexpected error occurred: {e}")

    def _get_setup_prompt(self, theme: str, variation_hint: str = "") -> str:
        theme = sanitize_prompt(theme)
        variation_instruction = ""
        if variation_hint:
            variation_instruction = (
                "\n**REGENERATION REQUEST:** This is a redo request. Generate a "
                "distinctly different but still valid server structure variation.\n"
                f'Variation marker: "{variation_hint}"\n'
            )

        return f"""
You are a machine that generates a JSON object for building a Discord server. Your response MUST be a single, raw, valid JSON object and nothing else. Do not include any commentary, explanations, or markdown formatting.

**USER REQUEST:** "Build a server for {theme}"
{variation_instruction}
**CRITICAL RULES:**
1.  Your entire response must be a single JSON object.
2.  The `plan` array MUST NOT be empty. A minimal plan is not acceptable.
3.  Channel names (`name` key) MUST be lowercase, use hyphens for spaces, and contain no special characters (e.g., "general-chat", "user-guides").
4.  Role names (`roles` key) can contain spaces and uppercase letters (e.g., "Team Captain").
5.  For `permissions` of type "restricted", the roles listed in the `allow` array MUST be present in the top-level `roles` array.

**JSON SCHEMA & LOGIC:**
- `roles`: (Optional) `Array<String>`. A list of role names to create.
- `plan`: (Required) `Array<Object>`. A non-empty list of tasks.
  - `task`: `String`. Must be "create_category" or "create_channel".
  - `name`: `String`. The name of the category or channel. Must follow naming rules.
  - `category`: `String`. (Required for "create_channel") The `name` of a previously defined "create_category" task.
  - `channel_type`: `String`. (Required for "create_channel") Must be "text" or "voice".
  - `permissions`: `String` ("public" or "read-only") OR `Object` (`{{"type": "restricted", "allow": Array<String>}}`).
  - `topic`: `String`. (Optional, for `channel_type: "text"`) A short description. `voice` channels MUST NOT have this key.
  - `message`: `String`. (Optional, for `channel_type: "text"`) A welcome message. `voice` channels MUST NOT have this key.

**VALIDATION:** Before generating your final response, mentally validate your output against all rules and the schema above.

Generate the JSON object now.
"""

    @app_commands.command(
        name="buildserver",
        description="Build a server structure based on a theme using AI.",
    )
    @app_commands.describe(
        theme="The theme for the server (e.g., 'A high-tech startup')",
        reset_server="WARNING: Deletes all existing channels and roles before building.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    async def build_server_command(
        self,
        interaction: discord.Interaction,
        theme: str,
        reset_server: bool = False,
    ):
        await interaction.response.defer(ephemeral=True, thinking=True)

        clean_theme = sanitize_prompt(theme)
        try:
            setup_plan = await self.generate_build_plan(clean_theme)
            preview_embed = self._format_plan_embed(clean_theme, setup_plan)
            confirmation_view = ConfirmBuildView(
                interaction,
                setup_plan,
                self,
                reset=reset_server,
            )
            await interaction.followup.send(
                embed=preview_embed,
                view=confirmation_view,
                ephemeral=True,
            )
        except google_exceptions.ResourceExhausted:
            msg = (
                "The AI service is currently rate-limited. "
                "Please wait 60 seconds and try again."
            )
            await interaction.followup.send(msg, ephemeral=True)
        except google_exceptions.GoogleAPICallError as e:
            msg = f"AI service returned an error: {getattr(e, 'message', str(e))}"
            await interaction.followup.send(msg, ephemeral=True)
        except ValueError as e:
            await interaction.followup.send(str(e), ephemeral=True)
        except Exception as e:
            log.error("An unexpected error occurred in buildserver: %s", e)
            await interaction.followup.send(f"An unexpected error occurred: {e}", ephemeral=True)

    @build_server_command.error
    async def on_cooldown_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CommandOnCooldown):
            message = f"Slow down! Try again in {error.retry_after:.0f}s."
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AICommands(bot))
