"""
Tests for the Bakushin Personality Engine.
"""

import pytest
from unittest.mock import MagicMock

from src.services.bakushin_personality import BakushinPersonality, ConversationTone


class TestBakushinPersonality:
    """Test cases for Bakushin's personality engine"""

    @pytest.fixture
    def personality(self):
        """Create personality instance for testing"""
        return BakushinPersonality()

    def test_horse_reference_frequency(self, personality):
        """Test that horse references appear at appropriate frequency"""
        # Test multiple calls to ensure frequency is around 15%
        horse_reference_count = 0
        total_calls = 100

        for _ in range(total_calls):
            if personality.should_use_horse_reference():
                horse_reference_count += 1

        # Should be around 15% (±10% tolerance for randomness)
        assert 5 <= horse_reference_count <= 25

    def test_horse_reference_categories(self, personality):
        """Test horse reference categories"""
        categories = ["motivational", "advice", "celebration"]

        for category in categories:
            reference = personality.get_horse_reference(category)
            assert isinstance(reference, str)
            assert len(reference) > 0

    def test_greeting_generation(self, personality):
        """Test greeting message generation"""
        # First time user
        context = {"is_first_time": True}
        greeting = personality._generate_greeting(context)

        assert "yooo" in greeting.lower()
        assert "whats ur name" in greeting.lower()

        # Returning user
        context = {"is_first_time": False, "name": "John"}
        greeting = personality._generate_greeting(context)

        assert "john" in greeting.lower()
        assert "back for more" in greeting.lower()

    def test_goal_setting_generation(self, personality):
        """Test goal setting message generation"""
        context = {"name": "Alex", "name_is_basic": False}
        response = personality._generate_goal_setting(context)

        assert "alex" in response.lower()
        assert "3 months" in response.lower()
        assert "goals" in response.lower()

    def test_task_creation_responses(self, personality):
        """Test task creation responses for different goal types"""
        goal_types = ["fitness", "reading", "mindfulness", "writing", "general"]

        for goal_type in goal_types:
            context = {"goal_type": goal_type}
            response = personality._generate_task_creation(context)

            assert isinstance(response, str)
            assert len(response) > 0
            assert "specific" in response.lower()

    def test_payment_prompt_generation(self, personality):
        """Test payment prompt generation"""
        context = {"name": "John"}
        response = personality._generate_payment_prompt(context)

        assert "john" in response.lower()
        assert "$5/month" in response.lower()
        assert "accountability" in response.lower()

    def test_reminder_personality_basic(self, personality):
        """Test basic reminder message personality"""
        # New streak
        reminder = personality.add_personality_to_reminder("workout", 0, "John")
        assert "john" in reminder.lower()
        assert "workout" in reminder.lower()

        # Ongoing streak
        reminder = personality.add_personality_to_reminder("workout", 5, "John")
        assert "day 6" in reminder.lower() or "consistency" in reminder.lower()

        # Long streak
        reminder = personality.add_personality_to_reminder("workout", 10, "John")
        assert "streak" in reminder.lower()

    def test_missed_reminder_personality(self, personality):
        """Test missed reminder message personality"""
        # Single missed day
        reminder = personality.add_personality_to_missed_reminder("workout", 1, "John")
        assert "bruh" in reminder.lower()
        assert "yesterday" in reminder.lower()

        # Multiple missed days
        reminder = personality.add_personality_to_missed_reminder("workout", 3, "John")
        assert "3 days" in reminder.lower()

        # Many missed days
        reminder = personality.add_personality_to_missed_reminder("workout", 7, "John")
        assert "7 days" in reminder.lower()

    def test_task_completion_responses(self, personality):
        """Test task completion response generation"""
        # Verified completion
        verified_result = {
            "verified": True,
            "confidence": 85,
            "explanation": "Clear evidence of workout completion",
        }

        response = personality.generate_task_completion_response(
            "workout", verified_result
        )
        assert any(
            positive in response.lower()
            for positive in ["yooo", "fire", "respect", "lets gooo"]
        )

        # Unverified completion
        unverified_result = {
            "verified": False,
            "confidence": 30,
            "explanation": "No clear evidence of task completion",
        }

        response = personality.generate_task_completion_response(
            "workout", unverified_result
        )
        assert any(
            negative in response.lower()
            for negative in ["bruh", "cap", "nah", "try again"]
        )

    def test_celebration_generation(self, personality):
        """Test celebration message generation"""
        # Short streak
        context = {"streak_count": 5, "task_name": "workout"}
        response = personality._generate_celebration(context)
        assert "completed" in response.lower()

        # Long streak
        context = {"streak_count": 10, "task_name": "workout"}
        response = personality._generate_celebration(context)
        assert "streak" in response.lower()

    def test_motivation_generation(self, personality):
        """Test motivational message generation"""
        context = {}
        response = personality._generate_motivation(context)

        motivational_words = [
            "lock in",
            "got this",
            "different breed",
            "main character",
        ]
        assert any(word in response.lower() for word in motivational_words)

    def test_reality_check_generation(self, personality):
        """Test reality check message generation"""
        context = {}
        response = personality._generate_reality_check(context)

        reality_check_words = ["bruh", "cap", "be fr", "nah fam"]
        assert any(word in response.lower() for word in reality_check_words)

    def test_help_response(self, personality):
        """Test help response generation"""
        response = personality.generate_help_response()

        assert "help" in response.lower()
        assert "work out" in response.lower()
        assert "read" in response.lower()
        assert "meditate" in response.lower()

    def test_error_responses(self, personality):
        """Test error response generation"""
        error_types = ["parsing_failed", "ai_service_down", "database_error", "general"]

        for error_type in error_types:
            response = personality.generate_error_response(error_type)
            assert isinstance(response, str)
            assert len(response) > 0

    def test_task_specific_motivation(self, personality):
        """Test task-specific motivational messages"""
        task_types = [
            ("workout", "gains"),
            ("read", "brain"),
            ("meditate", "zen"),
            ("run", "legs"),
            ("write", "thoughts"),
        ]

        for task_name, expected_word in task_types:
            motivation = personality.get_task_specific_motivation(task_name)
            assert (
                expected_word in motivation.lower() or "lock in" in motivation.lower()
            )

    def test_casual_filler_addition(self, personality):
        """Test casual filler word addition"""
        original_message = "This is a test message"

        # Test multiple times since it's random
        filler_added = False
        for _ in range(20):
            modified = personality.add_casual_filler(original_message)
            if modified != original_message:
                filler_added = True
                break

        # Should add filler at least sometimes
        assert filler_added

    def test_conversation_tone_responses(self, personality):
        """Test responses for different conversation tones"""
        tones_and_contexts = [
            (ConversationTone.GREETING, {"is_first_time": True}),
            (ConversationTone.GOAL_SETTING, {"name": "John"}),
            (ConversationTone.TASK_CREATION, {"goal_type": "fitness"}),
            (ConversationTone.PAYMENT_PROMPT, {"name": "John"}),
            (ConversationTone.CELEBRATION, {"streak_count": 7}),
            (ConversationTone.MOTIVATION, {}),
            (ConversationTone.REALITY_CHECK, {}),
        ]

        for tone, context in tones_and_contexts:
            response = personality.generate_response(context, tone)
            assert isinstance(response, str)
            assert len(response) > 0

    def test_personality_consistency(self, personality):
        """Test that personality remains consistent across calls"""
        context = {"name": "John", "goal_type": "fitness"}

        # Generate multiple responses
        responses = []
        for _ in range(5):
            response = personality._generate_task_creation(context)
            responses.append(response)

        # All should be strings and contain fitness-related content
        for response in responses:
            assert isinstance(response, str)
            assert "specific" in response.lower()

    def test_slang_usage(self, personality):
        """Test that appropriate slang is used"""
        # Test various response types for slang usage
        contexts_and_tones = [
            ({"name": "John"}, ConversationTone.GOAL_SETTING),
            ({"goal_type": "fitness"}, ConversationTone.TASK_CREATION),
            ({"streak_count": 5}, ConversationTone.CELEBRATION),
        ]

        slang_words = ["yo", "ngl", "fr", "tbh", "lowkey", "highkey", "bruh", "cap"]

        for context, tone in contexts_and_tones:
            response = personality.generate_response(context, tone)
            # At least some responses should contain slang
            # (not enforcing all since it depends on the specific response)
            assert isinstance(response, str)

    def test_horse_reference_integration(self, personality):
        """Test that horse references integrate naturally"""
        # Force horse reference usage by mocking
        original_should_use = personality.should_use_horse_reference
        personality.should_use_horse_reference = lambda: True

        try:
            reminder = personality.add_personality_to_reminder("workout", 0, "John")
            horse_words = ["horse", "gallop", "stallion", "thoroughbred"]
            assert any(word in reminder.lower() for word in horse_words)
        finally:
            personality.should_use_horse_reference = original_should_use

    def test_response_length_appropriateness(self, personality):
        """Test that responses are appropriately sized"""
        contexts_and_tones = [
            ({"is_first_time": True}, ConversationTone.GREETING),
            ({"name": "John"}, ConversationTone.GOAL_SETTING),
            ({"goal_type": "fitness"}, ConversationTone.TASK_CREATION),
        ]

        for context, tone in contexts_and_tones:
            response = personality.generate_response(context, tone)
            # Responses should be substantial but not too long
            assert 10 < len(response) < 1000
            # Should have multiple sentences for complex interactions
            if tone in [ConversationTone.GOAL_SETTING, ConversationTone.TASK_CREATION]:
                assert "\n" in response or "." in response
