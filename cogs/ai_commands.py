import discord
from discord.ext import commands
from discord import app_commands, ui
import google.generativeai as genai
import json
import os
import asyncio
import re

# Using flash for a good balance of speed, capability, and cost.
model = genai.GenerativeModel('gemini-2.5-flash')

class ConfirmBuildView(ui.View):
    def __init__(self, interaction: discord.Interaction, setup_plan: dict, cog):
        super().__init__(timeout=180)  # 3-minute timeout
        self.interaction = interaction
        self.setup_plan = setup_plan
        self.cog = cog

    async def on_timeout(self):
        # Disable buttons on timeout
        for item in self.children:
            item.disabled = True
        try:
            await self.interaction.edit_original_response(content="⌛ Timed out. The build has been cancelled.", view=self)
        except discord.NotFound:
            pass # The original message might have been dismissed

    @ui.button(label="Confirm & Build", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: ui.Button):
        # Acknowledge the button press and disable the view
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        await self.interaction.edit_original_response(content="✅ Plan confirmed. Starting the build process...", view=self)
        
        # Execute the build plan
        await self.cog._execute_build_plan(self.interaction, self.setup_plan)
        self.stop()

    @ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: ui.Button):
        # Acknowledge and disable
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        await self.interaction.edit_original_response(content="❌ Build cancelled by user.", view=self)
        self.stop()

class AICommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.max_messages_to_keep = 10

    async def _manage_history(self, chat_session):
        history_length = len(chat_session.history)
        if history_length > self.max_messages_to_keep + 1:
            chat_session.history = [chat_session.history[0]] + chat_session.history[-(self.max_messages_to_keep):]
            print(f"Pruned chat history to {len(chat_session.history) - 1} messages.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if self.bot.user in message.mentions:
            cleaned_message = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
            if not cleaned_message:
                await message.channel.send("Hello there! How can I help you today?", reference=message)
                return
            await self.handle_chat_request(message, cleaned_message)

    async def handle_chat_request(self, message: discord.Message, prompt: str):
        channel_id = message.channel.id
        if channel_id not in self.bot.chats:
            self.bot.chats[channel_id] = model.start_chat(history=[{"role": "user", "parts": ["You are a friendly and helpful Discord bot named Cruxy..."]}])
        await message.channel.send("Thinking...", reference=message)
        try:
            chat = self.bot.chats[channel_id]
            await self._manage_history(chat)
            response = await chat.send_message_async(prompt)
            await message.channel.send(response.text, reference=message)
        except Exception as e:
            print(f"An error occurred with the AI chat: {e}")
            await message.channel.send("Sorry, I'm having trouble with the AI service right now.", reference=message)

    def _format_plan_embed(self, theme: str, setup_plan: dict) -> discord.Embed:
        initial_description = f"Here is the plan my AI generated for the theme: **'{theme}'**.\nPlease review the changes below and confirm to proceed."
        
        embed = discord.Embed(
            title="Server Build Plan Preview",
            description=initial_description,
            color=discord.Color.blue()
        )

        roles = setup_plan.get('roles', [])
        if roles:
            embed.add_field(name="🔑 Roles to be Created", value="> " + "\n> ".join(f"`{role}`" for role in roles), inline=False)
        else:
            embed.add_field(name="🔑 Roles to be Created", value="> None", inline=False)

        structure_text = ""
        for task in setup_plan.get('plan', []):
            if task['task'] == 'create_category':
                structure_text += f"\n📁 **{task['name']}**\n"
            elif task['task'] == 'create_channel':
                perms = task.get('permissions', 'public')
                perm_text = ""
                if isinstance(perms, dict) and perms.get('type') == 'restricted':
                    allowed = perms.get('allow', [])
                    perm_text = f" (🔒 Restricted to: {', '.join(f'`{r}`' for r in allowed)})"
                elif perms == 'read-only':
                    perm_text = " (📢 Read-Only)"
                
                structure_text += f"  - # {task['name']}{perm_text}\n"

        if structure_text:
            final_description = embed.description + "\n\n**📂 Server Structure**" + structure_text
            
            if len(final_description) > 4096:
                final_description = final_description[:4090] + "\n..."
            
            embed.description = final_description
            
        embed.set_footer(text="The build will be cancelled automatically in 3 minutes if you don't respond.")
        return embed

    async def _execute_build_plan(self, interaction: discord.Interaction, setup_plan: dict):
        created_roles, created_categories, guild = {}, {}, interaction.guild
        try:
            role_names_to_create = setup_plan.get('roles', [])
            if role_names_to_create:
                await interaction.followup.send(f"**Step 1/2:** Creating roles: {', '.join(f'`{r}`' for r in role_names_to_create)}...", ephemeral=True)
                for role_name in role_names_to_create:
                    if existing_role := discord.utils.get(guild.roles, name=role_name):
                        created_roles[role_name] = existing_role
                    else:
                        created_roles[role_name] = await guild.create_role(name=role_name, reason="AI Server Build")
                await asyncio.sleep(1)
            await interaction.followup.send("**Step 2/2:** Creating categories and channels...", ephemeral=True)
            for task in setup_plan.get('plan', []):
                task_name, name = task.get('task'), task.get('name')
                if task_name == "create_category":
                    created_categories[name] = await guild.create_category(name, reason="AI Server Build")
                elif task_name == "create_channel":
                    category, overwrites = created_categories.get(task.get('category')), {}
                    perms_type = task.get('permissions', 'public')
                    if perms_type == "read-only":
                        overwrites[guild.default_role] = discord.PermissionOverwrite(send_messages=False)
                    elif isinstance(perms_type, dict) and perms_type.get('type') == 'restricted':
                        overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
                        overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True)
                        for role_name in perms_type.get('allow', []):
                            if role_obj := created_roles.get(role_name):
                                overwrites[role_obj] = discord.PermissionOverwrite(view_channel=True)
                    await guild.create_text_channel(name, category=category, overwrites=overwrites, reason="AI Server Build")
            await interaction.followup.send("✅ **Server setup complete!**", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ **Permission Error!** I need 'Manage Roles' and 'Manage Channels' permissions.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An unexpected error occurred during build: {e}", ephemeral=True)

    @app_commands.command(name="buildserver", description="Build a server structure based on a theme using AI.")
    @app_commands.describe(theme="The theme for the server (e.g., 'A high-tech startup')")
    @app_commands.checks.has_permissions(administrator=True)
    async def build_server_command(self, interaction: discord.Interaction, theme: str):
        await interaction.response.defer(ephemeral=True, thinking=True)

        setup_prompt = f"""
You are an API endpoint that generates a JSON object for building a Discord server structure. Your response must be a single, raw, valid JSON object and nothing else.

**CRITICAL RULE:** You **MUST** generate a plan. An empty `plan` array (`[]`) is considered a failure and is not a valid response. Be creative and comprehensive. A minimal or empty plan is not acceptable.

If the user provides a theme of a real-world company or brand, create a generic server inspired by that theme for fans or professionals in that industry.

**USER REQUEST:** "Build a server for {theme}"

**TASK:**
1.  Invent a list of relevant Discord role names for the theme.
2.  Design a full structure of categories and channels. You must create at least one category and two channels.
3.  Assign permissions to each channel, restricting some channels to the roles you invented.

**JSON SCHEMA:**
- The root must be an object.
- It can contain an optional key: "roles" (a list of strings).
- It must contain a required key: "plan" (a list of objects). This list cannot be empty.
- Each object in the "plan" list must have:
  - "task": A string, "create_category" or "create_channel".
  - "name": A string for the channel or category name.
  - "category": (Required for "create_channel") A string matching the name of a previously created category.
  - "permissions": Can be one of three types: "public", "read-only", or an object: `{{"type": "restricted", "allow": ["RoleName1", "RoleName2"]}}`.
"""
        try:
            response = await model.generate_content_async(setup_prompt)

            if not response.parts:
                block_reason = response.prompt_feedback.block_reason.name if response.prompt_feedback.block_reason else "Unknown"
                await interaction.followup.send(
                    f"❌ **Request Blocked by AI Safety Filter**\n"
                    f"> **Reason:** `{block_reason}`\n"
                    f"> This can happen with themes related to sensitive topics. Please try a different theme.",
                    ephemeral=True
                )
                return

            ai_response_text = response.text
            
            if not ai_response_text:
                await interaction.followup.send("❌ The AI generated an empty response. This may be a temporary issue. Please try again.", ephemeral=True)
                return

            json_match = re.search(r"\{.*\}", ai_response_text, re.DOTALL)
            if not json_match:
                await interaction.followup.send("❌ The AI's response was not in the correct format (could not find JSON).", ephemeral=True)
                return
            
            json_string = json_match.group(0)
            setup_plan = json.loads(json_string)

            if not setup_plan or not setup_plan.get('plan'):
                await interaction.followup.send(
                    "❌ The AI chose not to generate a server plan for that theme.\n"
                    "> This can happen with very specific or ambiguous topics. Please try rephrasing your theme.",
                    ephemeral=True
                )
                return
            
            preview_embed = self._format_plan_embed(theme, setup_plan)
            confirmation_view = ConfirmBuildView(interaction, setup_plan, self)
            await interaction.followup.send(embed=preview_embed, view=confirmation_view, ephemeral=True)

        except json.JSONDecodeError:
            await interaction.followup.send("❌ The AI's response was not valid JSON and could not be read.", ephemeral=True)
        except Exception as e:
            print(f"An unexpected error occurred in buildserver: {e}")
            await interaction.followup.send(f"An unexpected error occurred: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AICommands(bot))