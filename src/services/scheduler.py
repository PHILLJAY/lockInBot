"""
Task scheduling service for daily reminders.
"""

import logging
import asyncio
from datetime import datetime, time, timedelta
from typing import Optional, List, Dict, Any
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from sqlalchemy import select
from sqlalchemy.orm import selectinload

import discord

from database.connection import DatabaseManager
from database.models import User, Task, Streak
from services.ai_handler import AIHandler

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Manages daily task reminders using APScheduler."""

    def __init__(self, bot, db_manager: DatabaseManager, ai_handler: AIHandler):
        """Initialize the task scheduler."""
        self.bot = bot
        self.db_manager = db_manager
        self.ai_handler = ai_handler

        # Configure scheduler
        jobstores = {"default": MemoryJobStore()}

        self.scheduler = AsyncIOScheduler(jobstores=jobstores, timezone=pytz.UTC)

        self.is_running = False

    async def start(self) -> None:
        """Start the task scheduler."""
        try:
            self.scheduler.start()
            self.is_running = True
            logger.info("Task scheduler started")

            # Schedule initial job to load all user tasks
            await self.reload_all_tasks()

            # Schedule periodic reload (every hour)
            self.scheduler.add_job(
                self.reload_all_tasks,
                CronTrigger(minute=0),  # Every hour at minute 0
                id="reload_tasks",
                replace_existing=True,
            )

        except Exception as e:
            logger.error(f"Failed to start task scheduler: {e}")
            raise

    async def stop(self) -> None:
        """Stop the task scheduler."""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Task scheduler stopped")

    async def reload_all_tasks(self) -> None:
        """Reload all active tasks and schedule reminders."""
        try:
            async with self.db_manager.get_session() as session:
                # Get all active tasks
                stmt = (
                    select(Task)
                    .options(selectinload(Task.user))
                    .where(Task.is_active == True)
                )
                result = await session.execute(stmt)
                tasks = result.scalars().all()

                logger.info(f"Reloading {len(tasks)} active tasks")

                # Clear existing task jobs (but keep system jobs)
                for job in self.scheduler.get_jobs():
                    if job.id.startswith("task_"):
                        job.remove()

                # Schedule each task
                for task in tasks:
                    await self.schedule_task_reminder(task)

                logger.info(f"Scheduled reminders for {len(tasks)} tasks")

        except Exception as e:
            logger.error(f"Failed to reload tasks: {e}")

    async def schedule_task_reminder(self, task: Task) -> None:
        """Schedule a reminder for a specific task, handling recurring tasks."""
        try:
            # Parse user timezone
            user_tz = pytz.timezone(task.timezone)

            # Create cron trigger based on task recurrence pattern
            reminder_time = task.reminder_time

            if task.is_recurring:
                if task.recurrence_pattern == "weekly" and task.days_of_week:
                    # Weekly recurring task on specific days
                    day_numbers = [int(day) for day in task.days_of_week.split(",")]
                    # Convert from 0-6 (Mon-Sun) to 1-7 (Mon-Sun) for cron
                    cron_days = [
                        day + 1 if day < 6 else 0 for day in day_numbers
                    ]  # 0=Sunday in cron
                    trigger = CronTrigger(
                        day_of_week=",".join(str(day) for day in cron_days),
                        hour=reminder_time.hour,
                        minute=reminder_time.minute,
                        timezone=user_tz,
                    )
                elif task.recurrence_pattern == "daily":
                    # Daily recurring task
                    if task.recurrence_interval and task.recurrence_interval > 1:
                        # Interval-based daily task
                        trigger = CronTrigger(
                            hour=reminder_time.hour,
                            minute=reminder_time.minute,
                            timezone=user_tz,
                        )
                        # Note: APScheduler doesn't directly support interval days in CronTrigger
                        # This would need a different approach for true interval scheduling
                    else:
                        # Simple daily task
                        trigger = CronTrigger(
                            hour=reminder_time.hour,
                            minute=reminder_time.minute,
                            timezone=user_tz,
                        )
                else:
                    # Fallback to daily if pattern is not recognized
                    trigger = CronTrigger(
                        hour=reminder_time.hour,
                        minute=reminder_time.minute,
                        timezone=user_tz,
                    )
            else:
                # Non-recurring task - schedule for today
                trigger = CronTrigger(
                    hour=reminder_time.hour,
                    minute=reminder_time.minute,
                    timezone=user_tz,
                )

            # Schedule the job
            job_id = f"task_{task.user_id}_{task.id}"
            self.scheduler.add_job(
                self.send_task_reminder,
                trigger,
                args=[task.user_id, task.id],
                id=job_id,
                replace_existing=True,
                max_instances=1,
            )

            logger.debug(
                f"Scheduled reminder for task {task.id} at {reminder_time} ({task.timezone})"
            )

        except Exception as e:
            logger.error(f"Failed to schedule task {task.id}: {e}")

    async def unschedule_task_reminder(self, user_id: int, task_id: int) -> None:
        """Remove a scheduled task reminder."""
        job_id = f"task_{user_id}_{task_id}"
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.remove()
                logger.debug(f"Removed scheduled reminder for task {task_id}")
        except Exception as e:
            logger.error(f"Failed to unschedule task {task_id}: {e}")

    async def send_task_reminder(self, user_id: int, task_id: int) -> None:
        """Send a task reminder to a user."""
        try:
            # Get task and user information
            async with self.db_manager.get_session() as session:
                stmt = (
                    select(Task)
                    .options(selectinload(Task.user), selectinload(Task.streaks))
                    .where(Task.id == task_id)
                    .where(Task.is_active == True)
                )
                result = await session.execute(stmt)
                task = result.scalar_one_or_none()

                if not task:
                    logger.warning(f"Task {task_id} not found or inactive")
                    return

                # Get current streak information
                streak_info = None
                if task.streaks:
                    streak = task.streaks[0]  # Should only be one streak per task
                    streak_info = {
                        "current_streak": streak.current_streak,
                        "longest_streak": streak.longest_streak,
                        "last_completion": streak.last_completion_date,
                    }

            # Get Discord user
            discord_user = self.bot.get_user(user_id)
            if not discord_user:
                try:
                    discord_user = await self.bot.fetch_user(user_id)
                except discord.NotFound:
                    logger.warning(f"Discord user {user_id} not found")
                    return

            # Generate AI reminder message
            context = {
                "task_name": task.name,
                "task_description": task.description,
                "current_streak": streak_info["current_streak"] if streak_info else 0,
                "longest_streak": streak_info["longest_streak"] if streak_info else 0,
                "last_completion": streak_info["last_completion"]
                if streak_info
                else None,
            }

            ai_message = await self.ai_handler.generate_response(
                f"Daily reminder for task: {task.name}", context, user_id
            )

            # Create reminder embed
            embed = discord.Embed(
                title=f"📋 Daily Reminder: {task.name}",
                description=task.description or "Time to complete your task!",
                color=0x3498DB,
                timestamp=datetime.utcnow(),
            )

            # Add streak information
            if streak_info:
                streak_text = f"Current: {streak_info['current_streak']} days"
                if streak_info["longest_streak"] > 0:
                    streak_text += f" | Best: {streak_info['longest_streak']} days"
                embed.add_field(name="🔥 Streak", value=streak_text, inline=True)

            # Add AI message
            embed.add_field(name="💬 Motivation", value=ai_message, inline=False)

            # Add instructions
            embed.add_field(
                name="✅ Complete Task",
                value=f"Use `/complete {task.id}` with an image to mark as done!",
                inline=False,
            )

            embed.set_footer(text="Task Reminder Bot")

            # Send reminder
            try:
                await discord_user.send(embed=embed)
                logger.info(f"Sent reminder for task {task_id} to user {user_id}")
            except discord.Forbidden:
                logger.warning(f"Cannot send DM to user {user_id} - permissions denied")
                # Try to find a mutual guild and send in a channel
                await self._send_guild_reminder(user_id, embed)

        except Exception as e:
            logger.error(
                f"Failed to send reminder for task {task_id} to user {user_id}: {e}"
            )

    async def _send_guild_reminder(self, user_id: int, embed: discord.Embed) -> None:
        """Send reminder in a guild channel if DM fails."""
        try:
            # Find a mutual guild
            for guild in self.bot.guilds:
                member = guild.get_member(user_id)
                if member:
                    # Look for a task-reminders channel or general channel
                    channel = None
                    for ch in guild.text_channels:
                        if "task" in ch.name.lower() or "reminder" in ch.name.lower():
                            channel = ch
                            break

                    if not channel:
                        # Use first available text channel
                        channel = next(
                            (
                                ch
                                for ch in guild.text_channels
                                if ch.permissions_for(guild.me).send_messages
                            ),
                            None,
                        )

                    if channel:
                        # Modify embed to mention user
                        embed.description = f"{member.mention} {embed.description}"
                        await channel.send(embed=embed)
                        logger.info(
                            f"Sent guild reminder for user {user_id} in {guild.name}"
                        )
                        return

            logger.warning(
                f"Could not send reminder to user {user_id} - no mutual guilds or channels"
            )

        except Exception as e:
            logger.error(f"Failed to send guild reminder for user {user_id}: {e}")

    async def add_task_schedule(self, task: Task) -> None:
        """Add a new task to the schedule."""
        await self.schedule_task_reminder(task)

    async def remove_task_schedule(self, user_id: int, task_id: int) -> None:
        """Remove a task from the schedule."""
        await self.unschedule_task_reminder(user_id, task_id)

    async def update_task_schedule(self, task: Task) -> None:
        """Update an existing task schedule."""
        # Remove old schedule
        await self.unschedule_task_reminder(task.user_id, task.id)

        # Add new schedule if task is active
        if task.is_active:
            await self.schedule_task_reminder(task)

    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """Get information about all scheduled jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            if job.id.startswith("task_"):
                jobs.append(
                    {
                        "job_id": job.id,
                        "next_run": job.next_run_time,
                        "trigger": str(job.trigger),
                    }
                )
        return jobs

    async def get_user_next_reminders(self, user_id: int) -> List[Dict[str, Any]]:
        """Get next reminder times for a user's tasks."""
        reminders = []
        for job in self.scheduler.get_jobs():
            if job.id.startswith(f"task_{user_id}_"):
                task_id = int(job.id.split("_")[2])
                reminders.append(
                    {
                        "task_id": task_id,
                        "next_reminder": job.next_run_time,
                        "timezone": str(job.trigger.timezone)
                        if hasattr(job.trigger, "timezone")
                        else "UTC",
                    }
                )

        return sorted(
            reminders,
            key=lambda x: x["next_reminder"] or datetime.max.replace(tzinfo=pytz.UTC),
        )
