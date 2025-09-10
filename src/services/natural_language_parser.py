"""
Natural Language Parser for Bakushin AI - parses casual task creation requests.
"""

import logging
import re
from datetime import time, datetime
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ScheduleType(Enum):
    DAILY = "daily"
    WEEKLY_COUNT = "weekly_count"
    SPECIFIC_DAYS = "specific_days"
    INTERVAL = "interval"
    BI_WEEKLY = "bi_weekly"


@dataclass
class TaskIntent:
    """Represents parsed task intent from natural language"""

    task_name: str
    frequency_type: str
    frequency_value: Any = None
    time_preference: Optional[str] = None
    description: Optional[str] = None
    confidence: float = 0.0
    missing_info: Optional[List[str]] = None
    parsed_time: Optional[time] = None

    def __post_init__(self):
        if self.missing_info is None:
            self.missing_info = []


@dataclass
class SchedulePattern:
    """Represents a schedule pattern for task generation"""

    schedule_type: ScheduleType
    frequency: Optional[int] = None
    specific_days: Optional[List[str]] = None
    interval_days: Optional[int] = None
    start_date: Optional[datetime] = None
    time_preference: Optional[time] = None


class NaturalLanguageParser:
    """Parses natural language input into structured task intents"""

    def __init__(self, ai_handler):
        self.ai_handler = ai_handler

        # Time patterns and mappings
        self.time_patterns = {
            "morning": time(8, 0),
            "early morning": time(6, 0),
            "late morning": time(10, 0),
            "afternoon": time(14, 0),
            "early afternoon": time(13, 0),
            "late afternoon": time(16, 0),
            "evening": time(18, 0),
            "early evening": time(17, 0),
            "late evening": time(20, 0),
            "night": time(21, 0),
            "before work": time(7, 0),
            "after work": time(17, 30),
            "lunch time": time(12, 0),
            "before bed": time(21, 30),
            "wake up": time(7, 0),
        }

        # Frequency patterns
        self.frequency_patterns = {
            # Daily patterns
            r"daily|every day|each day": ("daily", 1),
            # Weekly count patterns
            r"(\d+)\s*times?\s*(?:a|per)\s*week": ("weekly_count", None),
            r"once\s*(?:a|per)\s*week": ("weekly_count", 1),
            r"twice\s*(?:a|per)\s*week": ("weekly_count", 2),
            r"three times\s*(?:a|per)\s*week": ("weekly_count", 3),
            r"four times\s*(?:a|per)\s*week": ("weekly_count", 4),
            r"five times\s*(?:a|per)\s*week": ("weekly_count", 5),
            # Interval patterns
            r"every other day": ("interval", 2),
            r"every two days": ("interval", 2),
            r"every three days": ("interval", 3),
            r"every (\d+) days": ("interval", None),
            # Bi-weekly patterns
            r"every two weeks": ("bi_weekly", 14),
            r"bi-weekly": ("bi_weekly", 14),
            r"twice a month": ("bi_weekly", 14),
            # Day-specific patterns
            r"weekdays?(?:\s*only)?": (
                "specific_days",
                ["monday", "tuesday", "wednesday", "thursday", "friday"],
            ),
            r"weekends?(?:\s*only)?": ("specific_days", ["saturday", "sunday"]),
            r"work days?": (
                "specific_days",
                ["monday", "tuesday", "wednesday", "thursday", "friday"],
            ),
        }

        # Day patterns
        self.day_patterns = {
            # Single days
            r"(?:every\s*)?mondays?": ["monday"],
            r"(?:every\s*)?tuesdays?": ["tuesday"],
            r"(?:every\s*)?wednesdays?": ["wednesday"],
            r"(?:every\s*)?thursdays?": ["thursday"],
            r"(?:every\s*)?fridays?": ["friday"],
            r"(?:every\s*)?saturdays?": ["saturday"],
            r"(?:every\s*)?sundays?": ["sunday"],
            # Multiple days
            r"monday\s*(?:and|,)\s*wednesday\s*(?:and|,)?\s*friday": [
                "monday",
                "wednesday",
                "friday",
            ],
            r"tuesday\s*(?:and|,)\s*thursday": ["tuesday", "thursday"],
            r"saturday\s*(?:and|,)\s*sunday": ["saturday", "sunday"],
            r"monday\s*(?:and|,)\s*friday": ["monday", "friday"],
            # Day ranges
            r"monday\s*(?:through|to|-)\s*friday": [
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
            ],
            r"monday\s*(?:through|to|-)\s*wednesday": [
                "monday",
                "tuesday",
                "wednesday",
            ],
        }

        # Task name extraction patterns
        self.task_verbs = [
            "work out",
            "exercise",
            "run",
            "jog",
            "lift",
            "gym",
            "read",
            "study",
            "learn",
            "practice",
            "meditate",
            "yoga",
            "stretch",
            "write",
            "journal",
            "blog",
            "cook",
            "meal prep",
            "eat",
            "walk",
            "hike",
            "bike",
            "code",
            "program",
            "develop",
            "clean",
            "organize",
            "tidy",
        ]

    async def parse_task_intent(self, user_input: str) -> TaskIntent:
        """Parse natural language input into structured task intent"""

        try:
            # First try AI parsing for complex cases
            ai_result = await self._parse_with_ai(user_input)

            # Also do rule-based parsing as fallback/validation
            rule_result = self._parse_with_rules(user_input)

            # Merge results with AI taking precedence but rules as validation
            return self._merge_parsing_results(ai_result, rule_result, user_input)

        except Exception as e:
            logger.error(f"Error parsing task intent: {e}")
            # Fallback to rule-based only
            return self._parse_with_rules(user_input)

    async def _parse_with_ai(self, user_input: str) -> TaskIntent:
        """Use AI to parse complex natural language"""

        prompt = f"""
Parse this task creation request and extract structured information:

Input: "{user_input}"

Extract:
1. Task name/activity (what they want to do)
2. Frequency pattern (daily, weekly count, specific days, interval)
3. Frequency value (number or list of days)
4. Time preference (if mentioned)
5. Confidence score (0-100)
6. Missing information needed

Respond in this exact JSON format:
{{
    "task_name": "extracted activity",
    "frequency_type": "daily|weekly_count|specific_days|interval|bi_weekly",
    "frequency_value": "number or list",
    "time_preference": "extracted time or null",
    "confidence": 85,
    "missing_info": ["list of missing required info"]
}}

Examples:
- "work out 3 times a week" → {{"task_name": "work out", "frequency_type": "weekly_count", "frequency_value": 3, "confidence": 90}}
- "read every weekday morning" → {{"task_name": "read", "frequency_type": "specific_days", "frequency_value": ["monday","tuesday","wednesday","thursday","friday"], "time_preference": "morning", "confidence": 95}}
- "exercise" → {{"task_name": "exercise", "frequency_type": "unknown", "confidence": 30, "missing_info": ["frequency", "time"]}}
"""

        try:
            response = await self.ai_handler.client.chat.completions.create(
                model=self.ai_handler.config.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.3,
            )

            # Parse JSON response
            import json

            result_text = response.choices[0].message.content.strip()

            # Extract JSON from response (in case there's extra text)
            json_start = result_text.find("{")
            json_end = result_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_text = result_text[json_start:json_end]
                parsed_data = json.loads(json_text)

                return TaskIntent(
                    task_name=parsed_data.get("task_name", ""),
                    frequency_type=parsed_data.get("frequency_type", "unknown"),
                    frequency_value=parsed_data.get("frequency_value"),
                    time_preference=parsed_data.get("time_preference"),
                    confidence=parsed_data.get("confidence", 0) / 100.0,
                    missing_info=parsed_data.get("missing_info", []),
                )
            else:
                raise ValueError("No valid JSON found in AI response")

        except Exception as e:
            logger.error(f"AI parsing failed: {e}")
            # Return low confidence result
            return TaskIntent(
                task_name=self._extract_task_name_simple(user_input),
                frequency_type="unknown",
                confidence=0.2,
                missing_info=["frequency", "time"],
            )

    def _parse_with_rules(self, text: str) -> TaskIntent:
        """Rule-based parsing as fallback"""
        text_lower = text.lower().strip()

        # Extract task name
        task_name = self._extract_task_name(text_lower)

        # Extract frequency
        frequency_type, frequency_value = self._extract_frequency(text_lower)

        # Extract time
        time_preference = self._extract_time_preference(text_lower)

        # Determine missing info
        missing_info = []
        if frequency_type == "unknown":
            missing_info.append("frequency")
        if not time_preference:
            missing_info.append("time")

        # Calculate confidence
        confidence = self._calculate_rule_confidence(
            task_name, frequency_type, time_preference
        )

        return TaskIntent(
            task_name=task_name,
            frequency_type=frequency_type,
            frequency_value=frequency_value,
            time_preference=time_preference,
            confidence=confidence,
            missing_info=missing_info,
        )

    def _extract_task_name(self, text: str) -> str:
        """Extract task name from text"""

        # Look for common task verbs
        for verb in self.task_verbs:
            if verb in text:
                return verb

        # Try to extract from common patterns
        patterns = [
            r"(?:i want to|i need to|i should|goal is to|plan to)\s+([^,\n]+)",
            r"(?:daily|every day|weekly|times a week)\s+([^,\n]+)",
            r"^([^,\n]+?)\s+(?:daily|every|times|weekly)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                extracted = match.group(1).strip()
                # Clean up common words
                extracted = re.sub(
                    r"^(i want to|i need to|i should|to)\s+", "", extracted
                )
                if len(extracted) > 2:
                    return extracted

        # Fallback: take first few words
        words = text.split()[:3]
        return " ".join(words) if words else "task"

    def _extract_task_name_simple(self, text: str) -> str:
        """Simple task name extraction for fallback"""
        # Remove common prefixes
        text = re.sub(
            r"^(i want to|i need to|i should|goal is to|plan to)\s+", "", text.lower()
        )

        # Take first meaningful words
        words = text.split()[:3]
        return " ".join(words) if words else "task"

    def _extract_frequency(self, text: str) -> Tuple[str, Any]:
        """Extract frequency pattern from text"""

        # Check specific day patterns first
        for pattern, days in self.day_patterns.items():
            if re.search(pattern, text):
                return ("specific_days", days)

        # Check frequency patterns
        for pattern, (freq_type, freq_value) in self.frequency_patterns.items():
            match = re.search(pattern, text)
            if match:
                if freq_type == "weekly_count" and freq_value is None:
                    # Extract number from match
                    try:
                        freq_value = int(match.group(1))
                    except (IndexError, ValueError):
                        freq_value = 1
                elif freq_type == "interval" and freq_value is None:
                    # Extract number from match
                    try:
                        freq_value = int(match.group(1))
                    except (IndexError, ValueError):
                        freq_value = 2

                return (freq_type, freq_value)

        return ("unknown", None)

    def _extract_time_preference(self, text: str) -> Optional[str]:
        """Extract time preference from text"""

        # Check relative times first
        for time_phrase in self.time_patterns.keys():
            if time_phrase in text:
                return time_phrase

        # Check for exact times
        time_patterns = [
            r"(\d{1,2}):(\d{2})\s*([ap]m?)",  # 7:30 AM
            r"(\d{1,2})\s*([ap]m?)",  # 7 AM
            r"(\d{1,2}):(\d{2})",  # 07:30
        ]

        for pattern in time_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)

        return None

    def _calculate_rule_confidence(
        self, task_name: str, frequency_type: str, time_preference: Optional[str]
    ) -> float:
        """Calculate confidence score for rule-based parsing"""
        confidence = 0.5  # Base confidence

        # Task name quality
        if any(verb in task_name.lower() for verb in self.task_verbs):
            confidence += 0.2
        elif len(task_name.split()) >= 2:
            confidence += 0.1

        # Frequency clarity
        if frequency_type != "unknown":
            confidence += 0.2

        # Time specificity
        if time_preference:
            confidence += 0.1

        return min(confidence, 1.0)

    def _merge_parsing_results(
        self, ai_result: TaskIntent, rule_result: TaskIntent, original_input: str
    ) -> TaskIntent:
        """Merge AI and rule-based parsing results"""

        # If AI confidence is high, use AI result with rule validation
        if ai_result.confidence > 0.7:
            # Validate AI result with rules
            if (
                rule_result.frequency_type != "unknown"
                and ai_result.frequency_type == "unknown"
            ):
                ai_result.frequency_type = rule_result.frequency_type
                ai_result.frequency_value = rule_result.frequency_value

            if not ai_result.time_preference and rule_result.time_preference:
                ai_result.time_preference = rule_result.time_preference

            return ai_result

        # If rule confidence is higher, use rule result
        elif rule_result.confidence > ai_result.confidence:
            return rule_result

        # Merge best parts of both
        else:
            merged = TaskIntent(
                task_name=ai_result.task_name
                if ai_result.task_name
                else rule_result.task_name,
                frequency_type=rule_result.frequency_type
                if rule_result.frequency_type != "unknown"
                else ai_result.frequency_type,
                frequency_value=rule_result.frequency_value
                if rule_result.frequency_value
                else ai_result.frequency_value,
                time_preference=rule_result.time_preference
                if rule_result.time_preference
                else ai_result.time_preference,
                confidence=max(ai_result.confidence, rule_result.confidence)
                * 0.8,  # Slightly lower for merged
                missing_info=list(
                    set(
                        (ai_result.missing_info or [])
                        + (rule_result.missing_info or [])
                    )
                ),
            )
            return merged

    async def parse_time_expression(self, time_text: str) -> Optional[time]:
        """Parse various time expressions into time objects"""
        time_text = time_text.lower().strip()

        # Check relative times first
        if time_text in self.time_patterns:
            return self.time_patterns[time_text]

        # Parse exact times
        # 12-hour format with minutes (7:30 AM, 2:15 PM)
        match = re.search(r"(\d{1,2}):(\d{2})\s*([ap]m?)", time_text)
        if match:
            hour, minute, period = match.groups()
            return self._convert_12_hour(int(hour), int(minute), period)

        # 12-hour format without minutes (7 AM, 2 PM)
        match = re.search(r"(\d{1,2})\s*([ap]m?)", time_text)
        if match:
            hour, period = match.groups()
            return self._convert_12_hour(int(hour), 0, period)

        # 24-hour format (07:30, 14:00)
        match = re.search(r"(\d{1,2}):(\d{2})", time_text)
        if match:
            hour, minute = match.groups()
            hour, minute = int(hour), int(minute)
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return time(hour, minute)

        return None

    def _convert_12_hour(self, hour: int, minute: int, period: str) -> Optional[time]:
        """Convert 12-hour format to 24-hour time object"""
        period = period.lower()

        if hour < 1 or hour > 12:
            return None

        if period.startswith("p") and hour != 12:
            hour += 12
        elif period.startswith("a") and hour == 12:
            hour = 0

        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return time(hour, minute)

        return None

    async def create_schedule_pattern(self, intent: TaskIntent) -> SchedulePattern:
        """Convert TaskIntent to SchedulePattern for schedule generation"""

        # Parse time if available
        parsed_time = None
        if intent.time_preference:
            parsed_time = await self.parse_time_expression(intent.time_preference)

        # Convert frequency type to ScheduleType
        if intent.frequency_type == "daily":
            return SchedulePattern(
                schedule_type=ScheduleType.DAILY,
                frequency=1,
                time_preference=parsed_time,
            )
        elif intent.frequency_type == "weekly_count":
            return SchedulePattern(
                schedule_type=ScheduleType.WEEKLY_COUNT,
                frequency=intent.frequency_value or 3,
                time_preference=parsed_time,
            )
        elif intent.frequency_type == "specific_days":
            return SchedulePattern(
                schedule_type=ScheduleType.SPECIFIC_DAYS,
                specific_days=intent.frequency_value
                or ["monday", "wednesday", "friday"],
                time_preference=parsed_time,
            )
        elif intent.frequency_type == "interval":
            return SchedulePattern(
                schedule_type=ScheduleType.INTERVAL,
                interval_days=intent.frequency_value or 2,
                time_preference=parsed_time,
            )
        elif intent.frequency_type == "bi_weekly":
            return SchedulePattern(
                schedule_type=ScheduleType.BI_WEEKLY,
                interval_days=14,
                time_preference=parsed_time,
            )
        else:
            # Default to 3 times a week
            return SchedulePattern(
                schedule_type=ScheduleType.WEEKLY_COUNT,
                frequency=3,
                time_preference=parsed_time,
            )

    def suggest_time_alternatives(self, failed_input: str) -> List[str]:
        """Suggest alternative time formats when parsing fails"""
        return [
            "Try formats like: '7:30 AM', 'morning', 'after work'",
            "Examples: '6:00 PM', 'evening', 'before bed'",
            "Use 24-hour format: '07:30', '18:00'",
        ]

    def suggest_frequency_alternatives(self, failed_input: str) -> List[str]:
        """Suggest alternative frequency formats when parsing fails"""
        return [
            "Try: '3 times a week', 'daily', 'every other day'",
            "Examples: 'weekdays only', 'Monday and Friday', 'twice a week'",
            "Be specific: 'every Tuesday', 'Monday through Friday'",
        ]

    def validate_parsed_intent(self, intent: TaskIntent) -> Tuple[bool, List[str]]:
        """Validate parsed intent for reasonableness"""
        errors = []

        # Check task name
        if not intent.task_name or len(intent.task_name.strip()) < 2:
            errors.append("Task name is too short or missing")

        # Check frequency reasonableness
        if intent.frequency_type == "weekly_count" and intent.frequency_value:
            if intent.frequency_value > 14:
                errors.append(
                    f"Frequency too high: {intent.frequency_value} times per week"
                )
            elif intent.frequency_value < 1:
                errors.append(f"Invalid frequency: {intent.frequency_value}")

        # Check interval reasonableness
        if intent.frequency_type == "interval" and intent.frequency_value:
            if intent.frequency_value > 30:
                errors.append(f"Interval too long: every {intent.frequency_value} days")
            elif intent.frequency_value < 1:
                errors.append(f"Invalid interval: {intent.frequency_value}")

        return len(errors) == 0, errors
