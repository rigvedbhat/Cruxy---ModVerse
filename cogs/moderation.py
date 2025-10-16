import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from better_profanity import profanity
import asyncio

DB_PATH = "moderation.db"

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        profanity.load_censor_words()

    async def ensure_tables(self):
        """Ensure required tables exist before any DB operation"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS warnings (
                    guild_id INTEGER,
                    user_id INTEGER,
                    warnings INTEGER,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    guild_id INTEGER PRIMARY KEY,
                    warning_limit INTEGER DEFAULT 3,
                    punishment_type TEXT DEFAULT 'mute',
                    mute_duration INTEGER DEFAULT 10
                )
            """)
            await db.commit()

    @app_commands.command(name="set_moderation", description="Configure profanity moderation settings")
    @app_commands.describe(
        warning_limit="Number of warnings before punishment (1-10)",
        punishment_type="Type of punishment to apply",
        mute_duration="Mute duration in minutes (only for 'mute')"
    )
    @app_commands.choices(
        punishment_type=[
            app_commands.Choice(name="Mute", value="mute"),
            app_commands.Choice(name="Kick", value="kick"),
            app_commands.Choice(name="Ban", value="ban"),
        ]
    )
    async def set_moderation(
        self,
        interaction: discord.Interaction,
        warning_limit: int,
        punishment_type: app_commands.Choice[str],
        mute_duration: int
    ):
        await self.ensure_tables()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO settings (guild_id, warning_limit, punishment_type, mute_duration)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    warning_limit = excluded.warning_limit,
                    punishment_type = excluded.punishment_type,
                    mute_duration = excluded.mute_duration
            """, (interaction.guild.id, warning_limit, punishment_type.value, mute_duration))
            await db.commit()

        await interaction.response.send_message(
            f"✅ Settings updated:\n"
            f"• Warning limit: **{warning_limit}**\n"
            f"• Punishment: **{punishment_type.name}**\n"
            f"• Mute duration: **{mute_duration} minutes**",
            ephemeral=True
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        if profanity.contains_profanity(message.content):
            await self.ensure_tables()
            guild_id = message.guild.id
            user_id = message.author.id

            async with aiosqlite.connect(DB_PATH) as db:
                # Get current warnings
                async with db.execute(
                    "SELECT warnings FROM warnings WHERE guild_id = ? AND user_id = ?",
                    (guild_id, user_id)
                ) as cursor:
                    row = await cursor.fetchone()
                current_warnings = row[0] if row else 0
                new_warnings = current_warnings + 1

                # Update warning count
                await db.execute("""
                    INSERT INTO warnings (guild_id, user_id, warnings)
                    VALUES (?, ?, ?)
                    ON CONFLICT(guild_id, user_id)
                    DO UPDATE SET warnings = excluded.warnings
                """, (guild_id, user_id, new_warnings))

                # Get server settings
                async with db.execute(
                    "SELECT warning_limit, punishment_type, mute_duration FROM settings WHERE guild_id = ?",
                    (guild_id,)
                ) as cursor:
                    settings_row = await cursor.fetchone()
                if settings_row:
                    warning_limit, punishment_type, mute_duration = settings_row
                else:
                    warning_limit, punishment_type, mute_duration = 3, "mute", 10

                await db.commit()

            await message.channel.send(
                f"⚠️ {message.author.mention}, watch your language! "
                f"You now have **{new_warnings}/{warning_limit}** warnings."
            )

            if new_warnings >= warning_limit:
                if punishment_type == "mute":
                    await self.mute_user(message, mute_duration)
                elif punishment_type == "kick":
                    await message.author.kick(reason="Exceeded profanity warning limit")
                    await message.channel.send(f"👢 {message.author.mention} has been kicked for repeated profanity.")
                elif punishment_type == "ban":
                    await message.guild.ban(message.author, reason="Exceeded profanity warning limit")
                    await message.channel.send(f"🔨 {message.author.mention} has been banned for repeated profanity.")

                # Reset warnings
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute("DELETE FROM warnings WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
                    await db.commit()

    async def mute_user(self, message, duration):
        guild = message.guild
        mute_role = discord.utils.get(guild.roles, name="Muted")
        if not mute_role:
            mute_role = await guild.create_role(name="Muted", permissions=discord.Permissions(send_messages=False, speak=False))
            for channel in guild.channels:
                await channel.set_permissions(mute_role, send_messages=False, speak=False)

        await message.author.add_roles(mute_role)
        await message.channel.send(f"🔇 {message.author.mention} has been muted for **{duration} minutes**.")
        await asyncio.sleep(duration * 60)
        if mute_role in message.author.roles:
            await message.author.remove_roles(mute_role)
            await message.channel.send(f"✅ {message.author.mention} has been unmuted.")

    # ---------- Text Commands ----------
    @commands.command(name="warnings")
    @commands.has_permissions(kick_members=True)
    async def check_warnings(self, ctx, member: discord.Member):
        await self.ensure_tables()
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT warnings FROM warnings WHERE guild_id = ? AND user_id = ?",
                (ctx.guild.id, member.id)
            ) as cursor:
                row = await cursor.fetchone()
            count = row[0] if row else 0
        await ctx.send(f"{member.display_name} has **{count} warning(s)**.")

    @commands.command(name="resetwarnings")
    @commands.has_permissions(kick_members=True)
    async def reset_warnings(self, ctx, member: discord.Member):
        await self.ensure_tables()
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "DELETE FROM warnings WHERE guild_id = ? AND user_id = ?",
                (ctx.guild.id, member.id)
            )
            await db.commit()
        await ctx.send(f"✅ Warnings for {member.display_name} have been reset.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
