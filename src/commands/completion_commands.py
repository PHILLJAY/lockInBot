"""
Task completion commands for the Discord Task Reminder Bot.
"""

import logging
from datetime import datetime, date
from typing import Optional
import discord
from discord.ext import commands
from discord import app_commands
from sqlalchemy import select, and_

from database.connection import get_db_manager
from database.models import User, Task, Completion

logger = logging.getLogger(__name__)


class CompletionCommands(commands.Cog):
    """Commands for task completion and streak tracking."""

    def __init__(self, bot):
        """Initialize the completion commands cog."""
        self.bot = bot

    @app_commands.command(
        name="complete", description="Complete a task with image proof"
    )
    @app_commands.describe(
        task_id="ID of the task to complete", image="Image showing task completion"
    )
    async def complete_task(
        self, interaction: discord.Interaction, task_id: int, image: discord.Attachment
    ):
        """Complete a task with image verification."""
        await interaction.response.defer()

        try:
            # Validate image
            if not image.content_type or not image.content_type.startswith("image/"):
                await interaction.followup.send(
                    "❌ Please upload a valid image file (JPEG, PNG, WebP, etc.)",
                    ephemeral=True,
                )
                return

            # Check image size
            max_size = (
                self.bot.config.max_image_size_mb * 1024 * 1024
            )  # Convert to bytes
            if image.size > max_size:
                await interaction.followup.send(
                    f"❌ Image too large! Maximum size is {self.bot.config.max_image_size_mb}MB",
                    ephemeral=True,
                )
                return

            # Get task and verify ownership
            db_manager = get_db_manager()
            async with db_manager.get_session() as session:
                stmt = select(Task).where(
                    and_(
                        Task.id == task_id,
                        Task.user_id == interaction.user.id,
                        Task.is_active == True,
                    )
                )
                result = await session.execute(stmt)
                task = result.scalar_one_or_none()

                if not task:
                    await interaction.followup.send(
                        f"❌ Task with ID `{task_id}` not found, doesn't belong to you, or is inactive.",
                        ephemeral=True,
                    )
                    return

                # Check if already completed today
                today = date.today()
                stmt = select(Completion).where(
                    and_(
                        Completion.user_id == interaction.user.id,
                        Completion.task_id == task_id,
                        Completion.completion_date == today,
                    )
                )
                result = await session.execute(stmt)
                existing_completion = result.scalar_one_or_none()

                if existing_completion:
                    await interaction.followup.send(
                        f"✅ You've already completed **{task.name}** today!\n"
                        f"Current completion status: {'Verified' if existing_completion.verified else 'Pending verification'}",
                        ephemeral=True,
                    )
                    return

                # Send initial response
                embed = discord.Embed(
                    title="🔍 Analyzing Image...",
                    description=f"Verifying completion of **{task.name}**",
                    color=0xF39C12,
                )
                embed.add_field(
                    name="📸 Image Received",
                    value=f"Size: {image.size / 1024:.1f} KB\nType: {image.content_type}",
                    inline=True,
                )
                embed.set_footer(text="This may take a few seconds...")

                message = await interaction.followup.send(embed=embed)

                # Get AI verification
                ai_handler = self.bot.get_ai_handler()
                verification_result = await ai_handler.verify_task_completion(
                    image.url, task.name, task.description, interaction.user.id
                )

                # Create completion record
                completion = Completion(
                    user_id=interaction.user.id,
                    task_id=task_id,
                    completion_date=today,
                    image_url=image.url,
                    verification_result=verification_result["explanation"],
                    verified=verification_result["verified"],
                    ai_confidence=verification_result["confidence"],
                    created_at=datetime.utcnow(),
                )

                session.add(completion)
                await session.commit()

                # Update streak if verified
                streak_info = None
                if verification_result["verified"]:
                    streak_manager = self.bot.get_streak_manager()
                    streak_info = await streak_manager.update_streak(
                        interaction.user.id, task_id, today
                    )

                # Create result embed
                if verification_result["verified"]:
                    embed = discord.Embed(
                        title="✅ Task Completed!",
                        description=f"Successfully completed **{task.name}**",
                        color=0x00FF00,
                        timestamp=datetime.utcnow(),
                    )

                    if streak_info:
                        streak_text = f"🔥 **{streak_info['current_streak']} days**"
                        if streak_info["is_new_record"]:
                            streak_text += " 🎉 NEW RECORD!"

                        embed.add_field(
                            name="Current Streak", value=streak_text, inline=True
                        )

                        embed.add_field(
                            name="Best Streak",
                            value=f"🏆 {streak_info['longest_streak']} days",
                            inline=True,
                        )
                else:
                    embed = discord.Embed(
                        title="❌ Verification Failed",
                        description=f"Could not verify completion of **{task.name}**",
                        color=0xE74C3C,
                        timestamp=datetime.utcnow(),
                    )

                # Add AI response
                embed.add_field(
                    name="🤖 AI Analysis",
                    value=verification_result["response"],
                    inline=False,
                )

                # Add confidence score
                confidence_emoji = (
                    "🟢"
                    if verification_result["confidence"] >= 80
                    else "🟡"
                    if verification_result["confidence"] >= 60
                    else "🔴"
                )
                embed.add_field(
                    name="📊 Confidence",
                    value=f"{confidence_emoji} {verification_result['confidence']}%",
                    inline=True,
                )

                # Add explanation
                embed.add_field(
                    name="📝 Explanation",
                    value=verification_result["explanation"],
                    inline=False,
                )

                if not verification_result["verified"]:
                    embed.add_field(
                        name="💡 Try Again",
                        value="Upload a clearer image showing the completed task!",
                        inline=False,
                    )

                embed.set_image(url=image.url)
                embed.set_footer(text=f"Completion ID: {completion.id}")

                # Update the message
                await message.edit(embed=embed)

                logger.info(
                    f"Task completion attempt - User: {interaction.user.id}, Task: {task_id}, "
                    f"Verified: {verification_result['verified']}, Confidence: {verification_result['confidence']}%"
                )

        except Exception as e:
            logger.error(
                f"Failed to complete task {task_id} for user {interaction.user.id}: {e}"
            )
            await interaction.followup.send(
                "❌ Failed to process task completion. Please try again later.",
                ephemeral=True,
            )

    @app_commands.command(name="streaks", description="View your current streaks")
    async def view_streaks(self, interaction: discord.Interaction):
        """View current streaks for all tasks."""
        await interaction.response.defer()

        try:
            streak_manager = self.bot.get_streak_manager()
            streaks = await streak_manager.get_user_streaks(interaction.user.id)

            if not streaks:
                embed = discord.Embed(
                    title="🔥 Your Streaks",
                    description="You don't have any tasks yet!\nUse `/create_task` to get started.",
                    color=0x95A5A6,
                )
                await interaction.followup.send(embed=embed)
                return

            embed = discord.Embed(
                title="🔥 Your Streaks",
                description=f"Tracking {len(streaks)} task(s)",
                color=0xE67E22,
                timestamp=datetime.utcnow(),
            )

            active_streaks = [
                s for s in streaks if s["is_active"] and s["current_streak"] > 0
            ]
            broken_streaks = [
                s for s in streaks if not s["is_active"] or s["current_streak"] == 0
            ]

            # Active streaks
            if active_streaks:
                streak_text = ""
                for streak in active_streaks:
                    days_text = "day" if streak["current_streak"] == 1 else "days"
                    streak_text += f"🔥 **{streak['task_name']}** - {streak['current_streak']} {days_text}\n"

                    if streak["longest_streak"] > streak["current_streak"]:
                        streak_text += f"   🏆 Best: {streak['longest_streak']} days\n"

                    if streak["days_since_completion"] is not None:
                        if streak["days_since_completion"] == 0:
                            streak_text += f"   ✅ Completed today\n"
                        elif streak["days_since_completion"] == 1:
                            streak_text += f"   ⚠️ Due today\n"
                        else:
                            streak_text += f"   🚨 {streak['days_since_completion']} days overdue\n"

                    streak_text += "\n"

                embed.add_field(
                    name="🔥 Active Streaks", value=streak_text.strip(), inline=False
                )

            # Broken or inactive streaks
            if broken_streaks:
                broken_text = ""
                for streak in broken_streaks[:5]:  # Limit to 5 to avoid embed limits
                    if streak["longest_streak"] > 0:
                        broken_text += f"💔 **{streak['task_name']}** - Best: {streak['longest_streak']} days\n"
                    else:
                        broken_text += (
                            f"⭐ **{streak['task_name']}** - No completions yet\n"
                        )

                embed.add_field(
                    name="💔 Inactive/Broken Streaks",
                    value=broken_text.strip(),
                    inline=False,
                )

            # Summary stats
            total_current = sum(s["current_streak"] for s in active_streaks)
            longest_overall = max((s["longest_streak"] for s in streaks), default=0)

            embed.add_field(
                name="📊 Summary",
                value=(
                    f"**Total Active Days:** {total_current}\n"
                    f"**Longest Ever:** {longest_overall} days\n"
                    f"**Active Streaks:** {len(active_streaks)}/{len(streaks)}"
                ),
                inline=True,
            )

            embed.set_footer(
                text="Use /complete <task_id> with an image to maintain streaks!"
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to get streaks for user {interaction.user.id}: {e}")
            await interaction.followup.send(
                "❌ Failed to load your streaks. Please try again later.",
                ephemeral=True,
            )

    @app_commands.command(name="stats", description="View detailed statistics")
    @app_commands.describe(task_id="Optional: View stats for a specific task")
    async def view_stats(
        self, interaction: discord.Interaction, task_id: Optional[int] = None
    ):
        """View detailed statistics."""
        await interaction.response.defer()

        try:
            streak_manager = self.bot.get_streak_manager()

            if task_id:
                # Get specific task stats
                db_manager = get_db_manager()
                async with db_manager.get_session() as session:
                    stmt = select(Task).where(
                        and_(Task.id == task_id, Task.user_id == interaction.user.id)
                    )
                    result = await session.execute(stmt)
                    task = result.scalar_one_or_none()

                    if not task:
                        await interaction.followup.send(
                            f"❌ Task with ID `{task_id}` not found or doesn't belong to you.",
                            ephemeral=True,
                        )
                        return

                # Get task-specific stats
                streak_info = await streak_manager.get_task_streak(
                    interaction.user.id, task_id
                )
                completion_history = await streak_manager.get_completion_history(
                    interaction.user.id, task_id, days=30
                )

                embed = discord.Embed(
                    title=f"📊 Stats: {task.name}",
                    description=f"Statistics for task ID {task_id}",
                    color=0x3498DB,
                    timestamp=datetime.utcnow(),
                )

                if streak_info:
                    embed.add_field(
                        name="🔥 Streak Info",
                        value=(
                            f"**Current:** {streak_info['current_streak']} days\n"
                            f"**Longest:** {streak_info['longest_streak']} days\n"
                            f"**Status:** {'Active' if streak_info['is_active'] else 'Broken'}"
                        ),
                        inline=True,
                    )

                embed.add_field(
                    name="📅 Task Details",
                    value=(
                        f"**Reminder:** {task.reminder_time.strftime('%H:%M')} ({task.timezone})\n"
                        f"**Status:** {'Active' if task.is_active else 'Inactive'}\n"
                        f"**Created:** {task.created_at.strftime('%Y-%m-%d')}"
                    ),
                    inline=True,
                )

                # Recent completions
                if completion_history:
                    verified_count = len(
                        [c for c in completion_history if c["verified"]]
                    )
                    completion_rate = (verified_count / len(completion_history)) * 100

                    embed.add_field(
                        name="📈 Last 30 Days",
                        value=(
                            f"**Attempts:** {len(completion_history)}\n"
                            f"**Verified:** {verified_count}\n"
                            f"**Success Rate:** {completion_rate:.1f}%"
                        ),
                        inline=True,
                    )

                    # Recent activity
                    recent_text = ""
                    for completion in completion_history[:5]:
                        status = "✅" if completion["verified"] else "❌"
                        recent_text += f"{status} {completion['completion_date']}\n"

                    embed.add_field(
                        name="📝 Recent Activity",
                        value=recent_text.strip() or "No recent activity",
                        inline=False,
                    )

            else:
                # Get overall user stats
                stats = await streak_manager.get_user_statistics(interaction.user.id)

                embed = discord.Embed(
                    title="📊 Your Statistics",
                    description="Overall performance across all tasks",
                    color=0x3498DB,
                    timestamp=datetime.utcnow(),
                )

                embed.add_field(
                    name="📋 Task Overview",
                    value=(
                        f"**Total Tasks:** {stats['total_tasks']}\n"
                        f"**Active Streaks:** {stats['active_streaks']}\n"
                        f"**Longest Streak:** {stats['longest_streak']} days"
                    ),
                    inline=True,
                )

                embed.add_field(
                    name="📈 Performance (30d)",
                    value=(
                        f"**Completions:** {stats['total_completions_30d']}\n"
                        f"**Success Rate:** {stats['completion_rate_30d']}%\n"
                        f"**Recent (7d):** {stats['recent_completions_7d']}"
                    ),
                    inline=True,
                )

                embed.add_field(
                    name="🔥 Current Total",
                    value=f"{stats['current_total_streak']} active streak days",
                    inline=True,
                )

                # Top performing tasks
                if stats["streaks"]:
                    top_text = ""
                    for i, streak in enumerate(stats["streaks"][:3], 1):
                        status = "🔥" if streak["is_active"] else "💔"
                        top_text += f"{i}. {status} **{streak['task_name']}** - {streak['current_streak']} days\n"

                    embed.add_field(
                        name="🏆 Top Streaks", value=top_text.strip(), inline=False
                    )

            embed.set_footer(text="Keep up the great work! 💪")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to get stats for user {interaction.user.id}: {e}")
            await interaction.followup.send(
                "❌ Failed to load statistics. Please try again later.", ephemeral=True
            )


async def setup(bot):
    """Set up the completion commands cog."""
    await bot.add_cog(CompletionCommands(bot))
