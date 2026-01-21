"""
Tests for multi-threaded initial setup.

Tests the parallel processing capability of InitialSetup with multiple worker threads.
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime

from src.smart_fork.initial_setup import InitialSetup


@pytest.fixture
def temp_dirs():
    """Create temporary directories for storage and claude data."""
    storage_dir = tempfile.mkdtemp()
    claude_dir = tempfile.mkdtemp()

    yield storage_dir, claude_dir

    # Cleanup
    shutil.rmtree(storage_dir, ignore_errors=True)
    shutil.rmtree(claude_dir, ignore_errors=True)


@pytest.fixture
def sample_sessions(temp_dirs):
    """Create sample session files for testing."""
    _, claude_dir = temp_dirs
    sessions_dir = Path(claude_dir) / "projects" / "test-project" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    # Create 10 small session files
    session_files = []
    for i in range(10):
        session_file = sessions_dir / f"test-session-{i:03d}.jsonl"

        # Create simple session data
        messages = []
        for j in range(3):  # 3 messages per session
            message = {
                "type": "message",
                "id": f"msg-{j}",
                "role": "user" if j % 2 == 0 else "assistant",
                "content": [{"type": "text", "text": f"Test message {j} in session {i}"}],
                "timestamp": datetime.utcnow().isoformat()
            }
            messages.append(json.dumps(message))

        # Write session file
        with open(session_file, 'w') as f:
            f.write('\n'.join(messages))

        session_files.append(session_file)

    return session_files


def test_single_threaded_indexing(temp_dirs, sample_sessions):
    """Test that single-threaded indexing works (workers=1)."""
    storage_dir, claude_dir = temp_dirs

    setup = InitialSetup(
        storage_dir=storage_dir,
        claude_dir=claude_dir,
        show_progress=False,
        workers=1
    )

    result = setup.run_setup()

    assert result['success'] is True
    assert result['files_processed'] == 10
    assert result['workers_used'] == 1
    assert len(result['errors']) == 0
    assert len(result['timeouts']) == 0
    assert result['total_chunks'] > 0


def test_multi_threaded_indexing_2_workers(temp_dirs, sample_sessions):
    """Test multi-threaded indexing with 2 workers."""
    storage_dir, claude_dir = temp_dirs

    setup = InitialSetup(
        storage_dir=storage_dir,
        claude_dir=claude_dir,
        show_progress=False,
        workers=2
    )

    result = setup.run_setup()

    assert result['success'] is True
    assert result['files_processed'] == 10
    assert result['workers_used'] == 2
    assert len(result['errors']) == 0
    assert len(result['timeouts']) == 0
    assert result['total_chunks'] > 0


def test_multi_threaded_indexing_4_workers(temp_dirs, sample_sessions):
    """Test multi-threaded indexing with 4 workers."""
    storage_dir, claude_dir = temp_dirs

    setup = InitialSetup(
        storage_dir=storage_dir,
        claude_dir=claude_dir,
        show_progress=False,
        workers=4
    )

    result = setup.run_setup()

    assert result['success'] is True
    assert result['files_processed'] == 10
    assert result['workers_used'] == 4
    assert len(result['errors']) == 0
    assert len(result['timeouts']) == 0
    assert result['total_chunks'] > 0


def test_multi_threaded_indexing_produces_same_results(temp_dirs, sample_sessions):
    """Test that multi-threaded indexing produces same results as single-threaded."""
    storage_dir, claude_dir = temp_dirs

    # Run single-threaded
    setup1 = InitialSetup(
        storage_dir=storage_dir,
        claude_dir=claude_dir,
        show_progress=False,
        workers=1
    )
    result1 = setup1.run_setup()

    # Get session registry
    registry_path1 = Path(storage_dir) / "session-registry.json"
    with open(registry_path1) as f:
        registry1 = json.load(f)

    # Clean up for second run
    shutil.rmtree(storage_dir)
    storage_dir2 = tempfile.mkdtemp()

    # Run multi-threaded
    setup2 = InitialSetup(
        storage_dir=storage_dir2,
        claude_dir=claude_dir,
        show_progress=False,
        workers=4
    )
    result2 = setup2.run_setup()

    # Get session registry
    registry_path2 = Path(storage_dir2) / "session-registry.json"
    with open(registry_path2) as f:
        registry2 = json.load(f)

    # Compare results
    assert result1['files_processed'] == result2['files_processed']
    assert result1['total_chunks'] == result2['total_chunks']
    assert len(registry1['sessions']) == len(registry2['sessions'])

    # Compare session IDs (order may differ)
    session_ids1 = set(registry1['sessions'].keys())
    session_ids2 = set(registry2['sessions'].keys())
    assert session_ids1 == session_ids2

    # Cleanup second storage dir
    shutil.rmtree(storage_dir2, ignore_errors=True)


def test_workers_parameter_validation(temp_dirs):
    """Test that workers parameter is validated (minimum 1)."""
    storage_dir, claude_dir = temp_dirs

    # Test with 0 workers (should be clamped to 1)
    setup = InitialSetup(
        storage_dir=storage_dir,
        claude_dir=claude_dir,
        show_progress=False,
        workers=0
    )
    assert setup.workers == 1

    # Test with negative workers (should be clamped to 1)
    setup = InitialSetup(
        storage_dir=storage_dir,
        claude_dir=claude_dir,
        show_progress=False,
        workers=-5
    )
    assert setup.workers == 1


def test_multi_threaded_with_errors(temp_dirs):
    """Test multi-threaded indexing handles errors gracefully."""
    storage_dir, claude_dir = temp_dirs
    sessions_dir = Path(claude_dir) / "projects" / "test-project" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    # Create valid session
    valid_session = sessions_dir / "valid-session.jsonl"
    messages = []
    for j in range(3):
        message = {
            "type": "message",
            "id": f"msg-{j}",
            "role": "user" if j % 2 == 0 else "assistant",
            "content": [{"type": "text", "text": f"Valid message {j}"}],
            "timestamp": datetime.utcnow().isoformat()
        }
        messages.append(json.dumps(message))
    with open(valid_session, 'w') as f:
        f.write('\n'.join(messages))

    # Create invalid session (corrupt JSON)
    invalid_session = sessions_dir / "invalid-session.jsonl"
    with open(invalid_session, 'w') as f:
        f.write("{ invalid json }")

    # Create empty session
    empty_session = sessions_dir / "empty-session.jsonl"
    with open(empty_session, 'w') as f:
        f.write("")

    setup = InitialSetup(
        storage_dir=storage_dir,
        claude_dir=claude_dir,
        show_progress=False,
        workers=2
    )

    result = setup.run_setup()

    # Should process valid session and handle errors
    assert result['success'] is True  # Overall success
    # Note: empty-session.jsonl is <100 bytes so it's skipped by _find_session_files
    # invalid-session.jsonl should generate an error
    assert result['files_processed'] >= 1  # At least the valid one


def test_multi_threaded_with_resume(temp_dirs, sample_sessions):
    """Test multi-threaded indexing can be interrupted and resumed."""
    storage_dir, claude_dir = temp_dirs

    # Start initial setup with interruption
    setup1 = InitialSetup(
        storage_dir=storage_dir,
        claude_dir=claude_dir,
        show_progress=False,
        workers=2
    )

    # Simulate interruption after processing a few files
    # We can't easily interrupt in the test, so we'll just verify resume works
    result1 = setup1.run_setup()

    # Verify setup completed
    assert result1['success'] is True
    assert result1['files_processed'] == 10

    # Try to resume (should detect no incomplete setup)
    setup2 = InitialSetup(
        storage_dir=storage_dir,
        claude_dir=claude_dir,
        show_progress=False,
        workers=2
    )

    # Resume should work (but find nothing to do since we completed)
    result2 = setup2.run_setup(resume=True)
    assert result2['success'] is True


def test_thread_safety_state_updates(temp_dirs, sample_sessions):
    """Test that state updates are thread-safe in multi-threaded mode."""
    storage_dir, claude_dir = temp_dirs

    setup = InitialSetup(
        storage_dir=storage_dir,
        claude_dir=claude_dir,
        show_progress=False,
        workers=4
    )

    result = setup.run_setup()

    # All files should be processed exactly once
    assert result['files_processed'] == 10

    # Load the final state to verify consistency
    registry_path = Path(storage_dir) / "session-registry.json"
    with open(registry_path) as f:
        registry = json.load(f)

    # Should have exactly 10 sessions registered
    assert len(registry['sessions']) == 10

    # Each session should have valid metadata
    for session_id, metadata in registry['sessions'].items():
        assert metadata['session_id'] == session_id
        assert metadata['chunk_count'] > 0
        assert metadata['message_count'] > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
