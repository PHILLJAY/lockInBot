"""
Tests for the Natural Language Parser service.
"""

import pytest
from datetime import time
from unittest.mock import AsyncMock, MagicMock

from src.services.natural_language_parser import (
    NaturalLanguageParser,
    TaskIntent,
    SchedulePattern,
    ScheduleType,
)


class TestNaturalLanguageParser:
    """Test cases for natural language parsing"""

    @pytest.fixture
    def mock_ai_handler(self):
        """Mock AI handler for testing"""
        mock = MagicMock()
        mock.client = AsyncMock()
        mock.config = MagicMock()
        mock.config.openai_model = "gpt-4o-mini"
        return mock

    @pytest.fixture
    def parser(self, mock_ai_handler):
        """Create parser instance for testing"""
        return NaturalLanguageParser(mock_ai_handler)

    @pytest.mark.asyncio
    async def test_parse_daily_pattern(self, parser):
        """Test parsing daily patterns"""
        result = await parser._parse_with_rules("I want to work out daily")

        assert result.task_name == "work out"
        assert result.frequency_type == "daily"
        assert result.frequency_value == 1

    @pytest.mark.asyncio
    async def test_parse_weekly_count_pattern(self, parser):
        """Test parsing weekly count patterns"""
        test_cases = [
            ("work out 3 times a week", 3),
            ("exercise twice per week", 2),
            ("run once a week", 1),
            ("lift 4 times a week", 4),
        ]

        for input_text, expected_count in test_cases:
            result = await parser._parse_with_rules(input_text)
            assert result.frequency_type == "weekly_count"
            assert result.frequency_value == expected_count

    @pytest.mark.asyncio
    async def test_parse_specific_days(self, parser):
        """Test parsing specific day patterns"""
        test_cases = [
            (
                "read every weekday",
                ["monday", "tuesday", "wednesday", "thursday", "friday"],
            ),
            ("meditate on weekends", ["saturday", "sunday"]),
            ("yoga every monday", ["monday"]),
        ]

        for input_text, expected_days in test_cases:
            result = await parser._parse_with_rules(input_text)
            assert result.frequency_type == "specific_days"
            assert result.frequency_value == expected_days

    @pytest.mark.asyncio
    async def test_parse_interval_patterns(self, parser):
        """Test parsing interval patterns"""
        test_cases = [
            ("run every other day", 2),
            ("exercise every two days", 2),
            ("workout every three days", 3),
        ]

        for input_text, expected_interval in test_cases:
            result = await parser._parse_with_rules(input_text)
            assert result.frequency_type == "interval"
            assert result.frequency_value == expected_interval

    @pytest.mark.asyncio
    async def test_parse_time_expressions(self, parser):
        """Test parsing various time expressions"""
        test_cases = [
            ("morning", time(8, 0)),
            ("7:30 AM", time(7, 30)),
            ("2:15 PM", time(14, 15)),
            ("before work", time(7, 0)),
            ("after work", time(17, 30)),
            ("18:00", time(18, 0)),
        ]

        for time_text, expected_time in test_cases:
            result = await parser.parse_time_expression(time_text)
            assert result == expected_time

    @pytest.mark.asyncio
    async def test_invalid_time_expressions(self, parser):
        """Test handling of invalid time expressions"""
        invalid_times = ["25:00", "not a time", "maybe later", "13:70"]

        for invalid_time in invalid_times:
            result = await parser.parse_time_expression(invalid_time)
            assert result is None

    @pytest.mark.asyncio
    async def test_confidence_scoring(self, parser):
        """Test confidence scoring for parsed intents"""
        # High confidence cases
        high_confidence_inputs = [
            "work out 3 times a week at 7 AM",
            "read daily at 9 PM",
            "meditate every weekday morning",
        ]

        for input_text in high_confidence_inputs:
            result = await parser._parse_with_rules(input_text)
            assert result.confidence > 0.7

        # Low confidence cases
        low_confidence_inputs = ["exercise", "be healthy", "do stuff"]

        for input_text in low_confidence_inputs:
            result = await parser._parse_with_rules(input_text)
            assert result.confidence < 0.5

    @pytest.mark.asyncio
    async def test_missing_info_detection(self, parser):
        """Test detection of missing information"""
        test_cases = [
            ("exercise", ["frequency", "time"]),
            ("work out daily", ["time"]),
            ("read at 9 PM", ["frequency"]),
        ]

        for input_text, expected_missing in test_cases:
            result = await parser._parse_with_rules(input_text)
            for missing_item in expected_missing:
                assert missing_item in result.missing_info

    @pytest.mark.asyncio
    async def test_create_schedule_pattern(self, parser):
        """Test creation of schedule patterns from task intents"""
        intent = TaskIntent(
            task_name="workout",
            frequency_type="weekly_count",
            frequency_value=3,
            time_preference="7:00 AM",
            confidence=0.9,
        )

        pattern = await parser.create_schedule_pattern(intent)

        assert pattern.schedule_type == ScheduleType.WEEKLY_COUNT
        assert pattern.frequency == 3
        assert pattern.time_preference == time(7, 0)

    def test_validate_parsed_intent(self, parser):
        """Test validation of parsed intents"""
        # Valid intent
        valid_intent = TaskIntent(
            task_name="workout",
            frequency_type="weekly_count",
            frequency_value=3,
            confidence=0.8,
        )

        is_valid, errors = parser.validate_parsed_intent(valid_intent)
        assert is_valid
        assert len(errors) == 0

        # Invalid intent - too high frequency
        invalid_intent = TaskIntent(
            task_name="workout",
            frequency_type="weekly_count",
            frequency_value=20,
            confidence=0.8,
        )

        is_valid, errors = parser.validate_parsed_intent(invalid_intent)
        assert not is_valid
        assert len(errors) > 0

    @pytest.mark.asyncio
    async def test_complex_parsing_scenarios(self, parser):
        """Test complex real-world parsing scenarios"""
        complex_cases = [
            {
                "input": "I want to work out Monday Wednesday Friday at 7:30 AM",
                "expected_task": "work out",
                "expected_frequency": "specific_days",
                "expected_days": ["monday", "wednesday", "friday"],
                "expected_time": "7:30 AM",
            },
            {
                "input": "read every weekday morning for 30 minutes",
                "expected_task": "read",
                "expected_frequency": "specific_days",
                "expected_days": [
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                ],
                "expected_time": "morning",
            },
            {
                "input": "meditate daily before bed",
                "expected_task": "meditate",
                "expected_frequency": "daily",
                "expected_time": "before bed",
            },
        ]

        for case in complex_cases:
            result = await parser._parse_with_rules(case["input"])

            assert case["expected_task"] in result.task_name.lower()
            assert result.frequency_type == case["expected_frequency"]

            if "expected_days" in case:
                assert result.frequency_value == case["expected_days"]

            if "expected_time" in case:
                assert result.time_preference == case["expected_time"]

    def test_task_name_extraction(self, parser):
        """Test task name extraction from various inputs"""
        test_cases = [
            ("I want to work out daily", "work out"),
            ("exercise 3 times a week", "exercise"),
            ("read books every night", "read"),
            ("do yoga in the morning", "yoga"),
            ("go for a run", "run"),
        ]

        for input_text, expected_task in test_cases:
            extracted = parser._extract_task_name(input_text.lower())
            assert expected_task in extracted.lower()

    def test_frequency_extraction_edge_cases(self, parser):
        """Test frequency extraction edge cases"""
        edge_cases = [
            ("work out every single day", ("daily", 1)),
            (
                "exercise on monday and wednesday",
                ("specific_days", ["monday", "wednesday"]),
            ),
            ("run every 2 weeks", ("bi_weekly", 14)),
            ("lift weights twice monthly", ("bi_weekly", 14)),
        ]

        for input_text, (expected_type, expected_value) in edge_cases:
            freq_type, freq_value = parser._extract_frequency(input_text.lower())
            assert freq_type == expected_type
            if expected_value is not None:
                assert freq_value == expected_value
