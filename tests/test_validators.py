"""
Tests for validation utilities.
"""

import pytest
from datetime import time
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.validators import (
    validate_task_name,
    validate_task_description,
    validate_time_format,
    validate_timezone,
    validate_image_file,
    validate_task_id,
    sanitize_text_input,
)


class TestTaskNameValidation:
    """Test task name validation."""

    def test_valid_task_names(self):
        """Test valid task names."""
        valid_names = [
            "Exercise",
            "Morning Workout",
            "Read for 30 minutes",
            "Take vitamins",
            "Walk the dog",
        ]

        for name in valid_names:
            is_valid, error = validate_task_name(name)
            assert is_valid, f"'{name}' should be valid but got error: {error}"

    def test_invalid_task_names(self):
        """Test invalid task names."""
        invalid_names = [
            "",  # Empty
            " ",  # Whitespace only
            "A",  # Too short
            "A" * 101,  # Too long
            "Task with <invalid> characters",  # Invalid characters
            "Task with @mention",  # Invalid characters
        ]

        for name in invalid_names:
            is_valid, error = validate_task_name(name)
            assert not is_valid, f"'{name}' should be invalid but was accepted"
            assert error is not None


class TestTaskDescriptionValidation:
    """Test task description validation."""

    def test_valid_descriptions(self):
        """Test valid descriptions."""
        valid_descriptions = [
            None,  # No description
            "",  # Empty description
            "A simple description",
            "A" * 500,  # Max length
        ]

        for desc in valid_descriptions:
            is_valid, error = validate_task_description(desc)
            assert is_valid, f"Description should be valid but got error: {error}"

    def test_invalid_descriptions(self):
        """Test invalid descriptions."""
        invalid_descriptions = [
            "A" * 501,  # Too long
        ]

        for desc in invalid_descriptions:
            is_valid, error = validate_task_description(desc)
            assert not is_valid, f"Description should be invalid but was accepted"


class TestTimeFormatValidation:
    """Test time format validation."""

    def test_valid_time_formats(self):
        """Test valid time formats."""
        valid_times = [
            ("07:30", time(7, 30)),
            ("14:00", time(14, 0)),
            ("23:59", time(23, 59)),
            ("00:00", time(0, 0)),
        ]

        for time_str, expected_time in valid_times:
            is_valid, error, parsed_time = validate_time_format(time_str)
            assert is_valid, f"'{time_str}' should be valid but got error: {error}"
            assert parsed_time == expected_time

    def test_invalid_time_formats(self):
        """Test invalid time formats."""
        invalid_times = [
            "",  # Empty
            "25:00",  # Invalid hour
            "12:60",  # Invalid minute
            "abc",  # Not a time
            "12",  # Missing minutes
        ]

        for time_str in invalid_times:
            is_valid, error, parsed_time = validate_time_format(time_str)
            assert not is_valid, f"'{time_str}' should be invalid but was accepted"
            assert parsed_time is None


class TestTimezoneValidation:
    """Test timezone validation."""

    def test_valid_timezones(self):
        """Test valid timezones."""
        valid_timezones = [
            "UTC",
            "America/Toronto",
            "Europe/London",
            "Asia/Tokyo",
        ]

        for tz in valid_timezones:
            is_valid, error = validate_timezone(tz)
            assert is_valid, f"'{tz}' should be valid but got error: {error}"

    def test_invalid_timezones(self):
        """Test invalid timezones."""
        invalid_timezones = [
            "",  # Empty
            "Invalid/Timezone",
            "Not_A_Timezone",
        ]

        for tz in invalid_timezones:
            is_valid, error = validate_timezone(tz)
            assert not is_valid, f"'{tz}' should be invalid but was accepted"


class TestImageFileValidation:
    """Test image file validation."""

    def test_valid_image_files(self):
        """Test valid image files."""
        valid_files = [
            ("image.jpg", "image/jpeg", 1024 * 1024),  # 1MB JPEG
            ("photo.png", "image/png", 2 * 1024 * 1024),  # 2MB PNG
            ("pic.webp", "image/webp", 500 * 1024),  # 500KB WebP
        ]

        for filename, content_type, size in valid_files:
            is_valid, error = validate_image_file(filename, content_type, size)
            assert is_valid, f"File should be valid but got error: {error}"

    def test_invalid_image_files(self):
        """Test invalid image files."""
        invalid_files = [
            ("file.txt", "text/plain", 1024),  # Wrong type
            ("image.jpg", "image/jpeg", 20 * 1024 * 1024),  # Too large
            ("virus.exe", "application/exe", 1024),  # Suspicious extension
        ]

        for filename, content_type, size in invalid_files:
            is_valid, error = validate_image_file(filename, content_type, size)
            assert not is_valid, f"File should be invalid but was accepted"


class TestTaskIdValidation:
    """Test task ID validation."""

    def test_valid_task_ids(self):
        """Test valid task IDs."""
        valid_ids = ["1", "123", "999999"]

        for task_id_str in valid_ids:
            is_valid, error, task_id = validate_task_id(task_id_str)
            assert is_valid, f"'{task_id_str}' should be valid but got error: {error}"
            assert task_id == int(task_id_str)

    def test_invalid_task_ids(self):
        """Test invalid task IDs."""
        invalid_ids = ["", "0", "-1", "abc", "1.5"]

        for task_id_str in invalid_ids:
            is_valid, error, task_id = validate_task_id(task_id_str)
            assert not is_valid, f"'{task_id_str}' should be invalid but was accepted"
            assert task_id is None


class TestTextSanitization:
    """Test text sanitization."""

    def test_sanitize_text_input(self):
        """Test text sanitization."""
        test_cases = [
            ("  hello world  ", "hello world"),
            ("hello\u200b\u200cworld", "helloworld"),  # Zero-width chars
            ("multiple   spaces", "multiple spaces"),
            ("", ""),
            ("normal text", "normal text"),
        ]

        for input_text, expected in test_cases:
            result = sanitize_text_input(input_text)
            assert result == expected, f"Expected '{expected}' but got '{result}'"


if __name__ == "__main__":
    pytest.main([__file__])
