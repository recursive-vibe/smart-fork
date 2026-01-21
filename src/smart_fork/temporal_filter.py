"""
Temporal filtering utilities for Smart Fork Detection.

This module provides utilities for parsing natural language date/time expressions
and filtering sessions based on temporal ranges.
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
from enum import Enum


class TimeRange(Enum):
    """Predefined time ranges."""
    TODAY = "today"
    YESTERDAY = "yesterday"
    THIS_WEEK = "this_week"
    LAST_WEEK = "last_week"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    THIS_YEAR = "this_year"
    CUSTOM = "custom"


class TemporalFilter:
    """
    Utility for parsing and applying temporal filters.

    Supports:
    - Predefined ranges: today, yesterday, this_week, last_week, etc.
    - Natural language: "last Tuesday", "2 weeks ago", "3 days ago"
    - Relative time: "1h", "2d", "3w", "4m"
    - ISO format: "2026-01-01", "2026-01-01T10:00:00"
    """

    # Natural language patterns
    RELATIVE_PATTERNS = {
        r'(\d+)\s*hours?\s*ago': lambda m: timedelta(hours=int(m.group(1))),
        r'(\d+)\s*days?\s*ago': lambda m: timedelta(days=int(m.group(1))),
        r'(\d+)\s*weeks?\s*ago': lambda m: timedelta(weeks=int(m.group(1))),
        r'(\d+)\s*months?\s*ago': lambda m: timedelta(days=int(m.group(1)) * 30),
        r'(\d+)h': lambda m: timedelta(hours=int(m.group(1))),
        r'(\d+)d': lambda m: timedelta(days=int(m.group(1))),
        r'(\d+)w': lambda m: timedelta(weeks=int(m.group(1))),
        r'(\d+)m': lambda m: timedelta(days=int(m.group(1)) * 30),
    }

    WEEKDAY_PATTERNS = {
        'monday': 0, 'mon': 0,
        'tuesday': 1, 'tue': 1, 'tues': 1,
        'wednesday': 2, 'wed': 2,
        'thursday': 3, 'thu': 3, 'thur': 3, 'thurs': 3,
        'friday': 4, 'fri': 4,
        'saturday': 5, 'sat': 5,
        'sunday': 6, 'sun': 6,
    }

    @staticmethod
    def parse_time_range(
        time_range: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[Tuple[datetime, datetime]]:
        """
        Parse a time range specification into start and end datetime objects.

        Args:
            time_range: Predefined range (today, this_week, etc.) or natural language
            start_date: Custom start date (ISO format or natural language)
            end_date: Custom end date (ISO format or natural language)

        Returns:
            Tuple of (start_datetime, end_datetime) or None if invalid
        """
        now = datetime.now()

        # Custom date range
        if start_date or end_date:
            start = TemporalFilter._parse_date(start_date) if start_date else datetime.min
            end = TemporalFilter._parse_date(end_date) if end_date else now
            if start and end:
                return (start, end)
            return None

        # Predefined ranges
        if not time_range:
            return None

        time_range_lower = time_range.lower().strip()

        # Today
        if time_range_lower == 'today':
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return (start, now)

        # Yesterday
        if time_range_lower == 'yesterday':
            yesterday = now - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1) - timedelta(microseconds=1)
            return (start, end)

        # This week (Monday to now)
        if time_range_lower in ('this_week', 'this week'):
            days_since_monday = now.weekday()
            monday = now - timedelta(days=days_since_monday)
            start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
            return (start, now)

        # Last week (previous Monday to Sunday)
        if time_range_lower in ('last_week', 'last week'):
            days_since_monday = now.weekday()
            this_monday = now - timedelta(days=days_since_monday)
            last_monday = this_monday - timedelta(weeks=1)
            last_monday_start = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
            last_sunday_end = last_monday_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
            return (last_monday_start, last_sunday_end)

        # This month
        if time_range_lower in ('this_month', 'this month'):
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return (start, now)

        # Last month
        if time_range_lower in ('last_month', 'last month'):
            first_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_day_prev_month = first_this_month - timedelta(days=1)
            first_prev_month = last_day_prev_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_prev_month = first_this_month - timedelta(microseconds=1)
            return (first_prev_month, end_prev_month)

        # This year
        if time_range_lower in ('this_year', 'this year'):
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            return (start, now)

        # Try parsing as natural language relative time
        parsed = TemporalFilter._parse_relative_time(time_range_lower)
        if parsed:
            return (parsed, now)

        # Try parsing as "last <weekday>"
        weekday_match = re.match(r'last\s+(\w+)', time_range_lower)
        if weekday_match:
            weekday_name = weekday_match.group(1).lower()
            if weekday_name in TemporalFilter.WEEKDAY_PATTERNS:
                target_weekday = TemporalFilter.WEEKDAY_PATTERNS[weekday_name]
                current_weekday = now.weekday()

                # Calculate days to go back
                days_back = (current_weekday - target_weekday) % 7
                if days_back == 0:
                    days_back = 7  # If today is the target weekday, go back a full week

                target_date = now - timedelta(days=days_back)
                start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end = start + timedelta(days=1) - timedelta(microseconds=1)
                return (start, end)

        # Try parsing as ISO date
        parsed_date = TemporalFilter._parse_date(time_range)
        if parsed_date:
            # Single date - return that day
            start = parsed_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1) - timedelta(microseconds=1)
            return (start, end)

        return None

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        """
        Parse a date string in ISO format or natural language.

        Args:
            date_str: Date string to parse

        Returns:
            datetime object or None if invalid
        """
        if not date_str:
            return None

        date_str = date_str.strip()

        # Try ISO format first
        for fmt in ('%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f'):
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Try relative time
        return TemporalFilter._parse_relative_time(date_str)

    @staticmethod
    def _parse_relative_time(time_str: str) -> Optional[datetime]:
        """
        Parse relative time expressions like "2 weeks ago", "3d".

        Args:
            time_str: Relative time string

        Returns:
            datetime object or None if invalid
        """
        if not time_str:
            return None

        time_str = time_str.lower().strip()
        now = datetime.now()

        for pattern, delta_func in TemporalFilter.RELATIVE_PATTERNS.items():
            match = re.match(pattern, time_str)
            if match:
                delta = delta_func(match)
                return now - delta

        return None

    @staticmethod
    def filter_by_timestamp(
        timestamp_str: Optional[str],
        start: datetime,
        end: datetime
    ) -> bool:
        """
        Check if a timestamp falls within the given range.

        Args:
            timestamp_str: ISO format timestamp string
            start: Start of time range
            end: End of time range

        Returns:
            True if timestamp is within range, False otherwise
        """
        if not timestamp_str:
            return False

        try:
            # Parse ISO timestamp
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            # Remove timezone info for comparison (assume all times are local)
            timestamp = timestamp.replace(tzinfo=None)
            return start <= timestamp <= end
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def calculate_recency_boost(
        timestamp_str: Optional[str],
        max_boost: float = 0.2,
        decay_days: int = 30
    ) -> float:
        """
        Calculate a recency boost score based on how recent a timestamp is.

        Args:
            timestamp_str: ISO format timestamp string
            max_boost: Maximum boost value for very recent items (default 0.2)
            decay_days: Number of days for boost to decay to zero (default 30)

        Returns:
            Boost value between 0.0 and max_boost
        """
        if not timestamp_str:
            return 0.0

        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            timestamp = timestamp.replace(tzinfo=None)
            now = datetime.now()

            # Calculate days since timestamp
            days_ago = (now - timestamp).total_seconds() / 86400

            if days_ago < 0:
                # Future timestamp, no boost
                return 0.0

            if days_ago >= decay_days:
                # Too old, no boost
                return 0.0

            # Linear decay from max_boost to 0
            boost = max_boost * (1 - days_ago / decay_days)
            return max(0.0, boost)

        except (ValueError, AttributeError):
            return 0.0
