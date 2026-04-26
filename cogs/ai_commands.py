import asyncio
import json
import logging
import os
import re
import time

import discord
import google.api_core.exceptions as google_exceptions
import google.generativeai as genai
from discord import app_commands, ui
from discord.ext import commands

from utils.sanitize import sanitize_prompt

log = logging.getLogger(__name__)
model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"))
SAFE_ALLOWED_MENTIONS = discord.AllowedMentions.none()
CHANNEL_NAME_RE = re.compile(r"^[a-z0-9-]{1,48}$")
ROLE_NAME_RE = re.compile(r"^[A-Za-z0-9 _.\-]{1,80}$")


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
        self.chat_cooldown_seconds = max(5, int(os.getenv("CHAT_COOLDOWN_SECONDS", "15")))
        self.max_build_roles = max(1, int(os.getenv("MAX_BUILD_ROLES", "25")))
        self.max_build_categories = max(1, int(os.getenv("MAX_BUILD_CATEGORIES", "12")))
        self.max_build_channels = max(1, int(os.getenv("MAX_BUILD_CHANNELS", "50")))
        self.max_restricted_roles = max(1, int(os.getenv("MAX_RESTRICTED_ROLE_ALLOW", "10")))
        self.chat_cooldowns = {}
        self.chat_locks = {}

    async def _manage_history(self, chat_session):
        history_length = len(chat_session.history)
        if history_length > self.max_messages_to_keep + 1:
            chat_session.history = [chat_session.history[0]] + chat_session.history[
                -self.max_messages_to_keep :
            ]
            log.info("Pruned chat history to %s messages.", len(chat_session.history) - 1)

    def _extract_json_object(self, text: str):
        """Extract first JSON object from model response."""
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        text = re.sub(r"```(?:json)?\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        end = -1
        for index, char in enumerate(text[start:], start):
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = index
                    break

        if end == -1:
            return None

        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None

    def _carry_thought_signatures(self, history: list) -> list:
        """
        Gemini 3 requires thought signatures to be passed back.
        Extract and re-attach them from assistant turns in history.
        This is a no-op on older models.
        """
        # google-generativeai SDK handles this internally for ChatSession.
        # This method is a documentation hook - the SDK's send_message_async
        # already carries signatures through the ChatSession object.
        # Manual calls to generate_content_async must include parts with
        # thought signatures if present in prior response.parts.
        return history

    def _get_channel_lock(self, channel_id: int) -> asyncio.Lock:
        lock = self.chat_locks.get(channel_id)
        if lock is None:
            lock = asyncio.Lock()
            self.chat_locks[channel_id] = lock
        return lock

    def _get_guild_operation_lock(self, guild_id: int) -> asyncio.Lock:
        lock = self.bot.guild_operation_locks.get(guild_id)
        if lock is None:
            lock = asyncio.Lock()
            self.bot.guild_operation_locks[guild_id] = lock
        return lock

    def _consume_chat_cooldown(self, guild_id: int, user_id: int) -> float:
        now = time.monotonic()
        key = (guild_id, user_id)
        retry_at = self.chat_cooldowns.get(key, 0.0)
        if retry_at > now:
            return retry_at - now

        self.chat_cooldowns[key] = now + self.chat_cooldown_seconds
        if len(self.chat_cooldowns) > 2048:
            stale_keys = [cooldown_key for cooldown_key, expiry in self.chat_cooldowns.items() if expiry <= now]
            for stale_key in stale_keys[:1024]:
                self.chat_cooldowns.pop(stale_key, None)
        return 0.0

    def _validate_role_name(self, role_name: str) -> str:
        clean_name = sanitize_prompt(role_name, max_length=80).strip()
        if not clean_name or not ROLE_NAME_RE.fullmatch(clean_name):
            raise ValueError(f"Invalid role name in AI plan: {role_name!r}")
        if clean_name == "@everyone":
            raise ValueError("The AI attempted to modify the @everyone role.")
        return clean_name

    def _validate_channel_name(self, channel_name: str) -> str:
        clean_name = sanitize_prompt(channel_name, max_length=48).lower().strip()
        if not CHANNEL_NAME_RE.fullmatch(clean_name):
            raise ValueError(f"Invalid channel or category name in AI plan: {channel_name!r}")
        return clean_name

    def _normalize_permissions(self, permissions, valid_roles):
        if permissions in (None, "", "public"):
            return "public"
        if permissions == "read-only":
            return "read-only"
        if isinstance(permissions, dict) and permissions.get("type") == "restricted":
            allowed_roles = permissions.get("allow", [])
            if not isinstance(allowed_roles, list) or not allowed_roles:
                raise ValueError("Restricted channel permissions must include at least one valid role.")
            normalized_roles = []
            seen_roles = set()
            for role_name in allowed_roles:
                clean_name = self._validate_role_name(str(role_name))
                if clean_name not in valid_roles:
                    raise ValueError(f"Restricted permissions reference unknown role: {clean_name}")
                if clean_name in seen_roles:
                    continue
                seen_roles.add(clean_name)
                normalized_roles.append(clean_name)
            if len(normalized_roles) > self.max_restricted_roles:
                raise ValueError("Restricted permissions reference too many roles.")
            return {"type": "restricted", "allow": normalized_roles}
        raise ValueError("Invalid permissions object in AI plan.")

    def _validate_build_plan(self, setup_plan: dict) -> dict:
        if not isinstance(setup_plan, dict):
            raise ValueError("The AI returned an invalid build plan.")

        raw_roles = setup_plan.get("roles", []) or []
        if not isinstance(raw_roles, list):
            raise ValueError("The AI returned invalid role data.")

        roles = []
        seen_roles = set()
        for role_name in raw_roles:
            clean_name = self._validate_role_name(str(role_name))
            if clean_name in seen_roles:
                continue
            seen_roles.add(clean_name)
            roles.append(clean_name)
        if len(roles) > self.max_build_roles:
            raise ValueError("The AI generated too many roles for a single build.")

        raw_tasks = setup_plan.get("plan")
        if not isinstance(raw_tasks, list) or not raw_tasks:
            raise ValueError("The AI chose not to generate a valid server plan.")

        tasks = []
        category_names = set()
        channel_names = set()
        channel_count = 0

        for raw_task in raw_tasks:
            if not isinstance(raw_task, dict):
                raise ValueError("The AI returned malformed task data.")

            task_type = raw_task.get("task")
            if task_type == "create_category":
                category_name = self._validate_channel_name(str(raw_task.get("name", "")))
                if category_name in category_names:
                    continue
                if len(category_names) >= self.max_build_categories:
                    raise ValueError("The AI generated too many categories for a single build.")
                category_names.add(category_name)
                tasks.append({"task": "create_category", "name": category_name})
                continue

            if task_type != "create_channel":
                raise ValueError(f"Unsupported task in AI plan: {task_type}")

            if channel_count >= self.max_build_channels:
                raise ValueError("The AI generated too many channels for a single build.")

            channel_name = self._validate_channel_name(str(raw_task.get("name", "")))
            if channel_name in channel_names:
                continue

            category_name = self._validate_channel_name(str(raw_task.get("category", "")))
            if category_name not in category_names:
                raise ValueError(f"Channel {channel_name} references an unknown category.")

            channel_type = str(raw_task.get("channel_type", "text")).strip().lower()
            if channel_type not in {"text", "voice"}:
                raise ValueError(f"Invalid channel type in AI plan: {channel_type}")

            permissions = self._normalize_permissions(raw_task.get("permissions", "public"), seen_roles)
            topic = None
            message = None
            if channel_type == "text":
                topic = sanitize_prompt(raw_task.get("topic", ""), max_length=250) or None
                message = sanitize_prompt(raw_task.get("message", ""), max_length=500) or None

            tasks.append(
                {
                    "task": "create_channel",
                    "name": channel_name,
                    "category": category_name,
                    "channel_type": channel_type,
                    "permissions": permissions,
                    "topic": topic,
                    "message": message,
                }
            )
            channel_names.add(channel_name)
            channel_count += 1

        if not tasks:
            raise ValueError("The AI returned an empty build plan.")

        return {"roles": roles, "plan": tasks}

    async def _get_or_create_feedback_channel(self, guild: discord.Guild):
        channel = discord.utils.get(guild.text_channels, name="seromod-instructions")
        if not channel:
            try:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    guild.me: discord.PermissionOverwrite(view_channel=True)
                }
                channel = await guild.create_text_channel("seromod-instructions", overwrites=overwrites)
            except Exception as e:
                log.warning("Could not create protected feedback channel in %s: %s", guild.name, e)
                # Fallback
                for ch in guild.text_channels:
                    if ch.permissions_for(guild.me).send_messages:
                        return ch
                return None
        return channel

    async def generate_build_plan(self, theme: str, variation_hint: str = ""):
        clean_theme = sanitize_prompt(theme)
        clean_variation_hint = sanitize_prompt(str(variation_hint), max_length=80)
        setup_prompt = self._get_setup_prompt(clean_theme, clean_variation_hint)

        async with self.bot.gemini_semaphore:
            # NOTE: Gemini 3 uses dynamic thinking by default and may include
            # thoughtSignature parts. The ChatSession object manages these automatically.
            # If you refactor to raw generate_content_async multi-turn calls, you MUST
            # pass back thought signatures or response quality degrades.
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

        return self._validate_build_plan(setup_plan)

    async def execute_api_build_plan(
        self,
        guild: discord.Guild,
        setup_plan: dict,
        reset_server: bool,
        theme: str = "",
        job_id: str | None = None,
    ):
        try:
            if job_id:
                await self.bot.db.update_build_job(
                    job_id,
                    "running",
                    "Applying the approved build plan in Discord...",
                )

            feedback_channel = await self._get_or_create_feedback_channel(guild)
            if not feedback_channel:
                message = (
                    "API build execution failed: bot could not find a channel in "
                    f"guild {guild.id}"
                )
                log.error(message)
                if job_id:
                    await self.bot.db.update_build_job(job_id, "failed", message)
                return

            if theme:
                await feedback_channel.send(
                    "Received approved server build from the dashboard for theme: "
                    f"**'{sanitize_prompt(theme)}'**",
                    allowed_mentions=SAFE_ALLOWED_MENTIONS,
                )
            else:
                await feedback_channel.send(
                    "Received an approved server build from the dashboard.",
                    allowed_mentions=SAFE_ALLOWED_MENTIONS,
                )

            success, result_message = await self._execute_build_plan(
                guild,
                feedback_channel,
                setup_plan,
                reset_server,
            )
            if job_id:
                await self.bot.db.update_build_job(
                    job_id,
                    "completed" if success else "failed",
                    result_message,
                )
        except Exception as error:
            log.exception("API build execution crashed for guild %s", guild.id)
            if job_id:
                await self.bot.db.update_build_job(
                    job_id,
                    "failed",
                    f"Build failed: {error}",
                )

    async def handle_bot_mention(self, message: discord.Message) -> bool:
        if self.bot.user in message.mentions:
            retry_after = self._consume_chat_cooldown(message.guild.id, message.author.id)
            if retry_after > 0:
                await message.channel.send(
                    f"Slow down! Try again in {retry_after:.0f}s.",
                    reference=message,
                    allowed_mentions=SAFE_ALLOWED_MENTIONS,
                )
                return True

            cleaned_message = message.content.replace(f"<@{self.bot.user.id}>", "").strip()
            if not cleaned_message:
                await message.channel.send(
                    "Hello there! How can I help you today?",
                    reference=message,
                    allowed_mentions=SAFE_ALLOWED_MENTIONS,
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

        async with self._get_channel_lock(channel_id):
            async with message.channel.typing():
                try:
                    chat = self.bot.chats[channel_id]
                    await self._manage_history(chat)
                    self._carry_thought_signatures(chat.history)
                    async with self.bot.gemini_semaphore:
                        # NOTE: Gemini 3 uses dynamic thinking by default and may include
                        # thoughtSignature parts. The ChatSession object manages these automatically.
                        # If you refactor to raw generate_content_async multi-turn calls, you MUST
                        # pass back thought signatures or response quality degrades.
                        response = await chat.send_message_async(prompt)
                    await message.channel.send(
                        response.text,
                        reference=message,
                        allowed_mentions=SAFE_ALLOWED_MENTIONS,
                    )
                except google_exceptions.ResourceExhausted:
                    msg = (
                        "The AI service is currently rate-limited. "
                        "Please wait 60 seconds and try again."
                    )
                    await message.channel.send(
                        msg,
                        reference=message,
                        allowed_mentions=SAFE_ALLOWED_MENTIONS,
                    )
                except google_exceptions.GoogleAPICallError as e:
                    msg = f"AI service returned an error: {getattr(e, 'message', str(e))}"
                    await message.channel.send(
                        msg,
                        reference=message,
                        allowed_mentions=SAFE_ALLOWED_MENTIONS,
                    )
                except Exception as e:
                    log.error("An error occurred with the AI chat: %s", e)
                    await message.channel.send(
                        "Sorry, I'm having trouble with the AI service right now.",
                        reference=message,
                        allowed_mentions=SAFE_ALLOWED_MENTIONS,
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
            return False, "Build failed: no feedback channel was available."

        async with self._get_guild_operation_lock(guild.id):
            if reset:
                await feedback_channel.send("**Step 1/3:** Wiping existing server structure...")
                for channel in guild.channels:
                    # Protect feedback_channel AND our persistent seromod-instructions control channel
                    if channel.id != feedback_channel.id and channel.name != "seromod-instructions":
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
                            await new_channel.send(
                                initial_message,
                                allowed_mentions=SAFE_ALLOWED_MENTIONS,
                            )
                        except discord.Forbidden:
                            pass

                completion_message = "Server setup complete!"
                await feedback_channel.send(f"**{completion_message}**")
                return True, completion_message
            except Exception as e:
                failure_message = f"Build failed: {e}"
                await feedback_channel.send(
                    f"An unexpected error occurred during build: {e}",
                    allowed_mentions=SAFE_ALLOWED_MENTIONS,
                )
                return False, failure_message

    async def handle_api_build_request(self, guild: discord.Guild, theme: str, reset_server: bool):
        theme = sanitize_prompt(theme)
        feedback_channel = await self._get_or_create_feedback_channel(guild)

        if not feedback_channel:
            log.error("API build request failed: bot could not find a channel in guild %s", guild.id)
            return

        await feedback_channel.send(
            f"Received `/buildserver` request from the web dashboard for theme: **'{theme}'**",
            allowed_mentions=SAFE_ALLOWED_MENTIONS,
        )

        try:
            setup_plan = await self.generate_build_plan(theme)
            await self._execute_build_plan(guild, feedback_channel, setup_plan, reset_server)
        except google_exceptions.ResourceExhausted:
            msg = (
                "The AI service is currently rate-limited. "
                "Please wait 60 seconds and try again."
            )
            await feedback_channel.send(f"[Warning] {msg}", allowed_mentions=SAFE_ALLOWED_MENTIONS)
        except google_exceptions.GoogleAPICallError as e:
            msg = f"AI service returned an error: {getattr(e, 'message', str(e))}"
            await feedback_channel.send(f"[Warning] {msg}", allowed_mentions=SAFE_ALLOWED_MENTIONS)
        except ValueError as e:
            await feedback_channel.send(str(e), allowed_mentions=SAFE_ALLOWED_MENTIONS)
        except Exception as e:
            log.error("An unexpected error occurred in API build request: %s", e)
            await feedback_channel.send(
                f"An unexpected error occurred: {e}",
                allowed_mentions=SAFE_ALLOWED_MENTIONS,
            )

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
You are an expert Discord server architect machine. Your response MUST be a single, raw, valid JSON object and nothing else. Do not include any commentary, explanations, or markdown formatting.

**USER REQUEST:** "Build a server for {theme}"
{variation_instruction}
**CRITICAL RULES:**
1.  Your entire response must be a single JSON object.
2.  The server structure MUST be extremely detailed, robust, and vibrant. An extensive and well-organized hierarchy of categories and numerous channels is required to fully capture the theme. A minimal plan is not acceptable.
3.  You MUST implement robust permission management. Create private/staff channels using the 'restricted' permission type, granting access to 'Admin' and 'Moderator' roles. Keep announcement or rules channels 'read-only' for the public. Protect sensible areas from general users.
4.  By default, you MUST include "Admin" and "Moderator" as the first two roles in the `roles` array for EVERY prompt, along with other highly creative, theme-specific roles.
5.  Channel names (`name` key) MUST be lowercase, use hyphens for spaces, and contain no special characters (e.g., "general-chat", "user-guides").
6.  Role names (`roles` key) can contain spaces and uppercase letters (e.g., "Team Captain").
7.  For `permissions` of type "restricted", the roles listed in the `allow` array MUST exactly match roles listed in the top-level `roles` array.

**JSON SCHEMA & LOGIC:**
- `roles`: (Required) `Array<String>`. A list of role names to create. Must absolutely include "Admin" and "Moderator" plus thematic variations.
- `plan`: (Required) `Array<Object>`. A highly-detailed, non-empty list of tasks.
  - `task`: `String`. Must be "create_category" or "create_channel".
  - `name`: `String`. The name of the category or channel. Must follow naming rules.
  - `category`: `String`. (Required for "create_channel") The `name` of a previously defined "create_category" task.
  - `channel_type`: `String`. (Required for "create_channel") Must be "text" or "voice".
  - `permissions`: `String` ("public" or "read-only") OR `Object` (`{{"type": "restricted", "allow": Array<String>}}`).
  - `topic`: `String`. (Optional, for `channel_type: "text"`) A vibrant, thematic short description of the channel. `voice` channels MUST NOT have this key.
  - `message`: `String`. (Optional, for `channel_type: "text"`) A customized, engaging welcome message explaining the channel. `voice` channels MUST NOT have this key.

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
