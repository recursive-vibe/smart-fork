"""
Unit tests for multi-threaded initial setup (without full model loading).

Tests the multi-threading logic without the overhead of loading embedding models.
"""

import pytest
from src.smart_fork.initial_setup import InitialSetup


def test_workers_parameter_initialization():
    """Test that workers parameter is properly initialized."""
    # Default: 1 worker
    setup = InitialSetup(workers=1, show_progress=False)
    assert setup.workers == 1

    # Multiple workers
    setup = InitialSetup(workers=4, show_progress=False)
    assert setup.workers == 4

    # Zero workers should be clamped to 1
    setup = InitialSetup(workers=0, show_progress=False)
    assert setup.workers == 1

    # Negative workers should be clamped to 1
    setup = InitialSetup(workers=-5, show_progress=False)
    assert setup.workers == 1


def test_locks_initialized():
    """Test that thread safety locks are initialized."""
    setup = InitialSetup(workers=4, show_progress=False)

    # Check that locks exist
    assert hasattr(setup, '_progress_lock')
    assert hasattr(setup, '_state_lock')
    assert setup._progress_lock is not None
    assert setup._state_lock is not None


def test_process_files_sequential_exists():
    """Test that sequential processing method exists."""
    setup = InitialSetup(workers=1, show_progress=False)
    assert hasattr(setup, '_process_files_sequential')
    assert callable(getattr(setup, '_process_files_sequential'))


def test_process_files_parallel_exists():
    """Test that parallel processing method exists."""
    setup = InitialSetup(workers=4, show_progress=False)
    assert hasattr(setup, '_process_files_parallel')
    assert callable(getattr(setup, '_process_files_parallel'))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
