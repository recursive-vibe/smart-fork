"""Tests for the temporal_filter module."""

import pytest
from datetime import datetime, timedelta
from smart_fork.temporal_filter import TemporalFilter, TimeRange


class TestTimeRangeParsing:
    """Test parsing of time range expressions."""

    def test_parse_today(self):
        """Test parsing 'today' time range."""
        start, end = TemporalFilter.parse_time_range("today")

        now = datetime.now()
        expected_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        assert start.date() == expected_start.date()
        assert start.hour == 0
        assert start.minute == 0
        assert end.date() == now.date()

    def test_parse_yesterday(self):
        """Test parsing 'yesterday' time range."""
        start, end = TemporalFilter.parse_time_range("yesterday")

        now = datetime.now()
        yesterday = now - timedelta(days=1)

        assert start.date() == yesterday.date()
        assert start.hour == 0
        assert end.date() == yesterday.date()

    def test_parse_this_week(self):
        """Test parsing 'this_week' time range."""
        start, end = TemporalFilter.parse_time_range("this_week")

        now = datetime.now()
        days_since_monday = now.weekday()
        monday = now - timedelta(days=days_since_monday)

        assert start.date() == monday.date()
        assert start.hour == 0
        assert end.date() == now.date()

    def test_parse_last_week(self):
        """Test parsing 'last_week' time range."""
        start, end = TemporalFilter.parse_time_range("last_week")

        now = datetime.now()
        days_since_monday = now.weekday()
        this_monday = now - timedelta(days=days_since_monday)
        last_monday = this_monday - timedelta(weeks=1)

        # Check start is last Monday at midnight
        assert start.date() == last_monday.date()
        assert start.hour == 0

        # Check end is last Sunday (6 days after last Monday) at end of day
        expected_sunday = last_monday.date() + timedelta(days=6)
        assert end.date() == expected_sunday
        assert end.hour == 23
        assert end.minute == 59

    def test_parse_this_month(self):
        """Test parsing 'this_month' time range."""
        start, end = TemporalFilter.parse_time_range("this_month")

        now = datetime.now()

        assert start.date() == now.replace(day=1).date()
        assert start.hour == 0
        assert end.date() == now.date()

    def test_parse_last_month(self):
        """Test parsing 'last_month' time range."""
        start, end = TemporalFilter.parse_time_range("last_month")

        now = datetime.now()
        first_this_month = now.replace(day=1)

        assert start.month == (first_this_month - timedelta(days=1)).month
        assert start.day == 1
        assert end.month == (first_this_month - timedelta(days=1)).month

    def test_parse_this_year(self):
        """Test parsing 'this_year' time range."""
        start, end = TemporalFilter.parse_time_range("this_year")

        now = datetime.now()

        assert start.date() == now.replace(month=1, day=1).date()
        assert start.hour == 0
        assert end.date() == now.date()


class TestRelativeTimeParsing:
    """Test parsing of relative time expressions."""

    def test_parse_hours_ago(self):
        """Test parsing '2 hours ago'."""
        start, end = TemporalFilter.parse_time_range("2 hours ago")

        now = datetime.now()
        expected = now - timedelta(hours=2)

        # Allow 1 second tolerance for test execution time
        assert abs((start - expected).total_seconds()) < 1
        assert abs((end - now).total_seconds()) < 1

    def test_parse_days_ago(self):
        """Test parsing '5 days ago'."""
        start, end = TemporalFilter.parse_time_range("5 days ago")

        now = datetime.now()
        expected = now - timedelta(days=5)

        assert abs((start - expected).total_seconds()) < 1
        assert abs((end - now).total_seconds()) < 1

    def test_parse_weeks_ago(self):
        """Test parsing '2 weeks ago'."""
        start, end = TemporalFilter.parse_time_range("2 weeks ago")

        now = datetime.now()
        expected = now - timedelta(weeks=2)

        assert abs((start - expected).total_seconds()) < 1
        assert abs((end - now).total_seconds()) < 1

    def test_parse_months_ago(self):
        """Test parsing '3 months ago'."""
        start, end = TemporalFilter.parse_time_range("3 months ago")

        now = datetime.now()
        expected = now - timedelta(days=90)  # 3 * 30 days

        assert abs((start - expected).total_seconds()) < 1
        assert abs((end - now).total_seconds()) < 1

    def test_parse_short_format(self):
        """Test parsing short format like '2d', '3w'."""
        # 2 days
        start, end = TemporalFilter.parse_time_range("2d")
        now = datetime.now()
        expected = now - timedelta(days=2)
        assert abs((start - expected).total_seconds()) < 1

        # 1 week
        start, end = TemporalFilter.parse_time_range("1w")
        expected = now - timedelta(weeks=1)
        assert abs((start - expected).total_seconds()) < 1


class TestWeekdayParsing:
    """Test parsing of weekday expressions."""

    def test_parse_last_monday(self):
        """Test parsing 'last monday'."""
        start, end = TemporalFilter.parse_time_range("last monday")

        assert start is not None
        assert end is not None
        assert start.weekday() == 0  # Monday
        assert start.hour == 0
        assert start.minute == 0

    def test_parse_last_friday(self):
        """Test parsing 'last friday'."""
        start, end = TemporalFilter.parse_time_range("last friday")

        assert start is not None
        assert end is not None
        assert start.weekday() == 4  # Friday
        assert start.hour == 0

    def test_parse_last_tuesday_variations(self):
        """Test different spellings of Tuesday."""
        for variant in ["last tuesday", "last tue", "last tues"]:
            start, end = TemporalFilter.parse_time_range(variant)
            assert start is not None
            assert start.weekday() == 1  # Tuesday


class TestCustomDateRangeParsing:
    """Test parsing of custom date ranges."""

    def test_parse_iso_date(self):
        """Test parsing ISO format date."""
        start, end = TemporalFilter.parse_time_range("2026-01-15")

        assert start.date() == datetime(2026, 1, 15).date()
        assert start.hour == 0
        assert end.date() == datetime(2026, 1, 15).date()
        assert end.hour == 23

    def test_parse_iso_datetime(self):
        """Test parsing ISO format datetime."""
        start, end = TemporalFilter.parse_time_range("2026-01-15T10:30:00")

        # When given a single datetime, it returns the day starting at midnight
        assert start.date() == datetime(2026, 1, 15).date()
        assert start.hour == 0

    def test_parse_custom_range(self):
        """Test parsing custom start and end dates."""
        start, end = TemporalFilter.parse_time_range(
            start_date="2026-01-01",
            end_date="2026-01-15"
        )

        assert start == datetime(2026, 1, 1, 0, 0, 0)
        assert end == datetime(2026, 1, 15, 0, 0, 0)

    def test_parse_custom_range_with_natural_language(self):
        """Test custom range with natural language dates."""
        start, end = TemporalFilter.parse_time_range(
            start_date="7 days ago"
        )

        now = datetime.now()
        expected_start = now - timedelta(days=7)

        assert abs((start - expected_start).total_seconds()) < 1
        assert abs((end - now).total_seconds()) < 1


class TestTimestampFiltering:
    """Test filtering by timestamp."""

    def test_filter_within_range(self):
        """Test timestamp within range."""
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 31)

        timestamp = "2026-01-15T12:00:00"

        assert TemporalFilter.filter_by_timestamp(timestamp, start, end) is True

    def test_filter_before_range(self):
        """Test timestamp before range."""
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 31)

        timestamp = "2025-12-15T12:00:00"

        assert TemporalFilter.filter_by_timestamp(timestamp, start, end) is False

    def test_filter_after_range(self):
        """Test timestamp after range."""
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 31)

        timestamp = "2026-02-15T12:00:00"

        assert TemporalFilter.filter_by_timestamp(timestamp, start, end) is False

    def test_filter_exact_boundaries(self):
        """Test timestamp at exact boundaries."""
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 31)

        # Exact start
        assert TemporalFilter.filter_by_timestamp("2026-01-01T00:00:00", start, end) is True

        # Exact end
        assert TemporalFilter.filter_by_timestamp("2026-01-31T00:00:00", start, end) is True

    def test_filter_none_timestamp(self):
        """Test filtering with None timestamp."""
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 31)

        assert TemporalFilter.filter_by_timestamp(None, start, end) is False

    def test_filter_invalid_timestamp(self):
        """Test filtering with invalid timestamp."""
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 31)

        assert TemporalFilter.filter_by_timestamp("invalid", start, end) is False


class TestRecencyBoost:
    """Test recency boost calculation."""

    def test_recency_boost_very_recent(self):
        """Test boost for very recent timestamp (today)."""
        now = datetime.now()
        timestamp = now.isoformat()

        boost = TemporalFilter.calculate_recency_boost(timestamp, max_boost=0.2, decay_days=30)

        # Should be close to max boost
        assert boost > 0.19
        assert boost <= 0.2

    def test_recency_boost_one_week_ago(self):
        """Test boost for timestamp one week ago."""
        one_week_ago = datetime.now() - timedelta(days=7)
        timestamp = one_week_ago.isoformat()

        boost = TemporalFilter.calculate_recency_boost(timestamp, max_boost=0.2, decay_days=30)

        # Should be around 0.2 * (1 - 7/30) ≈ 0.153
        assert 0.14 < boost < 0.16

    def test_recency_boost_halfway(self):
        """Test boost at halfway point (15 days for 30-day decay)."""
        fifteen_days_ago = datetime.now() - timedelta(days=15)
        timestamp = fifteen_days_ago.isoformat()

        boost = TemporalFilter.calculate_recency_boost(timestamp, max_boost=0.2, decay_days=30)

        # Should be around 0.1 (half of max)
        assert 0.09 < boost < 0.11

    def test_recency_boost_old(self):
        """Test boost for old timestamp (beyond decay period)."""
        old = datetime.now() - timedelta(days=60)
        timestamp = old.isoformat()

        boost = TemporalFilter.calculate_recency_boost(timestamp, max_boost=0.2, decay_days=30)

        # Should be 0 (beyond decay period)
        assert boost == 0.0

    def test_recency_boost_exact_boundary(self):
        """Test boost at exact decay boundary."""
        boundary = datetime.now() - timedelta(days=30)
        timestamp = boundary.isoformat()

        boost = TemporalFilter.calculate_recency_boost(timestamp, max_boost=0.2, decay_days=30)

        # Should be very close to 0
        assert boost < 0.01

    def test_recency_boost_none_timestamp(self):
        """Test boost with None timestamp."""
        boost = TemporalFilter.calculate_recency_boost(None)
        assert boost == 0.0

    def test_recency_boost_invalid_timestamp(self):
        """Test boost with invalid timestamp."""
        boost = TemporalFilter.calculate_recency_boost("invalid")
        assert boost == 0.0

    def test_recency_boost_future_timestamp(self):
        """Test boost with future timestamp."""
        future = datetime.now() + timedelta(days=1)
        timestamp = future.isoformat()

        boost = TemporalFilter.calculate_recency_boost(timestamp)

        # Future timestamps should get no boost
        assert boost == 0.0

    def test_recency_boost_custom_params(self):
        """Test boost with custom max_boost and decay_days."""
        one_day_ago = datetime.now() - timedelta(days=1)
        timestamp = one_day_ago.isoformat()

        # High boost, short decay
        boost = TemporalFilter.calculate_recency_boost(
            timestamp,
            max_boost=0.5,
            decay_days=10
        )

        # Should be 0.5 * (1 - 1/10) = 0.45
        assert 0.44 < boost < 0.46


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_parse_none_time_range(self):
        """Test parsing with None parameters."""
        result = TemporalFilter.parse_time_range(None, None, None)
        assert result is None

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        result = TemporalFilter.parse_time_range("")
        assert result is None

    def test_parse_invalid_range(self):
        """Test parsing invalid time range."""
        result = TemporalFilter.parse_time_range("invalid_range")
        assert result is None

    def test_parse_malformed_date(self):
        """Test parsing malformed date."""
        result = TemporalFilter.parse_time_range("2026-13-45")  # Invalid month/day
        assert result is None

    def test_case_insensitivity(self):
        """Test that parsing is case-insensitive."""
        # All should parse successfully
        for variant in ["TODAY", "Today", "today", "ToDay"]:
            result = TemporalFilter.parse_time_range(variant)
            assert result is not None

        for variant in ["THIS_WEEK", "this_week", "This_Week"]:
            result = TemporalFilter.parse_time_range(variant)
            assert result is not None

    def test_whitespace_handling(self):
        """Test handling of extra whitespace."""
        result = TemporalFilter.parse_time_range("  today  ")
        assert result is not None

        result = TemporalFilter.parse_time_range("  2 weeks ago  ")
        assert result is not None
