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


class AIEditCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

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
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if not json_match:
            return None
        return json.loads(json_match.group(0))

    async def _execute_edit_plan(self, guild, channel, plan):
        actions_taken = []
        feedback_messages = []

        for task in plan.get("plan", []):
            action = task.get("action")

            if action == "create_channel":
                all_channels = [c.name for c in guild.channels]
                new_name = task.get("name")
                match = process.extractOne(new_name, all_channels, score_cutoff=90)
                if match:
                    feedback_messages.append(
                        f"A channel named `{match[0]}` already exists. I skipped creating `{new_name}` to avoid a duplicate."
                    )
                    continue

            try:
                if action == "rename_channel":
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
                        await category.delete(reason="Seromod Edit")
                        actions_taken.append(f"Deleted category `{task.get('name')}`.")
            except discord.Forbidden:
                feedback_messages.append(
                    f"Lacked permissions for action `{action}` on "
                    f"`{task.get('name') or task.get('current_name')}`."
                )
            except Exception as e:
                feedback_messages.append(f"An error occurred with action `{action}`: {e}")

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

        await channel.send(final_message)

    async def handle_api_edit_request(self, guild, channel, request: str):
        request = sanitize_prompt(request)
        await channel.send(
            f"Received API request to edit the server: **'{request}'**. Generating plan..."
        )

        server_structure = {
            "categories": [c.name for c in guild.categories],
            "text_channels": [c.name for c in guild.text_channels],
            "voice_channels": [c.name for c in guild.voice_channels],
        }
        edit_prompt = self._build_edit_prompt(request, server_structure)

        try:
            async with self.bot.gemini_semaphore:
                response = await model.generate_content_async(edit_prompt)
            plan = self._extract_plan(response.text)
            if not plan:
                await channel.send("The AI did not return a valid plan. Please try rephrasing your request.")
                return

            await channel.send("AI plan generated. Now executing changes...")
            await self._execute_edit_plan(guild, channel, plan)
        except google_exceptions.ResourceExhausted:
            msg = (
                "The AI service is currently rate-limited. "
                "Please wait 60 seconds and try again."
            )
            await channel.send(f"⚠️ {msg}")
        except google_exceptions.GoogleAPICallError as e:
            msg = f"AI service returned an error: {getattr(e, 'message', str(e))}"
            await channel.send(f"⚠️ {msg}")
        except json.JSONDecodeError:
            await channel.send("The AI returned invalid JSON while processing your request.")
        except Exception as e:
            log.error("Error in API /serveredit: %s", e)
            await channel.send(f"An unexpected error occurred while processing your request: {e}")

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
            "categories": [c.name for c in guild.categories],
            "text_channels": [c.name for c in guild.text_channels],
            "voice_channels": [c.name for c in guild.voice_channels],
        }
        edit_prompt = self._build_edit_prompt(request, server_structure)

        try:
            async with self.bot.gemini_semaphore:
                response = await model.generate_content_async(edit_prompt)
            plan = self._extract_plan(response.text)
            if not plan:
                await interaction.followup.send(
                    "The AI did not return a valid plan. Please try rephrasing your request.",
                    ephemeral=True,
                )
                return

            await interaction.followup.send(
                "AI plan generated. Now executing changes in this channel...",
                ephemeral=True,
            )
            await self._execute_edit_plan(guild, interaction.channel, plan)
        except google_exceptions.ResourceExhausted:
            msg = (
                "The AI service is currently rate-limited. "
                "Please wait 60 seconds and try again."
            )
            await interaction.followup.send(msg, ephemeral=True)
        except google_exceptions.GoogleAPICallError as e:
            msg = f"AI service returned an error: {getattr(e, 'message', str(e))}"
            await interaction.followup.send(msg, ephemeral=True)
        except json.JSONDecodeError:
            await interaction.followup.send(
                "The AI returned invalid JSON while processing your request.",
                ephemeral=True,
            )
        except Exception as e:
            log.error("Error in /serveredit: %s", e)
            await interaction.followup.send(
                f"An unexpected error occurred while processing your request: {e}",
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
