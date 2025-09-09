"""
Streak management service for tracking user task completion streaks.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from database.connection import DatabaseManager
from database.models import User, Task, Streak, Completion

logger = logging.getLogger(__name__)


class StreakManager:
    """Manages user task completion streaks and statistics."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize the streak manager."""
        self.db_manager = db_manager

    async def update_streak(
        self, user_id: int, task_id: int, completion_date: date
    ) -> Dict[str, Any]:
        """Update streak for a user's task completion."""
        async with self.db_manager.get_session() as session:
            try:
                # Get or create streak record
                stmt = select(Streak).where(
                    and_(Streak.user_id == user_id, Streak.task_id == task_id)
                )
                result = await session.execute(stmt)
                streak = result.scalar_one_or_none()

                if not streak:
                    # Create new streak record
                    streak = Streak(
                        user_id=user_id,
                        task_id=task_id,
                        current_streak=1,
                        longest_streak=1,
                        last_completion_date=completion_date,
                    )
                    session.add(streak)
                else:
                    # Update existing streak
                    streak = await self._calculate_streak_update(
                        streak, completion_date
                    )

                await session.commit()

                return {
                    "current_streak": streak.current_streak,
                    "longest_streak": streak.longest_streak,
                    "last_completion": streak.last_completion_date,
                    "is_new_record": streak.current_streak == streak.longest_streak
                    and streak.current_streak > 1,
                }

            except Exception as e:
                logger.error(
                    f"Failed to update streak for user {user_id}, task {task_id}: {e}"
                )
                await session.rollback()
                raise

    async def _calculate_streak_update(
        self, streak: Streak, completion_date: date
    ) -> Streak:
        """Calculate the updated streak values."""
        if not streak.last_completion_date:
            # First completion
            streak.current_streak = 1
            streak.longest_streak = max(streak.longest_streak, 1)
            streak.last_completion_date = completion_date
            return streak

        days_since_last = (completion_date - streak.last_completion_date).days

        if days_since_last == 0:
            # Same day completion - no change to streak
            return streak
        elif days_since_last == 1:
            # Consecutive day - increment streak
            streak.current_streak += 1
            streak.longest_streak = max(streak.longest_streak, streak.current_streak)
        elif days_since_last <= 2:
            # Grace period (up to 2 days) - maintain streak
            streak.current_streak += 1
            streak.longest_streak = max(streak.longest_streak, streak.current_streak)
        else:
            # Streak broken - reset to 1
            streak.current_streak = 1

        streak.last_completion_date = completion_date
        return streak

    async def get_user_streaks(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all streaks for a user."""
        async with self.db_manager.get_session() as session:
            try:
                stmt = (
                    select(Streak)
                    .options(selectinload(Streak.task))
                    .where(Streak.user_id == user_id)
                    .order_by(Streak.current_streak.desc())
                )
                result = await session.execute(stmt)
                streaks = result.scalars().all()

                streak_data = []
                for streak in streaks:
                    # Check if streak is still active (not broken)
                    is_active = self._is_streak_active(streak)

                    streak_data.append(
                        {
                            "task_id": streak.task_id,
                            "task_name": streak.task.name
                            if streak.task
                            else "Unknown Task",
                            "current_streak": streak.current_streak if is_active else 0,
                            "longest_streak": streak.longest_streak,
                            "last_completion": streak.last_completion_date,
                            "is_active": is_active,
                            "days_since_completion": (
                                date.today() - streak.last_completion_date
                            ).days
                            if streak.last_completion_date
                            else None,
                        }
                    )

                return streak_data

            except Exception as e:
                logger.error(f"Failed to get streaks for user {user_id}: {e}")
                return []

    async def get_task_streak(
        self, user_id: int, task_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get streak information for a specific task."""
        async with self.db_manager.get_session() as session:
            try:
                stmt = (
                    select(Streak)
                    .options(selectinload(Streak.task))
                    .where(and_(Streak.user_id == user_id, Streak.task_id == task_id))
                )
                result = await session.execute(stmt)
                streak = result.scalar_one_or_none()

                if not streak:
                    return None

                is_active = self._is_streak_active(streak)

                return {
                    "task_id": streak.task_id,
                    "task_name": streak.task.name if streak.task else "Unknown Task",
                    "current_streak": streak.current_streak if is_active else 0,
                    "longest_streak": streak.longest_streak,
                    "last_completion": streak.last_completion_date,
                    "is_active": is_active,
                    "days_since_completion": (
                        date.today() - streak.last_completion_date
                    ).days
                    if streak.last_completion_date
                    else None,
                }

            except Exception as e:
                logger.error(
                    f"Failed to get streak for user {user_id}, task {task_id}: {e}"
                )
                return None

    def _is_streak_active(self, streak: Streak) -> bool:
        """Check if a streak is still active (not broken)."""
        if not streak.last_completion_date:
            return False

        days_since_last = (date.today() - streak.last_completion_date).days

        # Streak is broken if more than 2 days have passed without completion
        return days_since_last <= 2

    async def get_completion_history(
        self, user_id: int, task_id: Optional[int] = None, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get completion history for a user's tasks."""
        async with self.db_manager.get_session() as session:
            try:
                # Build query
                stmt = (
                    select(Completion)
                    .options(selectinload(Completion.task))
                    .where(Completion.user_id == user_id)
                    .where(
                        Completion.completion_date
                        >= date.today() - timedelta(days=days)
                    )
                )

                if task_id:
                    stmt = stmt.where(Completion.task_id == task_id)

                stmt = stmt.order_by(Completion.completion_date.desc())

                result = await session.execute(stmt)
                completions = result.scalars().all()

                history = []
                for completion in completions:
                    history.append(
                        {
                            "completion_id": completion.id,
                            "task_id": completion.task_id,
                            "task_name": completion.task.name
                            if completion.task
                            else "Unknown Task",
                            "completion_date": completion.completion_date,
                            "verified": completion.verified,
                            "verification_result": completion.verification_result,
                            "image_url": completion.image_url,
                            "created_at": completion.created_at,
                        }
                    )

                return history

            except Exception as e:
                logger.error(
                    f"Failed to get completion history for user {user_id}: {e}"
                )
                return []

    async def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive statistics for a user."""
        async with self.db_manager.get_session() as session:
            try:
                # Get all user streaks
                streaks = await self.get_user_streaks(user_id)

                # Get completion history for last 30 days
                recent_completions = await self.get_completion_history(user_id, days=30)

                # Calculate statistics
                total_tasks = len(streaks)
                active_streaks = len([s for s in streaks if s["is_active"]])
                longest_overall = max([s["longest_streak"] for s in streaks], default=0)
                current_total = sum(
                    [s["current_streak"] for s in streaks if s["is_active"]]
                )

                # Completion rate (last 30 days)
                total_possible = total_tasks * 30  # Assuming daily tasks
                actual_completions = len(recent_completions)
                completion_rate = (
                    (actual_completions / total_possible * 100)
                    if total_possible > 0
                    else 0
                )

                # Recent activity
                recent_activity = len(
                    [
                        c
                        for c in recent_completions
                        if c["completion_date"] >= date.today() - timedelta(days=7)
                    ]
                )

                return {
                    "total_tasks": total_tasks,
                    "active_streaks": active_streaks,
                    "longest_streak": longest_overall,
                    "current_total_streak": current_total,
                    "completion_rate_30d": round(completion_rate, 1),
                    "recent_completions_7d": recent_activity,
                    "total_completions_30d": actual_completions,
                    "streaks": streaks[:5],  # Top 5 streaks
                    "recent_completions": recent_completions[
                        :10
                    ],  # Last 10 completions
                }

            except Exception as e:
                logger.error(f"Failed to get statistics for user {user_id}: {e}")
                return {
                    "total_tasks": 0,
                    "active_streaks": 0,
                    "longest_streak": 0,
                    "current_total_streak": 0,
                    "completion_rate_30d": 0,
                    "recent_completions_7d": 0,
                    "total_completions_30d": 0,
                    "streaks": [],
                    "recent_completions": [],
                }

    async def check_streak_maintenance(self, user_id: int) -> List[Dict[str, Any]]:
        """Check which streaks are at risk of being broken."""
        streaks = await self.get_user_streaks(user_id)
        at_risk = []

        for streak in streaks:
            if not streak["is_active"]:
                continue

            days_since = streak["days_since_completion"]
            if days_since is None:
                continue

            if days_since >= 1:  # Haven't completed today
                risk_level = "high" if days_since >= 2 else "medium"
                at_risk.append(
                    {
                        **streak,
                        "risk_level": risk_level,
                        "days_remaining": max(0, 2 - days_since),
                    }
                )

        return at_risk
