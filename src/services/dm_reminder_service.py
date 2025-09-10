"""
DM Reminder Service for Bakushin AI - sends personalized reminders via direct messages.
"""

import logging
from datetime import datetime, date
from typing import Optional, Dict, Any
import discord

from database.connection import get_db_manager
from database.models import User, Task, Streak
from services.bakushin_personality import BakushinPersonality, ConversationTone
from sqlalchemy import select

logger = logging.getLogger(__name__)


class DMReminderService:
    """Handles sending reminders via DMs with Bakushin's personality"""

    def __init__(self, bot, db_manager, ai_handler):
        self.bot = bot
        self.db_manager = db_manager
        self.ai_handler = ai_handler
        self.personality = BakushinPersonality()

    async def send_task_reminder(self, user_id: int, task: Task):
        """Send personalized reminder via DM"""
        try:
            user = await self.bot.fetch_user(user_id)

            # Get user's streak info for context
            streak_info = await self.get_user_streak_context(user_id, task.id)

            # Get user info for personalization
            user_info = await self.get_user_info(user_id)
            user_name = (
                user_info.get("username", user.display_name)
                if user_info
                else user.display_name
            )

            # Generate personalized reminder message
            reminder_message = self.personality.add_personality_to_reminder(
                task.name, streak_info.get("current_streak", 0), user_name
            )

            # Create reminder embed
            embed = discord.Embed(
                title=f"⏰ Time for: {task.name}",
                description=reminder_message,
                color=0x3498DB,
                timestamp=datetime.utcnow(),
            )

            if task.description:
                embed.add_field(name="📝 Details", value=task.description, inline=False)

            # Add streak info if exists
            if streak_info.get("current_streak", 0) > 0:
                embed.add_field(
                    name="🔥 Current Streak",
                    value=f"{streak_info['current_streak']} days",
                    inline=True,
                )

            if streak_info.get("longest_streak", 0) > 0:
                embed.add_field(
                    name="🏆 Best Streak",
                    value=f"{streak_info['longest_streak']} days",
                    inline=True,
                )

            # Add quick actions
            embed.add_field(
                name="🎯 Quick Actions",
                value="Reply with a photo when you complete this task!\nOr just tell me you're done.",
                inline=False,
            )

            # Add motivational footer
            if streak_info.get("current_streak", 0) >= 7:
                embed.set_footer(text="You're on fire! Keep that streak alive! 🔥")
            elif streak_info.get("current_streak", 0) > 0:
                embed.set_footer(text="Building momentum! Every day counts! 💪")
            else:
                embed.set_footer(text="Time to start building that streak! 🚀")

            await user.send(embed=embed)
            logger.info(f"Sent DM reminder to user {user_id} for task {task.id}")

        except discord.Forbidden:
            # User has DMs disabled - log and handle gracefully
            await self.handle_dm_disabled(user_id, task)
        except discord.NotFound:
            # User not found - they may have left all mutual servers
            logger.warning(
                f"User {user_id} not found when sending reminder for task {task.id}"
            )
        except Exception as e:
            logger.error(f"Failed to send DM reminder to {user_id}: {e}")

    async def send_missed_task_reminder(
        self, user_id: int, task: Task, days_missed: int
    ):
        """Send reminder for missed tasks"""
        try:
            user = await self.bot.fetch_user(user_id)
            user_info = await self.get_user_info(user_id)
            user_name = (
                user_info.get("username", user.display_name)
                if user_info
                else user.display_name
            )

            # Generate missed task message
            missed_message = self.personality.add_personality_to_missed_reminder(
                task.name, days_missed, user_name
            )

            embed = discord.Embed(
                title=f"😬 Missed: {task.name}",
                description=missed_message,
                color=0xE74C3C,
                timestamp=datetime.utcnow(),
            )

            embed.add_field(
                name="🔄 Get Back On Track",
                value="It's not about being perfect, it's about being consistent.\nReady to run it back?",
                inline=False,
            )

            embed.set_footer(
                text="Everyone falls off sometimes. Champions get back up! 💪"
            )

            await user.send(embed=embed)
            logger.info(
                f"Sent missed task reminder to user {user_id} for task {task.id}"
            )

        except discord.Forbidden:
            await self.handle_dm_disabled(user_id, task)
        except Exception as e:
            logger.error(f"Failed to send missed task reminder to {user_id}: {e}")

    async def send_streak_celebration(
        self, user_id: int, task: Task, streak_count: int
    ):
        """Send celebration message for streak milestones"""
        try:
            user = await self.bot.fetch_user(user_id)
            user_info = await self.get_user_info(user_id)
            user_name = (
                user_info.get("username", user.display_name)
                if user_info
                else user.display_name
            )

            # Generate celebration message
            celebration_context = {
                "streak_count": streak_count,
                "task_name": task.name,
                "user_name": user_name,
            }

            celebration_message = self.personality.generate_response(
                context=celebration_context,
                tone=ConversationTone.CELEBRATION,
            )

            # Determine celebration level
            if streak_count >= 30:
                color = 0xFFD700  # Gold
                emoji = "👑"
                title = f"{emoji} LEGENDARY STREAK!"
            elif streak_count >= 14:
                color = 0xFF6B35  # Orange
                emoji = "🔥"
                title = f"{emoji} ON FIRE!"
            elif streak_count >= 7:
                color = 0x00FF00  # Green
                emoji = "💪"
                title = f"{emoji} WEEK STRONG!"
            else:
                color = 0x3498DB  # Blue
                emoji = "⭐"
                title = f"{emoji} Building Momentum!"

            embed = discord.Embed(
                title=title,
                description=celebration_message,
                color=color,
                timestamp=datetime.utcnow(),
            )

            embed.add_field(
                name=f"🎯 {task.name}",
                value=f"**{streak_count} days** and counting!",
                inline=False,
            )

            # Add milestone rewards/recognition
            if streak_count in [7, 14, 30, 60, 100]:
                embed.add_field(
                    name="🏆 Milestone Achieved!",
                    value=f"You've hit the {streak_count}-day mark! That's some serious dedication.",
                    inline=False,
                )

            embed.set_footer(text="Keep going! You're building something special! 🚀")

            await user.send(embed=embed)
            logger.info(
                f"Sent streak celebration to user {user_id} for {streak_count} days"
            )

        except discord.Forbidden:
            await self.handle_dm_disabled(user_id, task)
        except Exception as e:
            logger.error(f"Failed to send streak celebration to {user_id}: {e}")

    async def send_completion_response(
        self, user_id: int, task: Task, verification_result: Dict[str, Any]
    ):
        """Send response to task completion with image verification"""
        try:
            user = await self.bot.fetch_user(user_id)

            # Generate completion response
            response_message = self.personality.generate_task_completion_response(
                task.name, verification_result
            )

            if verification_result.get("verified", False):
                color = 0x00FF00  # Green for verified
                title = "✅ Task Completed!"
            else:
                color = 0xE74C3C  # Red for not verified
                title = "❌ Not Quite Right"

            embed = discord.Embed(
                title=title,
                description=response_message,
                color=color,
                timestamp=datetime.utcnow(),
            )

            # Add AI analysis if available
            if verification_result.get("explanation"):
                embed.add_field(
                    name="🤖 AI Analysis",
                    value=verification_result["explanation"],
                    inline=False,
                )

            # Add confidence score if high enough
            confidence = verification_result.get("confidence", 0)
            if confidence > 70:
                embed.add_field(
                    name="📊 Confidence", value=f"{confidence}%", inline=True
                )

            await user.send(embed=embed)
            logger.info(
                f"Sent completion response to user {user_id} for task {task.id}"
            )

        except discord.Forbidden:
            await self.handle_dm_disabled(user_id, task)
        except Exception as e:
            logger.error(f"Failed to send completion response to {user_id}: {e}")

    async def send_weekly_summary(self, user_id: int, summary_data: Dict[str, Any]):
        """Send weekly progress summary"""
        try:
            user = await self.bot.fetch_user(user_id)
            user_info = await self.get_user_info(user_id)
            user_name = (
                user_info.get("username", user.display_name)
                if user_info
                else user.display_name
            )

            completed_tasks = summary_data.get("completed_tasks", 0)
            total_tasks = summary_data.get("total_tasks", 0)
            completion_rate = (
                (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            )

            # Generate summary message based on performance
            if completion_rate >= 90:
                summary_message = f"yooo {user_name} absolutely crushed this week! 🔥\n{completed_tasks}/{total_tasks} tasks completed - that's some different breed energy"
                color = 0x00FF00
                emoji = "👑"
            elif completion_rate >= 70:
                summary_message = f"solid week {user_name}! 💪\n{completed_tasks}/{total_tasks} tasks done - we're building something here"
                color = 0x3498DB
                emoji = "💪"
            elif completion_rate >= 50:
                summary_message = f"decent progress {user_name} 📈\n{completed_tasks}/{total_tasks} tasks completed - room for improvement but we're moving"
                color = 0xF39C12
                emoji = "📈"
            else:
                summary_message = f"tough week huh {user_name}? 😅\n{completed_tasks}/{total_tasks} tasks done - time to lock in next week"
                color = 0xE74C3C
                emoji = "🔄"

            embed = discord.Embed(
                title=f"{emoji} Weekly Summary",
                description=summary_message,
                color=color,
                timestamp=datetime.utcnow(),
            )

            # Add detailed breakdown
            if summary_data.get("task_breakdown"):
                breakdown_text = ""
                for task_name, completed in summary_data["task_breakdown"].items():
                    status_emoji = "✅" if completed else "❌"
                    breakdown_text += f"{status_emoji} {task_name}\n"

                embed.add_field(
                    name="📋 Task Breakdown", value=breakdown_text, inline=False
                )

            # Add streak info
            if summary_data.get("active_streaks"):
                streak_text = ""
                for task_name, streak_days in summary_data["active_streaks"].items():
                    streak_text += f"🔥 {task_name}: {streak_days} days\n"

                embed.add_field(
                    name="🔥 Active Streaks", value=streak_text, inline=True
                )

            embed.set_footer(text="New week, new opportunities to level up! 🚀")

            await user.send(embed=embed)
            logger.info(f"Sent weekly summary to user {user_id}")

        except discord.Forbidden:
            logger.warning(
                f"User {user_id} has DMs disabled, cannot send weekly summary"
            )
        except Exception as e:
            logger.error(f"Failed to send weekly summary to {user_id}: {e}")

    async def get_user_streak_context(
        self, user_id: int, task_id: int
    ) -> Dict[str, Any]:
        """Get user's streak information for context"""
        try:
            async with self.db_manager.get_session() as session:
                stmt = select(Streak).where(
                    Streak.user_id == user_id, Streak.task_id == task_id
                )
                result = await session.execute(stmt)
                streak = result.scalar_one_or_none()

                if streak:
                    return {
                        "current_streak": streak.current_streak,
                        "longest_streak": streak.longest_streak,
                        "last_completion_date": streak.last_completion_date,
                        "is_active": streak.last_completion_date == date.today()
                        if streak.last_completion_date
                        else False,
                    }
                else:
                    return {
                        "current_streak": 0,
                        "longest_streak": 0,
                        "last_completion_date": None,
                        "is_active": False,
                    }
        except Exception as e:
            logger.error(
                f"Error getting streak context for user {user_id}, task {task_id}: {e}"
            )
            return {
                "current_streak": 0,
                "longest_streak": 0,
                "last_completion_date": None,
                "is_active": False,
            }

    async def get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information from database"""
        try:
            async with self.db_manager.get_session() as session:
                stmt = select(User).where(User.id == user_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if user:
                    return {
                        "username": user.username,
                        "timezone": user.timezone,
                        "created_at": user.created_at,
                        "last_active": user.last_active,
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting user info for {user_id}: {e}")
            return None

    async def handle_dm_disabled(self, user_id: int, task: Task):
        """Handle when user has DMs disabled"""
        logger.warning(
            f"User {user_id} has DMs disabled, cannot send reminder for task {task.id}"
        )

        # Could implement fallback strategies here:
        # 1. Try to send message in a mutual server
        # 2. Disable reminders for this user
        # 3. Store failed attempts and retry later

        # For now, just log the issue
        # In a production system, you might want to:
        # - Update user preferences to indicate DM issues
        # - Send a notification to server admins
        # - Provide alternative reminder methods

    async def test_dm_access(self, user_id: int) -> bool:
        """Test if bot can send DMs to user"""
        try:
            user = await self.bot.fetch_user(user_id)
            # Try to send a test message
            await user.send("Testing DM access...")
            return True
        except discord.Forbidden:
            return False
        except Exception as e:
            logger.error(f"Error testing DM access for user {user_id}: {e}")
            return False
