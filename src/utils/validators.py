"""
Input validation utilities for the Discord Task Reminder Bot.
"""

import re
from datetime import datetime, time
from typing import Optional, Tuple, List
import pytz


def validate_task_name(name: str) -> Tuple[bool, Optional[str]]:
    """Validate task name."""
    if not name or not name.strip():
        return False, "Task name cannot be empty"

    name = name.strip()

    if len(name) < 2:
        return False, "Task name must be at least 2 characters long"

    if len(name) > 100:
        return False, "Task name must be 100 characters or less"

    # Check for invalid characters
    if re.search(r"[<>@#&]", name):
        return False, "Task name contains invalid characters"

    return True, None


def validate_task_description(description: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Validate task description."""
    if description is None:
        return True, None

    description = description.strip()

    if len(description) > 500:
        return False, "Task description must be 500 characters or less"

    return True, None


def validate_time_format(time_str: str) -> Tuple[bool, Optional[str], Optional[time]]:
    """Validate time format and return parsed time."""
    if not time_str or not time_str.strip():
        return False, "Time cannot be empty", None

    time_str = time_str.strip()

    # Try to parse HH:MM format
    try:
        parsed_time = datetime.strptime(time_str, "%H:%M").time()
        return True, None, parsed_time
    except ValueError:
        pass

    # Try to parse H:MM format
    try:
        parsed_time = datetime.strptime(time_str, "%H:%M").time()
        return True, None, parsed_time
    except ValueError:
        pass

    # Try common variations
    patterns = [
        ("%H:%M", "24-hour format (e.g., 14:30)"),
        ("%I:%M %p", "12-hour format with AM/PM (e.g., 2:30 PM)"),
        ("%I:%M%p", "12-hour format without space (e.g., 2:30PM)"),
    ]

    for pattern, description in patterns:
        try:
            parsed_time = datetime.strptime(time_str.upper(), pattern).time()
            return True, None, parsed_time
        except ValueError:
            continue

    return (
        False,
        "Invalid time format. Use 24-hour format like '14:30' or '07:00'",
        None,
    )


def validate_timezone(timezone_str: str) -> Tuple[bool, Optional[str]]:
    """Validate timezone string."""
    if not timezone_str or not timezone_str.strip():
        return False, "Timezone cannot be empty"

    timezone_str = timezone_str.strip()

    try:
        pytz.timezone(timezone_str)
        return True, None
    except pytz.exceptions.UnknownTimeZoneError:
        return (
            False,
            f"Invalid timezone: {timezone_str}. Use format like 'America/Toronto' or 'Europe/London'",
        )


def validate_image_file(
    filename: str, content_type: str, size: int, max_size_mb: int = 10
) -> Tuple[bool, Optional[str]]:
    """Validate uploaded image file."""
    # Check content type
    valid_types = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"]

    if content_type not in valid_types:
        return False, f"Invalid file type. Supported formats: JPEG, PNG, WebP, GIF"

    # Check file size
    max_size_bytes = max_size_mb * 1024 * 1024
    if size > max_size_bytes:
        return False, f"File too large. Maximum size: {max_size_mb}MB"

    # Check filename
    if not filename or len(filename) > 255:
        return False, "Invalid filename"

    # Check for suspicious extensions
    suspicious_extensions = [".exe", ".bat", ".cmd", ".scr", ".pif", ".com"]
    filename_lower = filename.lower()

    for ext in suspicious_extensions:
        if filename_lower.endswith(ext):
            return False, "File type not allowed for security reasons"

    return True, None


def validate_task_id(task_id_str: str) -> Tuple[bool, Optional[str], Optional[int]]:
    """Validate task ID."""
    if not task_id_str or not task_id_str.strip():
        return False, "Task ID cannot be empty", None

    try:
        task_id = int(task_id_str.strip())
        if task_id <= 0:
            return False, "Task ID must be a positive number", None
        return True, None, task_id
    except ValueError:
        return False, "Task ID must be a valid number", None


def validate_user_input_length(
    text: str, max_length: int, field_name: str
) -> Tuple[bool, Optional[str]]:
    """Validate general text input length."""
    if text and len(text) > max_length:
        return False, f"{field_name} must be {max_length} characters or less"
    return True, None


def sanitize_text_input(text: str) -> str:
    """Sanitize text input by removing/replacing problematic characters."""
    if not text:
        return ""

    # Remove or replace problematic characters
    text = text.strip()

    # Remove zero-width characters
    text = re.sub(r"[\u200b-\u200d\ufeff]", "", text)

    # Replace multiple whitespace with single space
    text = re.sub(r"\s+", " ", text)

    # Remove leading/trailing whitespace
    text = text.strip()

    return text


def validate_discord_mention(text: str) -> bool:
    """Check if text contains Discord mentions that might be problematic."""
    # Check for @everyone or @here mentions
    if re.search(r"@(everyone|here)", text, re.IGNORECASE):
        return False

    # Check for excessive mentions
    mention_count = len(re.findall(r"<@[!&]?\d+>", text))
    if mention_count > 5:
        return False

    return True


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """Validate URL format."""
    if not url:
        return False, "URL cannot be empty"

    # Basic URL pattern
    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )

    if not url_pattern.match(url):
        return False, "Invalid URL format"

    # Check for suspicious domains
    suspicious_domains = ["bit.ly", "tinyurl.com", "goo.gl"]
    for domain in suspicious_domains:
        if domain in url.lower():
            return False, f"Shortened URLs from {domain} are not allowed"

    return True, None


def validate_completion_date(
    date_str: str,
) -> Tuple[bool, Optional[str], Optional[datetime]]:
    """Validate completion date format."""
    if not date_str:
        return False, "Date cannot be empty", None

    # Try different date formats
    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
    ]

    for fmt in formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            return True, None, parsed_date
        except ValueError:
            continue

    return False, "Invalid date format. Use YYYY-MM-DD or MM/DD/YYYY", None


def get_validation_summary() -> List[str]:
    """Get a summary of validation rules for user reference."""
    return [
        "**Task Names**: 2-100 characters, no special symbols",
        "**Descriptions**: Up to 500 characters",
        "**Times**: 24-hour format (e.g., 14:30, 07:00)",
        "**Timezones**: Standard format (e.g., America/Toronto)",
        "**Images**: JPEG, PNG, WebP, GIF up to 10MB",
        "**Task IDs**: Positive numbers only",
    ]
