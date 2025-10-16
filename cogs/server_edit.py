import discord
from discord.ext import commands
from discord import app_commands, ui
import google.generativeai as genai
import json
import asyncio
import re
from thefuzz import process

model = genai.GenerativeModel('gemini-2.5-flash')

class AIEditCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="serveredit", description="Make changes to channels and categories using natural language.")
    @app_commands.describe(request="Describe the changes you want to make (e.g., 'rename general to lounge').")
    @app_commands.checks.has_permissions(administrator=True)
    async def server_edit(self, interaction: discord.Interaction, request: str):
        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild

        # Simplified server structure, no longer includes roles
        server_structure = {
            "categories": [c.name for c in guild.categories],
            "text_channels": [c.name for c in guild.text_channels],
            "voice_channels": [c.name for c in guild.voice_channels],
        }

        # Simplified prompt, focused only on channel/category management
        edit_prompt = f"""
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
        
        try:
            response = await model.generate_content_async(edit_prompt)
            json_match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if not json_match:
                await interaction.followup.send("❌ The AI did not return a valid plan. Please try rephrasing your request.", ephemeral=True)
                return
            
            plan = json.loads(json_match.group(0))
            
            actions_taken = []
            feedback_messages = []

            for task in plan.get("plan", []):
                action = task.get("action")
                
                if action == "create_channel":
                    all_channels = [c.name for c in guild.channels]
                    new_name = task.get("name")
                    match = process.extractOne(new_name, all_channels, score_cutoff=90)
                    if match:
                        feedback_messages.append(f"⚠️ A channel named `{match[0]}` already exists. I skipped creating `{new_name}` to avoid a duplicate.")
                        continue

                # --- EXECUTION LOGIC ---
                if action == "rename_channel":
                    channel = discord.utils.get(guild.channels, name=task.get("current_name"))
                    if channel:
                        await channel.edit(name=task.get("new_name"), reason="Crux AI Edit")
                        actions_taken.append(f"Renamed channel `{task.get('current_name')}` to `{task.get('new_name')}`.")
                
                elif action == "delete_channel":
                    channel = discord.utils.get(guild.channels, name=task.get("name"))
                    if channel:
                        await channel.delete(reason="Crux AI Edit")
                        actions_taken.append(f"Deleted channel `{task.get('name')}`.")
                
                elif action == "create_channel":
                    category = discord.utils.get(guild.categories, name=task.get("category"))
                    channel_name = task.get("name")
                    channel_type = task.get("type", "text")
                    if channel_type == "voice":
                        await guild.create_voice_channel(name=channel_name, category=category, reason="Crux AI Edit")
                    else:
                        await guild.create_text_channel(name=channel_name, category=category, reason="Crux AI Edit")
                    actions_taken.append(f"Created {channel_type} channel `#{channel_name}` in category `{category.name if category else 'None'}`.")

                elif action == "rename_category":
                    category = discord.utils.get(guild.categories, name=task.get("current_name"))
                    if category:
                        await category.edit(name=task.get("new_name"), reason="Crux AI Edit")
                        actions_taken.append(f"Renamed category `{task.get('current_name')}` to `{task.get('new_name')}`.")

                elif action == "delete_category":
                    category = discord.utils.get(guild.categories, name=task.get("name"))
                    if category:
                        await category.delete(reason="Crux AI Edit")
                        actions_taken.append(f"Deleted category `{task.get('name')}`.")

            # --- FINAL FEEDBACK ---
            final_message = ""
            if actions_taken:
                final_message += "✅ **Actions Complete:**\n- " + "\n- ".join(actions_taken)
            if feedback_messages:
                if final_message: final_message += "\n\n"
                final_message += "ℹ️ **Notifications:**\n- " + "\n- ".join(feedback_messages)
            if not final_message:
                final_message = "I understood your request, but I couldn't find any valid actions to take based on the current server state."
            await interaction.followup.send(final_message, ephemeral=True)

        except Exception as e:
            print(f"Error in /serveredit: {e}")
            await interaction.followup.send(f"An unexpected error occurred while processing your request: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AIEditCommands(bot))

