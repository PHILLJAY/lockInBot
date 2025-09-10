"""
User management commands for the Discord Task Reminder Bot.
"""

import logging
from datetime import datetime
from typing import Optional
import pytz
import discord
from discord.ext import commands
from discord import app_commands
from sqlalchemy import select

from database.connection import get_db_manager
from database.models import User

logger = logging.getLogger(__name__)


class UserCommands(commands.Cog):
    """Commands for user registration and profile management."""

    def __init__(self, bot):
        """Initialize the user commands cog."""
        self.bot = bot

    @app_commands.command(
        name="start", description="Start your journey with Bakushin AI"
    )
    async def start_command(self, interaction: discord.Interaction):
        """Initialize DM conversation with user"""
        await interaction.response.defer(ephemeral=True)

        try:
            # Try to send a DM to the user
            try:
                dm_channel = await interaction.user.create_dm()

                # Check if user can receive DMs by sending a test message
                await dm_channel.send("yooo testing if you can get DMs...")

                # If successful, start the conversation
                dm_manager = self.bot.get_dm_conversation_manager()

                # Create a mock message for the conversation manager
                class MockMessage:
                    def __init__(self, user, channel, content):
                        self.author = user
                        self.channel = channel
                        self.content = content

                mock_message = MockMessage(interaction.user, dm_channel, "/start")
                await dm_manager.handle_dm_message(mock_message)

                # Send confirmation in server
                await interaction.followup.send(
                    "✅ Check your DMs! I've started a conversation with you there.\n"
                    "That's where we'll set up your tasks and I'll send your reminders! 💪",
                    ephemeral=True,
                )

            except discord.Forbidden:
                # User has DMs disabled
                await interaction.followup.send(
                    "❌ I can't send you DMs! Here's how to fix it:\n\n"
                    "1. Go to **User Settings** (gear icon)\n"
                    "2. Click **Privacy & Safety**\n"
                    "3. Enable **Allow direct messages from server members**\n"
                    "4. Try `/start` again!\n\n"
                    "I need DMs to have proper conversations with you about your goals 💬",
                    ephemeral=True,
                )

        except Exception as e:
            logger.error(f"Error in start command for user {interaction.user.id}: {e}")
            await interaction.followup.send(
                "❌ Something went wrong starting our conversation. Try again in a moment!",
                ephemeral=True,
            )

    @app_commands.command(
        name="register", description="Register your account with the task reminder bot"
    )
    @app_commands.describe(
        timezone="Your timezone (e.g., America/Toronto, Europe/London)"
    )
    async def register(
        self, interaction: discord.Interaction, timezone: Optional[str] = None
    ):
        """Register a new user account."""
        await interaction.response.defer()

        try:
            # Validate timezone
            if timezone:
                try:
                    pytz.timezone(timezone)
                except pytz.exceptions.UnknownTimeZoneError:
                    await interaction.followup.send(
                        f"❌ Invalid timezone: `{timezone}`\n"
                        f"Use a valid timezone like `America/Toronto` or `Europe/London`\n"
                        f"See: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones",
                        ephemeral=True,
                    )
                    return
            else:
                timezone = self.bot.config.default_timezone

            # Check if user already exists
            db_manager = get_db_manager()
            async with db_manager.get_session() as session:
                stmt = select(User).where(User.id == interaction.user.id)
                result = await session.execute(stmt)
                existing_user = result.scalar_one_or_none()

                if existing_user:
                    await interaction.followup.send(
                        f"✅ You're already registered!\n"
                        f"**Username:** {existing_user.username}\n"
                        f"**Timezone:** {existing_user.timezone}\n"
                        f"**Registered:** {existing_user.created_at.strftime('%Y-%m-%d')}\n\n"
                        f"Use `/profile` to view your full profile or `/timezone` to update your timezone.",
                        ephemeral=True,
                    )
                    return

                # Create new user
                new_user = User(
                    id=interaction.user.id,
                    username=interaction.user.display_name,
                    timezone=timezone,
                    created_at=datetime.utcnow(),
                    last_active=datetime.utcnow(),
                )

                session.add(new_user)
                await session.commit()

                # Create welcome embed
                embed = discord.Embed(
                    title="🎉 Welcome to Task Reminder Bot!",
                    description=f"Successfully registered {interaction.user.mention}",
                    color=0x00FF00,
                    timestamp=datetime.utcnow(),
                )

                embed.add_field(name="📍 Timezone", value=timezone, inline=True)

                embed.add_field(
                    name="🚀 Next Steps",
                    value=(
                        "• Use `/create_task` to add your first task\n"
                        "• Use `/help` to see all available commands\n"
                        "• Use `/profile` to view your profile"
                    ),
                    inline=False,
                )

                embed.set_footer(text="Ready to start building those streaks! 💪")

                await interaction.followup.send(embed=embed)
                logger.info(
                    f"Registered new user: {interaction.user.id} ({interaction.user.display_name})"
                )

        except Exception as e:
            logger.error(f"Failed to register user {interaction.user.id}: {e}")
            await interaction.followup.send(
                "❌ Failed to register your account. Please try again later.",
                ephemeral=True,
            )

    @app_commands.command(
        name="profile", description="View your profile and statistics"
    )
    async def profile(self, interaction: discord.Interaction):
        """Display user profile and statistics."""
        await interaction.response.defer()

        try:
            db_manager = get_db_manager()
            async with db_manager.get_session() as session:
                stmt = select(User).where(User.id == interaction.user.id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    await interaction.followup.send(
                        "❌ You're not registered yet! Use `/register` to get started.",
                        ephemeral=True,
                    )
                    return

                # Update last active
                user.last_active = datetime.utcnow()
                await session.commit()

                # Get statistics from streak manager
                streak_manager = self.bot.get_streak_manager()
                stats = await streak_manager.get_user_statistics(user.id)

                # Create profile embed
                embed = discord.Embed(
                    title=f"📊 Profile: {user.username}",
                    color=0x3498DB,
                    timestamp=datetime.utcnow(),
                )

                embed.set_thumbnail(url=interaction.user.display_avatar.url)

                # Basic info
                embed.add_field(
                    name="👤 Account Info",
                    value=(
                        f"**Timezone:** {user.timezone}\n"
                        f"**Registered:** {user.created_at.strftime('%Y-%m-%d')}\n"
                        f"**Last Active:** {user.last_active.strftime('%Y-%m-%d %H:%M')}"
                    ),
                    inline=True,
                )

                # Task statistics
                embed.add_field(
                    name="📋 Task Stats",
                    value=(
                        f"**Total Tasks:** {stats['total_tasks']}\n"
                        f"**Active Streaks:** {stats['active_streaks']}\n"
                        f"**Longest Streak:** {stats['longest_streak']} days"
                    ),
                    inline=True,
                )

                # Recent activity
                embed.add_field(
                    name="📈 Recent Activity",
                    value=(
                        f"**Completions (7d):** {stats['recent_completions_7d']}\n"
                        f"**Completions (30d):** {stats['total_completions_30d']}\n"
                        f"**Completion Rate:** {stats['completion_rate_30d']}%"
                    ),
                    inline=True,
                )

                # Top streaks
                if stats["streaks"]:
                    streak_text = ""
                    for i, streak in enumerate(stats["streaks"][:3], 1):
                        status = "🔥" if streak["is_active"] else "💔"
                        streak_text += f"{i}. {status} **{streak['task_name']}** - {streak['current_streak']} days\n"

                    embed.add_field(
                        name="🏆 Top Streaks", value=streak_text, inline=False
                    )

                # API usage
                ai_handler = self.bot.get_ai_handler()
                usage_stats = await ai_handler.get_usage_stats(user.id)

                embed.add_field(
                    name="🤖 AI Usage Today",
                    value=f"{usage_stats['daily_usage']}/{usage_stats['daily_limit']} calls",
                    inline=True,
                )

                embed.set_footer(text="Use /help to see available commands")

                await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to get profile for user {interaction.user.id}: {e}")
            await interaction.followup.send(
                "❌ Failed to load your profile. Please try again later.",
                ephemeral=True,
            )

    @app_commands.command(name="timezone", description="Update your timezone")
    @app_commands.describe(
        timezone="Your new timezone (e.g., America/Toronto, Europe/London)"
    )
    async def timezone(self, interaction: discord.Interaction, timezone: str):
        """Update user timezone."""
        await interaction.response.defer()

        try:
            # Validate timezone
            try:
                pytz.timezone(timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                await interaction.followup.send(
                    f"❌ Invalid timezone: `{timezone}`\n"
                    f"Use a valid timezone like `America/Toronto` or `Europe/London`\n"
                    f"See: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones",
                    ephemeral=True,
                )
                return

            db_manager = get_db_manager()
            async with db_manager.get_session() as session:
                stmt = select(User).where(User.id == interaction.user.id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    await interaction.followup.send(
                        "❌ You're not registered yet! Use `/register` to get started.",
                        ephemeral=True,
                    )
                    return

                old_timezone = user.timezone
                user.timezone = timezone
                user.last_active = datetime.utcnow()
                await session.commit()

                # Update task schedules
                scheduler = self.bot.get_scheduler()
                await scheduler.reload_all_tasks()

                embed = discord.Embed(
                    title="🌍 Timezone Updated",
                    description=f"Successfully updated your timezone",
                    color=0x00FF00,
                )

                embed.add_field(name="Previous", value=old_timezone, inline=True)

                embed.add_field(name="New", value=timezone, inline=True)

                embed.add_field(
                    name="📅 Effect",
                    value="All your task reminders have been rescheduled to the new timezone.",
                    inline=False,
                )

                await interaction.followup.send(embed=embed)
                logger.info(
                    f"Updated timezone for user {interaction.user.id}: {old_timezone} -> {timezone}"
                )

        except Exception as e:
            logger.error(
                f"Failed to update timezone for user {interaction.user.id}: {e}"
            )
            await interaction.followup.send(
                "❌ Failed to update your timezone. Please try again later.",
                ephemeral=True,
            )

    @app_commands.command(
        name="help", description="Show available commands and how to use the bot"
    )
    async def help_command(self, interaction: discord.Interaction):
        """Display help information."""
        embed = discord.Embed(
            title="🤖 Task Reminder Bot - Help",
            description="I help you stay on track with daily tasks and build streaks! Here's what I can do:",
            color=0x3498DB,
        )

        # User commands
        embed.add_field(
            name="👤 User Commands",
            value=(
                "`/register [timezone]` - Register your account\n"
                "`/profile` - View your profile and stats\n"
                "`/timezone <timezone>` - Update your timezone"
            ),
            inline=False,
        )

        # Task commands
        embed.add_field(
            name="📋 Task Commands",
            value=(
                "`/create_task <name> <time> [description]` - Create a new task\n"
                "`/list_tasks` - View all your tasks\n"
                "`/edit_task <id> [name] [time] [description]` - Edit a task\n"
                "`/delete_task <id>` - Delete a task\n"
                "`/toggle_task <id>` - Enable/disable task reminders"
            ),
            inline=False,
        )

        # Completion commands
        embed.add_field(
            name="✅ Completion Commands",
            value=(
                "`/complete <task_id> <image>` - Complete task with image proof\n"
                "`/streaks` - View your current streaks\n"
                "`/stats [task_id]` - View detailed statistics"
            ),
            inline=False,
        )

        # How it works
        embed.add_field(
            name="🔥 How Streaks Work",
            value=(
                "• Complete tasks daily to build streaks\n"
                "• Upload image proof for verification\n"
                "• AI analyzes images to confirm completion\n"
                "• 2-day grace period if you miss a day\n"
                "• Track your progress and beat your records!"
            ),
            inline=False,
        )

        embed.add_field(
            name="⏰ Time Format",
            value="Use 24-hour format: `07:30`, `14:00`, `23:45`",
            inline=True,
        )

        embed.add_field(
            name="🌍 Timezones",
            value="Examples: `America/Toronto`, `Europe/London`, `Asia/Tokyo`",
            inline=True,
        )

        embed.set_footer(
            text="Need more help? Check the documentation or ask in the support server!"
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    """Set up the user commands cog."""
    await bot.add_cog(UserCommands(bot))
