#!/usr/bin/env python3
"""
Test script for progress display functionality in InitialSetup.

This script verifies that:
1. Progress callback displays correctly formatted output
2. Time formatting works for various durations
3. Byte formatting works for various sizes
4. Default progress callback is used when none provided
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from smart_fork.initial_setup import (
    InitialSetup,
    SetupProgress,
    default_progress_callback,
    _format_time,
    _format_bytes
)


def test_format_time():
    """Test time formatting."""
    print("Test 1: Time formatting...")
    assert _format_time(30) == "30s"
    assert _format_time(90) == "1m 30s"
    assert _format_time(3600) == "1h 0m"
    assert _format_time(3661) == "1h 1m"
    print("✓ Time formatting works")


def test_format_bytes():
    """Test byte formatting."""
    print("\nTest 2: Byte formatting...")
    assert _format_bytes(500) == "500.0 B"
    assert _format_bytes(1024) == "1.0 KB"
    assert _format_bytes(1536) == "1.5 KB"
    assert _format_bytes(1048576) == "1.0 MB"
    assert _format_bytes(1073741824) == "1.0 GB"
    print("✓ Byte formatting works")


def test_default_progress_callback():
    """Test default progress callback output."""
    print("\nTest 3: Default progress callback...")

    # Test progress update
    print("  Testing progress update:")
    progress = SetupProgress(
        total_files=100,
        processed_files=50,
        current_file="session_123.jsonl",
        total_chunks=1000,
        elapsed_time=120.0,
        estimated_remaining=120.0
    )
    default_progress_callback(progress)

    # Test completion
    print("\n  Testing completion:")
    progress_complete = SetupProgress(
        total_files=100,
        processed_files=100,
        current_file="",
        total_chunks=2000,
        elapsed_time=300.0,
        estimated_remaining=0.0,
        is_complete=True
    )
    default_progress_callback(progress_complete)

    # Test error
    print("\n  Testing error:")
    progress_error = SetupProgress(
        total_files=100,
        processed_files=50,
        current_file="session_broken.jsonl",
        total_chunks=1000,
        elapsed_time=120.0,
        estimated_remaining=120.0,
        error="Failed to parse session"
    )
    default_progress_callback(progress_error)

    print("\n✓ Default progress callback works")


def test_initial_setup_with_default_callback():
    """Test that InitialSetup uses default callback when none provided."""
    print("\nTest 4: InitialSetup with default callback...")

    # With show_progress=True (default)
    setup1 = InitialSetup()
    assert setup1.progress_callback is not None
    assert setup1.progress_callback == default_progress_callback
    print("✓ Default callback is used when show_progress=True")

    # With show_progress=False
    setup2 = InitialSetup(show_progress=False)
    assert setup2.progress_callback is None
    print("✓ No callback is used when show_progress=False")

    # With custom callback
    def custom_callback(progress):
        pass

    setup3 = InitialSetup(progress_callback=custom_callback)
    assert setup3.progress_callback == custom_callback
    print("✓ Custom callback is used when provided")


def test_progress_sequence():
    """Test a sequence of progress updates."""
    print("\nTest 5: Progress sequence simulation...")

    print("\n  Simulating setup of 10 files:")
    for i in range(10):
        progress = SetupProgress(
            total_files=10,
            processed_files=i,
            current_file=f"session_{i}.jsonl",
            total_chunks=i * 50,
            elapsed_time=i * 2.5,
            estimated_remaining=(10 - i) * 2.5
        )
        default_progress_callback(progress)
        time.sleep(0.1)  # Brief pause for visibility

    # Final completion
    progress_complete = SetupProgress(
        total_files=10,
        processed_files=10,
        current_file="",
        total_chunks=500,
        elapsed_time=25.0,
        estimated_remaining=0.0,
        is_complete=True
    )
    default_progress_callback(progress_complete)

    print("\n✓ Progress sequence works")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Progress Display Tests")
    print("=" * 60)

    tests = [
        test_format_time,
        test_format_bytes,
        test_default_progress_callback,
        test_initial_setup_with_default_callback,
        test_progress_sequence,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n✗ {test_func.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
