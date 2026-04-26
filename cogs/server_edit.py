import asyncio
import json
import logging
import os
import re

import discord
import google.api_core.exceptions as google_exceptions
import google.generativeai as genai
from discord import app_commands
from discord.ext import commands
from thefuzz import process

from utils.sanitize import sanitize_prompt

log = logging.getLogger(__name__)
model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"))
SAFE_ALLOWED_MENTIONS = discord.AllowedMentions.none()
CHANNEL_NAME_RE = re.compile(r"^[a-z0-9-]{1,48}$")
CATEGORY_NAME_RE = re.compile(r"^[A-Za-z0-9 _.\-]{1,80}$")


class AIEditCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.max_edit_actions = max(1, int(os.getenv("MAX_EDIT_ACTIONS", "25")))

    def _build_edit_prompt(self, request: str, server_structure: dict) -> str:
        request = sanitize_prompt(request)
        return f"""
You are a server management API that translates natural language requests into a structured JSON plan for managing channels and categories. Your only output must be a raw JSON object.

**CURRENT SERVER STRUCTURE:**
{json.dumps(server_structure, indent=2)}

**USER REQUEST:** "{request}"

**TASK:** Analyze the user's request and the current server structure. Generate a JSON plan with a list of "actions".

**VALID ACTIONS & SCHEMA:**
- `{{"action": "rename_channel", "current_name": "old-name", "new_name": "new-name"}}`
- `{{"action": "delete_channel", "name": "channel-to-delete"}}`
- `{{"action": "create_channel", "name": "new-channel-name", "category": "Category Name", "type": "text_or_voice"}}`
- `{{"action": "rename_category", "current_name": "Old Name", "new_name": "New Name"}}`
- `{{"action": "delete_category", "name": "category-to-delete"}}`

**CRITICAL RULE:**
For `create_channel`, the `type` key must be either "text" or "voice".

**EXAMPLE:**
If the request is "change general to lounge and delete the art-gallery channel", the output should be:
{{
    "plan": [
        {{"action": "rename_channel", "current_name": "general", "new_name": "lounge"}},
        {{"action": "delete_channel", "name": "art-gallery"}}
    ]
}}

Generate the JSON plan now.
"""

    def _extract_plan(self, text: str):
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

    def _get_guild_operation_lock(self, guild_id: int) -> asyncio.Lock:
        lock = self.bot.guild_operation_locks.get(guild_id)
        if lock is None:
            lock = asyncio.Lock()
            self.bot.guild_operation_locks[guild_id] = lock
        return lock

    def _validate_channel_name(self, value: str, *, field_name: str) -> str:
        cleaned_value = sanitize_prompt(value, max_length=48).lower().strip()
        if not CHANNEL_NAME_RE.fullmatch(cleaned_value):
            raise ValueError(f"{field_name} must be a lowercase Discord channel name.")
        return cleaned_value

    def _validate_category_name(self, value: str, *, field_name: str) -> str:
        cleaned_value = sanitize_prompt(value, max_length=80).strip()
        if not CATEGORY_NAME_RE.fullmatch(cleaned_value):
            raise ValueError(f"{field_name} contains invalid characters.")
        return cleaned_value

    def _validate_edit_plan(self, plan: dict) -> dict:
        if not isinstance(plan, dict):
            raise ValueError("The AI returned an invalid edit plan.")

        raw_actions = plan.get("plan")
        if not isinstance(raw_actions, list) or not raw_actions:
            raise ValueError("The AI did not return a valid edit plan.")
        if len(raw_actions) > self.max_edit_actions:
            raise ValueError("The AI returned too many edit actions at once.")

        validated_actions = []
        for raw_action in raw_actions:
            if not isinstance(raw_action, dict):
                raise ValueError("The AI returned malformed edit actions.")

            action = str(raw_action.get("action", "")).strip()
            if action == "rename_channel":
                validated_actions.append(
                    {
                        "action": action,
                        "current_name": self._validate_channel_name(
                            str(raw_action.get("current_name", "")),
                            field_name="current_name",
                        ),
                        "new_name": self._validate_channel_name(
                            str(raw_action.get("new_name", "")),
                            field_name="new_name",
                        ),
                    }
                )
            elif action == "delete_channel":
                validated_actions.append(
                    {
                        "action": action,
                        "name": self._validate_channel_name(
                            str(raw_action.get("name", "")),
                            field_name="name",
                        ),
                    }
                )
            elif action == "create_channel":
                channel_type = str(raw_action.get("type", "text")).strip().lower()
                if channel_type not in {"text", "voice"}:
                    raise ValueError("Channel type must be text or voice.")
                category_name = sanitize_prompt(raw_action.get("category", ""), max_length=80).strip()
                validated_actions.append(
                    {
                        "action": action,
                        "name": self._validate_channel_name(
                            str(raw_action.get("name", "")),
                            field_name="name",
                        ),
                        "category": self._validate_category_name(
                            category_name,
                            field_name="category",
                        ) if category_name else None,
                        "type": channel_type,
                    }
                )
            elif action == "rename_category":
                validated_actions.append(
                    {
                        "action": action,
                        "current_name": self._validate_category_name(
                            str(raw_action.get("current_name", "")),
                            field_name="current_name",
                        ),
                        "new_name": self._validate_category_name(
                            str(raw_action.get("new_name", "")),
                            field_name="new_name",
                        ),
                    }
                )
            elif action == "delete_category":
                validated_actions.append(
                    {
                        "action": action,
                        "name": self._validate_category_name(
                            str(raw_action.get("name", "")),
                            field_name="name",
                        ),
                    }
                )
            else:
                raise ValueError(f"Unsupported edit action: {action}")

        return {"plan": validated_actions}

    async def _execute_edit_plan(self, guild, channel, plan):
        actions_taken = []
        feedback_messages = []

        async with self._get_guild_operation_lock(guild.id):
            for task in plan.get("plan", []):
                action = task.get("action")

                if action == "create_channel":
                    all_channels = [existing_channel.name for existing_channel in guild.channels]
                    new_name = task.get("name")
                    match = process.extractOne(new_name, all_channels, score_cutoff=90)
                    if match:
                        feedback_messages.append(
                            f"A channel named `{match[0]}` already exists. I skipped creating `{new_name}` to avoid a duplicate."
                        )
                        continue

                try:
                    if action == "rename_channel":
                        if task.get("current_name") == "seromod-instructions":
                            feedback_messages.append("Skipped renaming of protected `seromod-instructions` channel.")
                            continue
                        target_channel = discord.utils.get(guild.channels, name=task.get("current_name"))
                        if target_channel:
                            await target_channel.edit(
                                name=task.get("new_name"),
                                reason="Seromod Edit",
                            )
                            actions_taken.append(
                                f"Renamed channel `{task.get('current_name')}` to `{task.get('new_name')}`."
                            )

                    elif action == "delete_channel":
                        if task.get("name") == "seromod-instructions":
                            feedback_messages.append("Skipped deletion of protected `seromod-instructions` channel.")
                            continue
                        target_channel = discord.utils.get(guild.channels, name=task.get("name"))
                        if target_channel:
                            await target_channel.delete(reason="Seromod Edit")
                            actions_taken.append(f"Deleted channel `{task.get('name')}`.")

                    elif action == "create_channel":
                        category = discord.utils.get(guild.categories, name=task.get("category"))
                        channel_name = task.get("name")
                        channel_type = task.get("type", "text")
                        if channel_type == "voice":
                            await guild.create_voice_channel(
                                name=channel_name,
                                category=category,
                                reason="Seromod Edit",
                            )
                        else:
                            await guild.create_text_channel(
                                name=channel_name,
                                category=category,
                                reason="Seromod Edit",
                            )
                        actions_taken.append(
                            f"Created {channel_type} channel `#{channel_name}` in category "
                            f"`{category.name if category else 'None'}`."
                        )

                    elif action == "rename_category":
                        category = discord.utils.get(guild.categories, name=task.get("current_name"))
                        if category:
                            await category.edit(
                                name=task.get("new_name"),
                                reason="Seromod Edit",
                            )
                            actions_taken.append(
                                f"Renamed category `{task.get('current_name')}` to `{task.get('new_name')}`."
                            )

                    elif action == "delete_category":
                        category = discord.utils.get(guild.categories, name=task.get("name"))
                        if category:
                            skipped_protected = False
                            for existing_channel in list(category.channels):
                                if existing_channel.name == "seromod-instructions":
                                    skipped_protected = True
                                    continue
                                try:
                                    await existing_channel.delete(reason="Seromod Edit")
                                except (discord.Forbidden, discord.HTTPException) as error:
                                    feedback_messages.append(
                                        f"Could not delete channel `{existing_channel.name}` in category `{category.name}`: {error}"
                                    )
                            try:
                                if skipped_protected:
                                    feedback_messages.append("Skipped deletion of protected `seromod-instructions` channel inside category.")
                                    actions_taken.append(f"Deleted unprotected channels in category `{task.get('name')}`.")
                                else:
                                    await category.delete(reason="Seromod Edit")
                                    actions_taken.append(
                                        f"Deleted category `{task.get('name')}` and its channels."
                                    )
                            except (discord.Forbidden, discord.HTTPException) as error:
                                feedback_messages.append(
                                    f"Could not delete category `{category.name}`: {error}"
                                )
                except (discord.Forbidden, discord.HTTPException) as error:
                    feedback_messages.append(
                        f"Lacked permissions for action `{action}` on "
                        f"`{task.get('name') or task.get('current_name')}`: {error}"
                    )
                except Exception as error:
                    feedback_messages.append(f"An error occurred with action `{action}`: {error}")

        final_message = ""
        if actions_taken:
            final_message += "Actions Complete:\n- " + "\n- ".join(actions_taken)
        if feedback_messages:
            if final_message:
                final_message += "\n\n"
            final_message += "Notifications:\n- " + "\n- ".join(feedback_messages)
        if not final_message:
            final_message = (
                "I understood your request, but I couldn't find any valid actions "
                "to take based on the current server state."
            )

        await channel.send(final_message, allowed_mentions=SAFE_ALLOWED_MENTIONS)

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
                for ch in guild.text_channels:
                    if ch.permissions_for(guild.me).send_messages:
                        return ch
                return None
        return channel

    async def handle_api_edit_request(self, guild, request: str):
        channel = await self._get_or_create_feedback_channel(guild)
        if not channel:
            log.error("No channel found to send server edit feedback for guild %s", guild.id)
            return

        request = sanitize_prompt(request)
        await channel.send(
            f"Received API request to edit the server: **'{request}'**. Generating plan...",
            allowed_mentions=SAFE_ALLOWED_MENTIONS,
        )

        server_structure = {
            "categories": [category.name for category in guild.categories],
            "text_channels": [text_channel.name for text_channel in guild.text_channels],
            "voice_channels": [voice_channel.name for voice_channel in guild.voice_channels],
        }
        edit_prompt = self._build_edit_prompt(request, server_structure)

        try:
            async with self.bot.gemini_semaphore:
                # NOTE: Gemini 3 uses dynamic thinking by default and may include
                # thoughtSignature parts. The ChatSession object manages these automatically.
                # If you refactor to raw generate_content_async multi-turn calls, you MUST
                # pass back thought signatures or response quality degrades.
                response = await model.generate_content_async(edit_prompt)
            plan = self._extract_plan(response.text)
            if not plan:
                await channel.send(
                    "The AI did not return a valid plan. Please try rephrasing your request.",
                    allowed_mentions=SAFE_ALLOWED_MENTIONS,
                )
                return

            validated_plan = self._validate_edit_plan(plan)
            await channel.send("AI plan generated. Now executing changes...")
            await self._execute_edit_plan(guild, channel, validated_plan)
        except google_exceptions.ResourceExhausted:
            msg = (
                "The AI service is currently rate-limited. "
                "Please wait 60 seconds and try again."
            )
            await channel.send(f"[Warning] {msg}", allowed_mentions=SAFE_ALLOWED_MENTIONS)
        except google_exceptions.GoogleAPICallError as error:
            msg = f"AI service returned an error: {getattr(error, 'message', str(error))}"
            await channel.send(f"[Warning] {msg}", allowed_mentions=SAFE_ALLOWED_MENTIONS)
        except ValueError as error:
            await channel.send(str(error), allowed_mentions=SAFE_ALLOWED_MENTIONS)
        except json.JSONDecodeError:
            await channel.send(
                "The AI returned invalid JSON while processing your request.",
                allowed_mentions=SAFE_ALLOWED_MENTIONS,
            )
        except Exception as error:
            log.error("Error in API /serveredit: %s", error)
            await channel.send(
                f"An unexpected error occurred while processing your request: {error}",
                allowed_mentions=SAFE_ALLOWED_MENTIONS,
            )

    @app_commands.command(
        name="serveredit",
        description="Make changes to channels and categories using natural language.",
    )
    @app_commands.describe(request="Describe the changes you want to make (e.g., 'rename general to lounge').")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    async def server_edit(self, interaction: discord.Interaction, request: str):
        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild
        request = sanitize_prompt(request)

        server_structure = {
            "categories": [category.name for category in guild.categories],
            "text_channels": [text_channel.name for text_channel in guild.text_channels],
            "voice_channels": [voice_channel.name for voice_channel in guild.voice_channels],
        }
        edit_prompt = self._build_edit_prompt(request, server_structure)

        try:
            async with self.bot.gemini_semaphore:
                # NOTE: Gemini 3 uses dynamic thinking by default and may include
                # thoughtSignature parts. The ChatSession object manages these automatically.
                # If you refactor to raw generate_content_async multi-turn calls, you MUST
                # pass back thought signatures or response quality degrades.
                response = await model.generate_content_async(edit_prompt)
            plan = self._extract_plan(response.text)
            if not plan:
                await interaction.followup.send(
                    "The AI did not return a valid plan. Please try rephrasing your request.",
                    ephemeral=True,
                )
                return

            validated_plan = self._validate_edit_plan(plan)
            await interaction.followup.send(
                "AI plan generated. Now executing changes in this channel...",
                ephemeral=True,
            )
            await self._execute_edit_plan(guild, interaction.channel, validated_plan)
        except google_exceptions.ResourceExhausted:
            msg = (
                "The AI service is currently rate-limited. "
                "Please wait 60 seconds and try again."
            )
            await interaction.followup.send(msg, ephemeral=True)
        except google_exceptions.GoogleAPICallError as error:
            msg = f"AI service returned an error: {getattr(error, 'message', str(error))}"
            await interaction.followup.send(msg, ephemeral=True)
        except ValueError as error:
            await interaction.followup.send(str(error), ephemeral=True)
        except json.JSONDecodeError:
            await interaction.followup.send(
                "The AI returned invalid JSON while processing your request.",
                ephemeral=True,
            )
        except Exception as error:
            log.error("Error in /serveredit: %s", error)
            await interaction.followup.send(
                f"An unexpected error occurred while processing your request: {error}",
                ephemeral=True,
            )

    @server_edit.error
    async def on_server_edit_cooldown_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CommandOnCooldown):
            message = f"Slow down! Try again in {error.retry_after:.0f}s."
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AIEditCommands(bot))
