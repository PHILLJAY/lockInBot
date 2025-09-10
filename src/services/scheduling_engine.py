"""
Advanced Scheduling Engine for Bakushin AI - converts natural language patterns to specific task schedules.
"""

import logging
from datetime import datetime, timedelta, time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from services.natural_language_parser import ScheduleType, SchedulePattern

logger = logging.getLogger(__name__)


@dataclass
class GeneratedTask:
    """Represents a generated task with specific scheduling"""

    name: str
    description: Optional[str]
    reminder_time: time
    days_of_week: List[int]  # 0=Monday, 6=Sunday
    is_recurring: bool = True
    interval_days: Optional[int] = None


class AdvancedSchedulingEngine:
    """Converts natural language patterns to specific task schedules"""

    def __init__(self):
        self.day_mapping = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }

        # Optimal day distributions for "X times per week"
        self.optimal_distributions = {
            1: [0],  # Monday
            2: [0, 3],  # Monday, Thursday
            3: [0, 2, 4],  # Monday, Wednesday, Friday
            4: [0, 1, 3, 4],  # Monday, Tuesday, Thursday, Friday
            5: [0, 1, 2, 3, 4],  # Weekdays
            6: [0, 1, 2, 3, 4, 5],  # All except Sunday
            7: [0, 1, 2, 3, 4, 5, 6],  # Every day
        }

        # Default times for different contexts
        self.default_times = {
            "morning": time(8, 0),
            "afternoon": time(14, 0),
            "evening": time(18, 0),
            "night": time(21, 0),
        }

    async def generate_schedule(
        self,
        pattern: SchedulePattern,
        task_name: str,
        description: Optional[str] = None,
    ) -> List[GeneratedTask]:
        """Generate specific task schedule from pattern"""

        try:
            if pattern.schedule_type == ScheduleType.DAILY:
                return self._generate_daily_schedule(pattern, task_name, description)

            elif pattern.schedule_type == ScheduleType.WEEKLY_COUNT:
                return self._generate_weekly_count_schedule(
                    pattern, task_name, description
                )

            elif pattern.schedule_type == ScheduleType.SPECIFIC_DAYS:
                return self._generate_specific_days_schedule(
                    pattern, task_name, description
                )

            elif pattern.schedule_type == ScheduleType.INTERVAL:
                return self._generate_interval_schedule(pattern, task_name, description)

            elif pattern.schedule_type == ScheduleType.BI_WEEKLY:
                return self._generate_bi_weekly_schedule(
                    pattern, task_name, description
                )

            else:
                raise ValueError(f"Unsupported schedule type: {pattern.schedule_type}")

        except Exception as e:
            logger.error(f"Error generating schedule: {e}")
            # Fallback to simple daily schedule
            return self._generate_fallback_schedule(
                task_name, description, pattern.time_preference
            )

    def _generate_daily_schedule(
        self, pattern: SchedulePattern, task_name: str, description: Optional[str]
    ) -> List[GeneratedTask]:
        """Generate daily task schedule"""
        reminder_time = pattern.time_preference or self.default_times["morning"]

        return [
            GeneratedTask(
                name=task_name,
                description=description,
                reminder_time=reminder_time,
                days_of_week=list(range(7)),  # Every day
                is_recurring=True,
            )
        ]

    def _generate_weekly_count_schedule(
        self, pattern: SchedulePattern, task_name: str, description: Optional[str]
    ) -> List[GeneratedTask]:
        """Generate schedule for 'X times per week' patterns"""
        frequency = pattern.frequency or 3
        reminder_time = pattern.time_preference or self.default_times["morning"]

        # Get optimal day distribution
        if frequency in self.optimal_distributions:
            optimal_days = self.optimal_distributions[frequency]
        else:
            # For frequencies > 7, distribute evenly
            optimal_days = self._distribute_days_evenly(frequency)

        tasks = []
        day_names = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        for i, day_index in enumerate(optimal_days):
            # Create descriptive task name
            if len(optimal_days) == 1:
                task_name_with_day = task_name
            else:
                day_name = day_names[day_index]
                task_name_with_day = f"{task_name} ({day_name})"

            tasks.append(
                GeneratedTask(
                    name=task_name_with_day,
                    description=description,
                    reminder_time=reminder_time,
                    days_of_week=[day_index],
                    is_recurring=True,
                )
            )

        return tasks

    def _generate_specific_days_schedule(
        self, pattern: SchedulePattern, task_name: str, description: Optional[str]
    ) -> List[GeneratedTask]:
        """Generate schedule for specific days (weekdays, weekends, etc.)"""
        if not pattern.specific_days:
            raise ValueError("Specific days pattern requires day list")

        reminder_time = pattern.time_preference or self.default_times["morning"]
        day_indices = [
            self.day_mapping[day.lower()]
            for day in pattern.specific_days
            if day.lower() in self.day_mapping
        ]

        if not day_indices:
            raise ValueError("No valid days found in specific days pattern")

        tasks = []
        day_names = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        if len(day_indices) == 1:
            # Single day - one task
            return [
                GeneratedTask(
                    name=task_name,
                    description=description,
                    reminder_time=reminder_time,
                    days_of_week=day_indices,
                    is_recurring=True,
                )
            ]
        elif len(day_indices) <= 3:
            # Few days - separate tasks for clarity
            for day_index in day_indices:
                day_name = day_names[day_index]
                tasks.append(
                    GeneratedTask(
                        name=f"{task_name} ({day_name})",
                        description=description,
                        reminder_time=reminder_time,
                        days_of_week=[day_index],
                        is_recurring=True,
                    )
                )
            return tasks
        else:
            # Many days - single task with multiple days
            return [
                GeneratedTask(
                    name=task_name,
                    description=description,
                    reminder_time=reminder_time,
                    days_of_week=day_indices,
                    is_recurring=True,
                )
            ]

    def _generate_interval_schedule(
        self, pattern: SchedulePattern, task_name: str, description: Optional[str]
    ) -> List[GeneratedTask]:
        """Generate schedule for interval patterns (every X days)"""
        reminder_time = pattern.time_preference or self.default_times["morning"]
        interval_days = pattern.interval_days or 2

        return [
            GeneratedTask(
                name=task_name,
                description=description,
                reminder_time=reminder_time,
                days_of_week=[],  # Empty for interval-based
                is_recurring=True,
                interval_days=interval_days,
            )
        ]

    def _generate_bi_weekly_schedule(
        self, pattern: SchedulePattern, task_name: str, description: Optional[str]
    ) -> List[GeneratedTask]:
        """Generate bi-weekly schedule"""
        reminder_time = pattern.time_preference or self.default_times["morning"]
        # Default to Monday for bi-weekly tasks
        preferred_day = 0  # Monday

        return [
            GeneratedTask(
                name=task_name,
                description=description,
                reminder_time=reminder_time,
                days_of_week=[preferred_day],
                is_recurring=True,
                interval_days=14,  # Every 14 days
            )
        ]

    def _generate_fallback_schedule(
        self,
        task_name: str,
        description: Optional[str],
        time_preference: Optional[time],
    ) -> List[GeneratedTask]:
        """Generate fallback schedule when parsing fails"""
        reminder_time = time_preference or self.default_times["morning"]

        # Default to 3 times a week (Monday, Wednesday, Friday)
        return [
            GeneratedTask(
                name=f"{task_name} (Monday)",
                description=description,
                reminder_time=reminder_time,
                days_of_week=[0],  # Monday
                is_recurring=True,
            ),
            GeneratedTask(
                name=f"{task_name} (Wednesday)",
                description=description,
                reminder_time=reminder_time,
                days_of_week=[2],  # Wednesday
                is_recurring=True,
            ),
            GeneratedTask(
                name=f"{task_name} (Friday)",
                description=description,
                reminder_time=reminder_time,
                days_of_week=[4],  # Friday
                is_recurring=True,
            ),
        ]

    def _distribute_days_evenly(self, frequency: int) -> List[int]:
        """Distribute high frequency across week evenly"""
        if frequency >= 7:
            return list(range(7))  # Every day

        # Calculate spacing
        spacing = 7 / frequency
        days = []
        current = 0

        for i in range(frequency):
            days.append(int(current) % 7)
            current += spacing

        return sorted(list(set(days)))  # Remove duplicates and sort

    def optimize_schedule_for_user_preferences(
        self, tasks: List[GeneratedTask], user_preferences: Dict[str, Any]
    ) -> List[GeneratedTask]:
        """Optimize schedule based on user preferences"""

        optimized_tasks = tasks.copy()

        # Avoid user's busy days
        if "busy_days" in user_preferences:
            busy_days = user_preferences["busy_days"]
            for task in optimized_tasks:
                task.days_of_week = [
                    day for day in task.days_of_week if day not in busy_days
                ]

                # If all days were removed, find alternatives
                if not task.days_of_week and not task.interval_days:
                    available_days = [day for day in range(7) if day not in busy_days]
                    if available_days:
                        task.days_of_week = [
                            available_days[0]
                        ]  # Use first available day

        # Respect preferred time ranges
        if "preferred_time_range" in user_preferences:
            start_time, end_time = user_preferences["preferred_time_range"]
            for task in optimized_tasks:
                if not (start_time <= task.reminder_time <= end_time):
                    # Adjust to preferred range
                    task.reminder_time = start_time

        # Avoid time conflicts
        optimized_tasks = self._resolve_time_conflicts(optimized_tasks)

        return optimized_tasks

    def _resolve_time_conflicts(
        self, tasks: List[GeneratedTask]
    ) -> List[GeneratedTask]:
        """Resolve time conflicts by adjusting reminder times"""
        time_slots = {}

        for task in tasks:
            for day in task.days_of_week:
                key = (day, task.reminder_time)
                if key in time_slots:
                    # Conflict detected - adjust time
                    new_time = self._find_next_available_time(
                        task.reminder_time, time_slots, day
                    )
                    task.reminder_time = new_time

                time_slots[(day, task.reminder_time)] = task

        return tasks

    def _find_next_available_time(
        self, preferred_time: time, time_slots: Dict, day: int
    ) -> time:
        """Find next available time slot"""
        current_time = preferred_time

        for _ in range(48):  # Try up to 24 hours in 30-minute increments
            if (day, current_time) not in time_slots:
                return current_time

            # Add 30 minutes
            current_datetime = datetime.combine(datetime.today(), current_time)
            current_datetime += timedelta(minutes=30)
            current_time = current_datetime.time()

        return preferred_time  # Fallback to original if no slot found

    def validate_schedule(self, tasks: List[GeneratedTask]) -> Tuple[bool, List[str]]:
        """Validate generated schedule for conflicts and issues"""
        errors = []

        # Check for time conflicts
        time_conflicts = self._check_time_conflicts(tasks)
        if time_conflicts:
            errors.extend(time_conflicts)

        # Check for reasonable frequency
        frequency_issues = self._check_frequency_reasonableness(tasks)
        if frequency_issues:
            errors.extend(frequency_issues)

        # Check for day distribution
        distribution_issues = self._check_day_distribution(tasks)
        if distribution_issues:
            errors.extend(distribution_issues)

        return len(errors) == 0, errors

    def _check_time_conflicts(self, tasks: List[GeneratedTask]) -> List[str]:
        """Check for tasks scheduled at the same time on same days"""
        conflicts = []

        for i, task1 in enumerate(tasks):
            for j, task2 in enumerate(tasks[i + 1 :], i + 1):
                # Check if tasks overlap in days and time
                common_days = set(task1.days_of_week) & set(task2.days_of_week)
                if common_days and task1.reminder_time == task2.reminder_time:
                    conflicts.append(
                        f"Time conflict: '{task1.name}' and '{task2.name}' "
                        f"both scheduled at {task1.reminder_time.strftime('%H:%M')}"
                    )

        return conflicts

    def _check_frequency_reasonableness(self, tasks: List[GeneratedTask]) -> List[str]:
        """Check if frequency is reasonable"""
        issues = []

        total_weekly_tasks = 0
        for task in tasks:
            if task.interval_days:
                # Interval-based tasks
                weekly_frequency = 7 / task.interval_days
                total_weekly_tasks += weekly_frequency
            else:
                # Day-based tasks
                total_weekly_tasks += len(task.days_of_week)

        if total_weekly_tasks > 14:  # More than 2 tasks per day on average
            issues.append(
                f"High frequency detected: {total_weekly_tasks:.1f} tasks per week. "
                "Consider reducing frequency for better sustainability."
            )

        return issues

    def _check_day_distribution(self, tasks: List[GeneratedTask]) -> List[str]:
        """Check for poor day distribution"""
        issues = []

        # Count tasks per day
        day_counts = [0] * 7
        for task in tasks:
            for day in task.days_of_week:
                day_counts[day] += 1

        max_daily = max(day_counts) if day_counts else 0
        if max_daily > 3:
            day_names = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            overloaded_days = [
                day_names[i] for i, count in enumerate(day_counts) if count > 3
            ]
            issues.append(
                f"Heavy load on {', '.join(overloaded_days)}. "
                "Consider redistributing tasks for better balance."
            )

        return issues

    def suggest_schedule_improvements(self, tasks: List[GeneratedTask]) -> List[str]:
        """Suggest improvements to the generated schedule"""
        suggestions = []

        # Check for clustering
        day_counts = [0] * 7
        for task in tasks:
            for day in task.days_of_week:
                day_counts[day] += 1

        # Suggest spreading out if clustered
        max_count = max(day_counts) if day_counts else 0
        min_count = min(day_counts) if day_counts else 0

        if max_count - min_count > 2:
            suggestions.append("Consider spreading tasks more evenly across the week")

        # Check for weekend balance
        weekday_tasks = sum(day_counts[:5])  # Monday-Friday
        weekend_tasks = sum(day_counts[5:])  # Saturday-Sunday

        if weekday_tasks > 0 and weekend_tasks == 0:
            suggestions.append(
                "Consider adding some weekend activities for better work-life balance"
            )

        # Check for early morning clustering
        early_morning_tasks = sum(1 for task in tasks if task.reminder_time.hour < 7)
        if early_morning_tasks > 2:
            suggestions.append(
                "Multiple early morning tasks detected - ensure this is sustainable"
            )

        return suggestions

    def get_schedule_summary(self, tasks: List[GeneratedTask]) -> Dict[str, Any]:
        """Get a summary of the generated schedule"""

        total_tasks = len(tasks)
        weekly_frequency = 0

        for task in tasks:
            if task.interval_days:
                weekly_frequency += 7 / task.interval_days
            else:
                weekly_frequency += len(task.days_of_week)

        # Get time distribution
        time_distribution = {}
        for task in tasks:
            hour = task.reminder_time.hour
            if hour < 12:
                period = "Morning"
            elif hour < 17:
                period = "Afternoon"
            else:
                period = "Evening"

            time_distribution[period] = time_distribution.get(period, 0) + 1

        # Get day distribution
        day_distribution = [0] * 7
        for task in tasks:
            for day in task.days_of_week:
                day_distribution[day] += 1

        return {
            "total_tasks": total_tasks,
            "weekly_frequency": round(weekly_frequency, 1),
            "time_distribution": time_distribution,
            "day_distribution": day_distribution,
            "busiest_day": day_distribution.index(max(day_distribution))
            if day_distribution
            else None,
            "average_daily_tasks": round(weekly_frequency / 7, 1),
        }
