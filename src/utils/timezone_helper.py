"""
Timezone utilities for the Discord Task Reminder Bot.
"""

import pytz
from datetime import datetime, time
from typing import List, Optional


def get_available_timezones() -> List[str]:
    """Get a list of common timezones."""
    common_timezones = [
        "UTC",
        "US/Eastern",
        "US/Central",
        "US/Mountain",
        "US/Pacific",
        "America/New_York",
        "America/Chicago",
        "America/Denver",
        "America/Los_Angeles",
        "America/Toronto",
        "America/Vancouver",
        "Europe/London",
        "Europe/Paris",
        "Europe/Berlin",
        "Europe/Rome",
        "Europe/Madrid",
        "Asia/Tokyo",
        "Asia/Shanghai",
        "Asia/Kolkata",
        "Asia/Dubai",
        "Australia/Sydney",
        "Australia/Melbourne",
    ]
    return sorted(common_timezones)


def validate_timezone(timezone_str: str) -> bool:
    """Validate if a timezone string is valid."""
    try:
        pytz.timezone(timezone_str)
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        return False


def convert_time_to_utc(local_time: time, timezone_str: str) -> time:
    """Convert a local time to UTC."""
    try:
        tz = pytz.timezone(timezone_str)

        # Create a datetime object for today with the given time
        today = datetime.now().date()
        local_dt = datetime.combine(today, local_time)

        # Localize to the given timezone
        local_dt = tz.localize(local_dt)

        # Convert to UTC
        utc_dt = local_dt.astimezone(pytz.UTC)

        return utc_dt.time()
    except Exception:
        # Return original time if conversion fails
        return local_time


def convert_time_from_utc(utc_time: time, timezone_str: str) -> time:
    """Convert a UTC time to local timezone."""
    try:
        tz = pytz.timezone(timezone_str)

        # Create a datetime object for today with the given UTC time
        today = datetime.now().date()
        utc_dt = datetime.combine(today, utc_time)
        utc_dt = pytz.UTC.localize(utc_dt)

        # Convert to local timezone
        local_dt = utc_dt.astimezone(tz)

        return local_dt.time()
    except Exception:
        # Return original time if conversion fails
        return utc_time


def get_timezone_offset(timezone_str: str) -> str:
    """Get the current UTC offset for a timezone."""
    try:
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        offset = now.strftime("%z")

        # Format as +/-HH:MM
        if len(offset) == 5:
            return f"{offset[:3]}:{offset[3:]}"
        return offset
    except Exception:
        return "+00:00"


def format_timezone_display(timezone_str: str) -> str:
    """Format timezone for display with current offset."""
    try:
        offset = get_timezone_offset(timezone_str)
        return f"{timezone_str} (UTC{offset})"
    except Exception:
        return timezone_str


def get_user_local_time(timezone_str: str) -> datetime:
    """Get current local time for a user's timezone."""
    try:
        tz = pytz.timezone(timezone_str)
        return datetime.now(tz)
    except Exception:
        return datetime.now(pytz.UTC)


def is_dst_active(timezone_str: str) -> bool:
    """Check if daylight saving time is currently active."""
    try:
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        return bool(now.dst())
    except Exception:
        return False


def find_timezone_by_name(search_term: str) -> List[str]:
    """Find timezones that match a search term."""
    search_term = search_term.lower()
    matches = []

    for tz_name in pytz.all_timezones:
        if search_term in tz_name.lower():
            matches.append(tz_name)

    # Sort by relevance (exact matches first, then by length)
    matches.sort(key=lambda x: (search_term not in x.lower().split("/")[-1], len(x)))

    return matches[:10]  # Return top 10 matches
