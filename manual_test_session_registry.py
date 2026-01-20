#!/usr/bin/env python3
"""
Manual test script for SessionRegistry.

This script tests the SessionRegistry functionality without requiring pytest.
"""

import os
import sys
import tempfile
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from smart_fork.session_registry import SessionRegistry, SessionMetadata


def test_session_metadata():
    """Test SessionMetadata dataclass."""
    print("\n=== Testing SessionMetadata ===")

    # Test creation with defaults
    metadata = SessionMetadata(session_id="test-123")
    assert metadata.session_id == "test-123"
    assert metadata.project is None
    assert metadata.chunk_count == 0
    assert metadata.tags == []
    print("✓ Creation with defaults")

    # Test creation with values
    metadata = SessionMetadata(
        session_id="test-456",
        project="my-project",
        chunk_count=42,
        message_count=100,
        tags=["important", "bugfix"]
    )
    assert metadata.session_id == "test-456"
    assert metadata.project == "my-project"
    assert metadata.chunk_count == 42
    print("✓ Creation with values")

    # Test to_dict
    data = metadata.to_dict()
    assert data["session_id"] == "test-456"
    assert data["project"] == "my-project"
    assert data["chunk_count"] == 42
    print("✓ to_dict conversion")

    # Test from_dict
    metadata2 = SessionMetadata.from_dict(data)
    assert metadata2.session_id == "test-456"
    assert metadata2.project == "my-project"
    print("✓ from_dict conversion")


def test_basic_operations():
    """Test basic CRUD operations."""
    print("\n=== Testing Basic CRUD Operations ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = os.path.join(tmpdir, "test-registry.json")
        registry = SessionRegistry(registry_path=registry_path)

        # Test add_session
        metadata = registry.add_session("session-001")
        assert metadata.session_id == "session-001"
        print("✓ Add session with default metadata")

        # Test add_session with custom metadata
        custom = SessionMetadata(
            session_id="ignored",
            project="test-project",
            chunk_count=10
        )
        metadata = registry.add_session("session-002", custom)
        assert metadata.session_id == "session-002"
        assert metadata.project == "test-project"
        print("✓ Add session with custom metadata")

        # Test get_session
        metadata = registry.get_session("session-001")
        assert metadata is not None
        assert metadata.session_id == "session-001"
        print("✓ Get existing session")

        # Test get non-existent session
        metadata = registry.get_session("nonexistent")
        assert metadata is None
        print("✓ Get non-existent session returns None")

        # Test update_session
        updated = registry.update_session("session-001", project="updated", chunk_count=50)
        assert updated.project == "updated"
        assert updated.chunk_count == 50
        print("✓ Update existing session")

        # Test update non-existent session
        result = registry.update_session("nonexistent", project="test")
        assert result is None
        print("✓ Update non-existent session returns None")

        # Test delete_session
        result = registry.delete_session("session-001")
        assert result is True
        assert registry.get_session("session-001") is None
        print("✓ Delete existing session")

        # Test delete non-existent session
        result = registry.delete_session("nonexistent")
        assert result is False
        print("✓ Delete non-existent session returns False")


def test_listing_and_filtering():
    """Test listing and filtering sessions."""
    print("\n=== Testing Listing and Filtering ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = os.path.join(tmpdir, "test-registry.json")
        registry = SessionRegistry(registry_path=registry_path)

        # Add test sessions
        registry.add_session("session-001", SessionMetadata(
            session_id="session-001",
            project="project-a",
            tags=["urgent", "bugfix"]
        ))
        registry.add_session("session-002", SessionMetadata(
            session_id="session-002",
            project="project-b",
            tags=["feature"]
        ))
        registry.add_session("session-003", SessionMetadata(
            session_id="session-003",
            project="project-a",
            tags=["urgent", "feature"]
        ))

        # Test list all sessions
        sessions = registry.list_sessions()
        assert len(sessions) == 3
        print("✓ List all sessions")

        # Test filter by project
        sessions = registry.list_sessions(project="project-a")
        assert len(sessions) == 2
        for s in sessions:
            assert s.project == "project-a"
        print("✓ Filter sessions by project")

        # Test filter by tags
        sessions = registry.list_sessions(tags=["urgent"])
        assert len(sessions) == 2
        session_ids = {s.session_id for s in sessions}
        assert "session-001" in session_ids
        assert "session-003" in session_ids
        print("✓ Filter sessions by tags")

        # Test get_all_sessions
        all_sessions = registry.get_all_sessions()
        assert isinstance(all_sessions, dict)
        assert len(all_sessions) == 3
        print("✓ Get all sessions as dictionary")


def test_last_synced():
    """Test last_synced timestamp tracking."""
    print("\n=== Testing Last Synced Tracking ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = os.path.join(tmpdir, "test-registry.json")
        registry = SessionRegistry(registry_path=registry_path)

        registry.add_session("session-001")

        # Test with custom timestamp
        timestamp = "2026-01-20T15:30:00"
        result = registry.set_last_synced("session-001", timestamp)
        assert result is True
        metadata = registry.get_session("session-001")
        assert metadata.last_synced == timestamp
        print("✓ Set last_synced with custom timestamp")

        # Test with auto timestamp
        registry.add_session("session-002")
        result = registry.set_last_synced("session-002")
        assert result is True
        metadata = registry.get_session("session-002")
        assert metadata.last_synced is not None
        # Verify it's a valid ISO timestamp
        datetime.fromisoformat(metadata.last_synced)
        print("✓ Set last_synced with auto timestamp")

        # Test non-existent session
        result = registry.set_last_synced("nonexistent")
        assert result is False
        print("✓ Set last_synced on non-existent session returns False")


def test_statistics():
    """Test registry statistics."""
    print("\n=== Testing Statistics ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = os.path.join(tmpdir, "test-registry.json")
        registry = SessionRegistry(registry_path=registry_path)

        # Test empty stats
        stats = registry.get_stats()
        assert stats['total_sessions'] == 0
        assert stats['total_chunks'] == 0
        assert stats['total_messages'] == 0
        assert stats['total_projects'] == 0
        print("✓ Get stats from empty registry")

        # Add sessions with data
        registry.add_session("session-001", SessionMetadata(
            session_id="session-001",
            project="project-a",
            chunk_count=10,
            message_count=50
        ))
        registry.add_session("session-002", SessionMetadata(
            session_id="session-002",
            project="project-b",
            chunk_count=20,
            message_count=100
        ))
        registry.add_session("session-003", SessionMetadata(
            session_id="session-003",
            project="project-a",
            chunk_count=5,
            message_count=25
        ))

        # Test stats with data
        stats = registry.get_stats()
        assert stats['total_sessions'] == 3
        assert stats['total_chunks'] == 35
        assert stats['total_messages'] == 175
        assert stats['total_projects'] == 2
        assert set(stats['projects']) == {"project-a", "project-b"}
        print("✓ Get stats with data")


def test_persistence():
    """Test persistence to disk."""
    print("\n=== Testing Persistence ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = os.path.join(tmpdir, "test-registry.json")

        # Create registry and add session
        registry1 = SessionRegistry(registry_path=registry_path)
        registry1.add_session("session-001", SessionMetadata(
            session_id="session-001",
            project="persistent-project",
            chunk_count=99
        ))

        # Verify file exists
        assert os.path.exists(registry_path)
        print("✓ Registry file created")

        # Create new instance and verify data persists
        registry2 = SessionRegistry(registry_path=registry_path)
        metadata = registry2.get_session("session-001")
        assert metadata is not None
        assert metadata.project == "persistent-project"
        assert metadata.chunk_count == 99
        print("✓ Data persists across instances")

        # Update and verify persistence
        registry2.update_session("session-001", chunk_count=42)
        registry3 = SessionRegistry(registry_path=registry_path)
        metadata = registry3.get_session("session-001")
        assert metadata.chunk_count == 42
        print("✓ Updates persist to disk")


def test_clear():
    """Test clearing the registry."""
    print("\n=== Testing Clear ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = os.path.join(tmpdir, "test-registry.json")
        registry = SessionRegistry(registry_path=registry_path)

        registry.add_session("session-001")
        registry.add_session("session-002")
        assert len(registry.get_all_sessions()) == 2

        registry.clear()
        assert len(registry.get_all_sessions()) == 0
        print("✓ Clear removes all sessions")


def test_corrupted_file():
    """Test handling of corrupted registry file."""
    print("\n=== Testing Corrupted File Handling ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = os.path.join(tmpdir, "test-registry.json")

        # Create corrupted file
        os.makedirs(os.path.dirname(registry_path), exist_ok=True)
        with open(registry_path, 'w') as f:
            f.write("{ invalid json }")

        # Should start fresh without crashing
        registry = SessionRegistry(registry_path=registry_path)
        assert len(registry.get_all_sessions()) == 0
        print("✓ Handles corrupted file gracefully")


def main():
    """Run all tests."""
    print("=" * 70)
    print("SessionRegistry Manual Test Suite")
    print("=" * 70)

    try:
        test_session_metadata()
        test_basic_operations()
        test_listing_and_filtering()
        test_last_synced()
        test_statistics()
        test_persistence()
        test_clear()
        test_corrupted_file()

        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED")
        print("=" * 70)
        return 0

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
