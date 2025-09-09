"""
Task management commands for the Discord Task Reminder Bot.
"""

import logging
from datetime import datetime, time
from typing import Optional
import pytz
import discord
from discord.ext import commands
from discord import app_commands
from sqlalchemy import select, and_

from database.connection import get_db_manager
from database.models import User, Task, Streak

logger = logging.getLogger(__name__)


class TaskCommands(commands.Cog):
    """Commands for task creation and management."""

    def __init__(self, bot):
        """Initialize the task commands cog."""
        self.bot = bot

    @app_commands.command(name="create_task", description="Create a new daily task")
    @app_commands.describe(
        name="Name of the task (e.g., 'Morning Exercise')",
        reminder_time="Time for daily reminder in 24-hour format (e.g., '07:30')",
        description="Optional description of the task",
    )
    async def create_task(
        self,
        interaction: discord.Interaction,
        name: str,
        reminder_time: str,
        description: Optional[str] = None,
    ):
        """Create a new daily task with reminders."""
        await interaction.response.defer()

        try:
            # Validate time format
            try:
                parsed_time = datetime.strptime(reminder_time, "%H:%M").time()
            except ValueError:
                await interaction.followup.send(
                    f"❌ Invalid time format: `{reminder_time}`\n"
                    f"Use 24-hour format like `07:30`, `14:00`, or `23:45`",
                    ephemeral=True,
                )
                return

            # Check if user is registered
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

                # Check for duplicate task names
                stmt = select(Task).where(
                    and_(
                        Task.user_id == interaction.user.id,
                        Task.name == name,
                        Task.is_active == True,
                    )
                )
                result = await session.execute(stmt)
                existing_task = result.scalar_one_or_none()

                if existing_task:
                    await interaction.followup.send(
                        f"❌ You already have an active task named `{name}`\n"
                        f"Use `/edit_task {existing_task.id}` to modify it or choose a different name.",
                        ephemeral=True,
                    )
                    return

                # Create new task
                new_task = Task(
                    user_id=interaction.user.id,
                    name=name,
                    description=description,
                    reminder_time=parsed_time,
                    timezone=user.timezone,
                    is_active=True,
                    created_at=datetime.utcnow(),
                )

                session.add(new_task)
                await session.commit()

                # Refresh to get the ID
                await session.refresh(new_task)

                # Create initial streak record
                initial_streak = Streak(
                    user_id=interaction.user.id,
                    task_id=new_task.id,
                    current_streak=0,
                    longest_streak=0,
                    last_completion_date=None,
                )

                session.add(initial_streak)
                await session.commit()

                # Schedule the task reminder
                scheduler = self.bot.get_scheduler()
                await scheduler.add_task_schedule(new_task)

                # Create success embed
                embed = discord.Embed(
                    title="✅ Task Created Successfully!",
                    description=f"**{name}** is now set up with daily reminders",
                    color=0x00FF00,
                    timestamp=datetime.utcnow(),
                )

                embed.add_field(
                    name="📋 Task Details",
                    value=(
                        f"**Name:** {name}\n"
                        f"**Description:** {description or 'None'}\n"
                        f"**Reminder Time:** {reminder_time} ({user.timezone})\n"
                        f"**Task ID:** {new_task.id}"
                    ),
                    inline=False,
                )

                embed.add_field(
                    name="🚀 Next Steps",
                    value=(
                        f"• I'll remind you daily at {reminder_time}\n"
                        f"• Use `/complete {new_task.id}` with an image to mark as done\n"
                        f"• Use `/streaks` to track your progress"
                    ),
                    inline=False,
                )

                embed.set_footer(text="Ready to start building that streak! 🔥")

                await interaction.followup.send(embed=embed)
                logger.info(
                    f"Created task {new_task.id} for user {interaction.user.id}: {name}"
                )

        except Exception as e:
            logger.error(f"Failed to create task for user {interaction.user.id}: {e}")
            await interaction.followup.send(
                "❌ Failed to create task. Please try again later.", ephemeral=True
            )

    @app_commands.command(name="list_tasks", description="View all your tasks")
    async def list_tasks(self, interaction: discord.Interaction):
        """List all user tasks."""
        await interaction.response.defer()

        try:
            db_manager = get_db_manager()
            async with db_manager.get_session() as session:
                # Get user tasks
                stmt = (
                    select(Task)
                    .where(Task.user_id == interaction.user.id)
                    .order_by(Task.is_active.desc(), Task.reminder_time)
                )
                result = await session.execute(stmt)
                tasks = result.scalars().all()

                if not tasks:
                    embed = discord.Embed(
                        title="📋 Your Tasks",
                        description="You don't have any tasks yet!\nUse `/create_task` to add your first task.",
                        color=0x95A5A6,
                    )
                    await interaction.followup.send(embed=embed)
                    return

                # Get streak information
                streak_manager = self.bot.get_streak_manager()
                user_streaks = await streak_manager.get_user_streaks(
                    interaction.user.id
                )
                streak_dict = {s["task_id"]: s for s in user_streaks}

                # Create tasks embed
                embed = discord.Embed(
                    title="📋 Your Tasks",
                    description=f"You have {len(tasks)} task(s) configured",
                    color=0x3498DB,
                    timestamp=datetime.utcnow(),
                )

                active_tasks = [t for t in tasks if t.is_active]
                inactive_tasks = [t for t in tasks if not t.is_active]

                # Active tasks
                if active_tasks:
                    active_text = ""
                    for task in active_tasks:
                        streak_info = streak_dict.get(task.id, {})
                        current_streak = streak_info.get("current_streak", 0)
                        is_active = streak_info.get("is_active", False)

                        status_emoji = (
                            "🔥" if is_active and current_streak > 0 else "⭐"
                        )
                        streak_text = (
                            f" ({current_streak} day streak)"
                            if current_streak > 0
                            else ""
                        )

                        active_text += (
                            f"{status_emoji} **{task.name}** (ID: {task.id})\n"
                            f"   ⏰ {task.reminder_time.strftime('%H:%M')} {task.timezone}{streak_text}\n"
                        )

                        if task.description:
                            active_text += f"   📝 {task.description}\n"
                        active_text += "\n"

                    embed.add_field(
                        name="✅ Active Tasks", value=active_text.strip(), inline=False
                    )

                # Inactive tasks
                if inactive_tasks:
                    inactive_text = ""
                    for task in inactive_tasks:
                        inactive_text += (
                            f"⏸️ **{task.name}** (ID: {task.id})\n"
                            f"   ⏰ {task.reminder_time.strftime('%H:%M')} {task.timezone}\n"
                        )
                        if task.description:
                            inactive_text += f"   📝 {task.description}\n"
                        inactive_text += "\n"

                    embed.add_field(
                        name="⏸️ Inactive Tasks",
                        value=inactive_text.strip(),
                        inline=False,
                    )

                embed.add_field(
                    name="🛠️ Task Management",
                    value=(
                        "`/edit_task <id>` - Edit a task\n"
                        "`/delete_task <id>` - Delete a task\n"
                        "`/toggle_task <id>` - Enable/disable reminders"
                    ),
                    inline=False,
                )

                embed.set_footer(text="Use task IDs for management commands")

                await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Failed to list tasks for user {interaction.user.id}: {e}")
            await interaction.followup.send(
                "❌ Failed to load your tasks. Please try again later.", ephemeral=True
            )

    @app_commands.command(name="edit_task", description="Edit an existing task")
    @app_commands.describe(
        task_id="ID of the task to edit",
        name="New name for the task",
        reminder_time="New reminder time in 24-hour format (e.g., '07:30')",
        description="New description for the task",
    )
    async def edit_task(
        self,
        interaction: discord.Interaction,
        task_id: int,
        name: Optional[str] = None,
        reminder_time: Optional[str] = None,
        description: Optional[str] = None,
    ):
        """Edit an existing task."""
        await interaction.response.defer()

        try:
            # Validate time format if provided
            parsed_time = None
            if reminder_time:
                try:
                    parsed_time = datetime.strptime(reminder_time, "%H:%M").time()
                except ValueError:
                    await interaction.followup.send(
                        f"❌ Invalid time format: `{reminder_time}`\n"
                        f"Use 24-hour format like `07:30`, `14:00`, or `23:45`",
                        ephemeral=True,
                    )
                    return

            db_manager = get_db_manager()
            async with db_manager.get_session() as session:
                # Get the task
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

                # Store old values for comparison
                old_name = task.name
                old_time = task.reminder_time
                old_description = task.description

                # Update fields if provided
                if name:
                    task.name = name
                if parsed_time:
                    task.reminder_time = parsed_time
                if description is not None:  # Allow empty string to clear description
                    task.description = description if description else None

                await session.commit()

                # Update scheduler if time changed
                if parsed_time:
                    scheduler = self.bot.get_scheduler()
                    await scheduler.update_task_schedule(task)

                # Create update embed
                embed = discord.Embed(
                    title="✏️ Task Updated Successfully!",
                    description=f"Task ID {task_id} has been updated",
                    color=0x00FF00,
                    timestamp=datetime.utcnow(),
                )

                # Show changes
                changes = []
                if name and name != old_name:
                    changes.append(f"**Name:** {old_name} → {name}")
                if parsed_time and parsed_time != old_time:
                    changes.append(
                        f"**Time:** {old_time.strftime('%H:%M')} → {reminder_time}"
                    )
                if description is not None and description != old_description:
                    old_desc = old_description or "None"
                    new_desc = description or "None"
                    changes.append(f"**Description:** {old_desc} → {new_desc}")

                if changes:
                    embed.add_field(
                        name="📝 Changes Made", value="\n".join(changes), inline=False
                    )
                else:
                    embed.add_field(
                        name="ℹ️ No Changes",
                        value="No changes were made to the task.",
                        inline=False,
                    )

                # Current task info
                embed.add_field(
                    name="📋 Current Task Info",
                    value=(
                        f"**Name:** {task.name}\n"
                        f"**Time:** {task.reminder_time.strftime('%H:%M')} ({task.timezone})\n"
                        f"**Description:** {task.description or 'None'}\n"
                        f"**Status:** {'Active' if task.is_active else 'Inactive'}"
                    ),
                    inline=False,
                )

                await interaction.followup.send(embed=embed)
                logger.info(f"Updated task {task_id} for user {interaction.user.id}")

        except Exception as e:
            logger.error(
                f"Failed to edit task {task_id} for user {interaction.user.id}: {e}"
            )
            await interaction.followup.send(
                "❌ Failed to edit task. Please try again later.", ephemeral=True
            )

    @app_commands.command(name="delete_task", description="Delete a task permanently")
    @app_commands.describe(task_id="ID of the task to delete")
    async def delete_task(self, interaction: discord.Interaction, task_id: int):
        """Delete a task permanently."""
        await interaction.response.defer()

        try:
            db_manager = get_db_manager()
            async with db_manager.get_session() as session:
                # Get the task
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

                task_name = task.name

                # Remove from scheduler
                scheduler = self.bot.get_scheduler()
                await scheduler.remove_task_schedule(interaction.user.id, task_id)

                # Delete the task (cascades to streaks and completions)
                await session.delete(task)
                await session.commit()

                embed = discord.Embed(
                    title="🗑️ Task Deleted",
                    description=f"Successfully deleted task: **{task_name}**",
                    color=0xE74C3C,
                    timestamp=datetime.utcnow(),
                )

                embed.add_field(
                    name="⚠️ Note",
                    value="All associated streaks and completion history have been permanently removed.",
                    inline=False,
                )

                await interaction.followup.send(embed=embed)
                logger.info(
                    f"Deleted task {task_id} ({task_name}) for user {interaction.user.id}"
                )

        except Exception as e:
            logger.error(
                f"Failed to delete task {task_id} for user {interaction.user.id}: {e}"
            )
            await interaction.followup.send(
                "❌ Failed to delete task. Please try again later.", ephemeral=True
            )

    @app_commands.command(
        name="toggle_task", description="Enable or disable task reminders"
    )
    @app_commands.describe(task_id="ID of the task to toggle")
    async def toggle_task(self, interaction: discord.Interaction, task_id: int):
        """Toggle task active status."""
        await interaction.response.defer()

        try:
            db_manager = get_db_manager()
            async with db_manager.get_session() as session:
                # Get the task
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

                # Toggle active status
                task.is_active = not task.is_active
                await session.commit()

                # Update scheduler
                scheduler = self.bot.get_scheduler()
                await scheduler.update_task_schedule(task)

                status = "enabled" if task.is_active else "disabled"
                emoji = "✅" if task.is_active else "⏸️"
                color = 0x00FF00 if task.is_active else 0x95A5A6

                embed = discord.Embed(
                    title=f"{emoji} Task {status.title()}",
                    description=f"Task **{task.name}** has been {status}",
                    color=color,
                    timestamp=datetime.utcnow(),
                )

                if task.is_active:
                    embed.add_field(
                        name="📅 Next Reminder",
                        value=f"Daily at {task.reminder_time.strftime('%H:%M')} ({task.timezone})",
                        inline=False,
                    )
                else:
                    embed.add_field(
                        name="ℹ️ Note",
                        value="No reminders will be sent until you re-enable this task.",
                        inline=False,
                    )

                await interaction.followup.send(embed=embed)
                logger.info(
                    f"Toggled task {task_id} to {status} for user {interaction.user.id}"
                )

        except Exception as e:
            logger.error(
                f"Failed to toggle task {task_id} for user {interaction.user.id}: {e}"
            )
            await interaction.followup.send(
                "❌ Failed to toggle task. Please try again later.", ephemeral=True
            )


async def setup(bot):
    """Set up the task commands cog."""
    await bot.add_cog(TaskCommands(bot))
