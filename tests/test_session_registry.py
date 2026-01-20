"""
Unit tests for SessionRegistry class.
"""

import os
import json
import tempfile
import pytest
from datetime import datetime
from smart_fork.session_registry import SessionRegistry, SessionMetadata


class TestSessionMetadata:
    """Test SessionMetadata dataclass."""

    def test_creation_with_defaults(self):
        """Test creating SessionMetadata with default values."""
        metadata = SessionMetadata(session_id="test-123")
        assert metadata.session_id == "test-123"
        assert metadata.project is None
        assert metadata.created_at is None
        assert metadata.last_modified is None
        assert metadata.last_synced is None
        assert metadata.chunk_count == 0
        assert metadata.message_count == 0
        assert metadata.tags == []

    def test_creation_with_values(self):
        """Test creating SessionMetadata with all values."""
        metadata = SessionMetadata(
            session_id="test-456",
            project="my-project",
            created_at="2026-01-20T10:00:00",
            last_modified="2026-01-20T11:00:00",
            last_synced="2026-01-20T12:00:00",
            chunk_count=42,
            message_count=100,
            tags=["important", "bugfix"]
        )
        assert metadata.session_id == "test-456"
        assert metadata.project == "my-project"
        assert metadata.created_at == "2026-01-20T10:00:00"
        assert metadata.chunk_count == 42
        assert metadata.message_count == 100
        assert metadata.tags == ["important", "bugfix"]

    def test_to_dict(self):
        """Test converting SessionMetadata to dictionary."""
        metadata = SessionMetadata(
            session_id="test-789",
            project="test-project",
            chunk_count=10
        )
        data = metadata.to_dict()
        assert data["session_id"] == "test-789"
        assert data["project"] == "test-project"
        assert data["chunk_count"] == 10
        assert data["tags"] == []

    def test_from_dict(self):
        """Test creating SessionMetadata from dictionary."""
        data = {
            "session_id": "test-abc",
            "project": "from-dict",
            "chunk_count": 5,
            "message_count": 20,
            "tags": ["test"]
        }
        metadata = SessionMetadata.from_dict(data)
        assert metadata.session_id == "test-abc"
        assert metadata.project == "from-dict"
        assert metadata.chunk_count == 5
        assert metadata.message_count == 20
        assert metadata.tags == ["test"]


class TestSessionRegistry:
    """Test SessionRegistry class."""

    @pytest.fixture
    def temp_registry_path(self):
        """Create a temporary path for registry testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = os.path.join(tmpdir, "session-registry.json")
            yield registry_path

    @pytest.fixture
    def registry(self, temp_registry_path):
        """Create a SessionRegistry instance for testing."""
        return SessionRegistry(registry_path=temp_registry_path)

    def test_initialization(self, temp_registry_path):
        """Test SessionRegistry initialization."""
        registry = SessionRegistry(registry_path=temp_registry_path)
        assert registry.registry_path == temp_registry_path
        assert os.path.exists(os.path.dirname(temp_registry_path))

    def test_add_session_default_metadata(self, registry):
        """Test adding session with default metadata."""
        metadata = registry.add_session("session-001")
        assert metadata.session_id == "session-001"
        assert metadata.chunk_count == 0
        assert metadata.tags == []

    def test_add_session_custom_metadata(self, registry):
        """Test adding session with custom metadata."""
        custom_metadata = SessionMetadata(
            session_id="will-be-overwritten",
            project="test-project",
            chunk_count=10,
            tags=["test"]
        )
        metadata = registry.add_session("session-002", custom_metadata)
        assert metadata.session_id == "session-002"  # ID is overwritten
        assert metadata.project == "test-project"
        assert metadata.chunk_count == 10
        assert metadata.tags == ["test"]

    def test_get_session_exists(self, registry):
        """Test getting an existing session."""
        registry.add_session("session-003", SessionMetadata(
            session_id="session-003",
            project="my-project"
        ))
        metadata = registry.get_session("session-003")
        assert metadata is not None
        assert metadata.session_id == "session-003"
        assert metadata.project == "my-project"

    def test_get_session_not_exists(self, registry):
        """Test getting a non-existent session."""
        metadata = registry.get_session("nonexistent")
        assert metadata is None

    def test_update_session_exists(self, registry):
        """Test updating an existing session."""
        registry.add_session("session-004")
        updated = registry.update_session(
            "session-004",
            project="updated-project",
            chunk_count=50
        )
        assert updated is not None
        assert updated.project == "updated-project"
        assert updated.chunk_count == 50

        # Verify persistence
        metadata = registry.get_session("session-004")
        assert metadata.project == "updated-project"
        assert metadata.chunk_count == 50

    def test_update_session_not_exists(self, registry):
        """Test updating a non-existent session."""
        result = registry.update_session("nonexistent", project="test")
        assert result is None

    def test_delete_session_exists(self, registry):
        """Test deleting an existing session."""
        registry.add_session("session-005")
        assert registry.get_session("session-005") is not None

        result = registry.delete_session("session-005")
        assert result is True
        assert registry.get_session("session-005") is None

    def test_delete_session_not_exists(self, registry):
        """Test deleting a non-existent session."""
        result = registry.delete_session("nonexistent")
        assert result is False

    def test_list_sessions_all(self, registry):
        """Test listing all sessions."""
        registry.add_session("session-006", SessionMetadata(
            session_id="session-006",
            project="project-a"
        ))
        registry.add_session("session-007", SessionMetadata(
            session_id="session-007",
            project="project-b"
        ))

        sessions = registry.list_sessions()
        assert len(sessions) == 2
        session_ids = {s.session_id for s in sessions}
        assert "session-006" in session_ids
        assert "session-007" in session_ids

    def test_list_sessions_filter_by_project(self, registry):
        """Test listing sessions filtered by project."""
        registry.add_session("session-008", SessionMetadata(
            session_id="session-008",
            project="project-a"
        ))
        registry.add_session("session-009", SessionMetadata(
            session_id="session-009",
            project="project-b"
        ))
        registry.add_session("session-010", SessionMetadata(
            session_id="session-010",
            project="project-a"
        ))

        sessions = registry.list_sessions(project="project-a")
        assert len(sessions) == 2
        for session in sessions:
            assert session.project == "project-a"

    def test_list_sessions_filter_by_tags(self, registry):
        """Test listing sessions filtered by tags."""
        registry.add_session("session-011", SessionMetadata(
            session_id="session-011",
            tags=["urgent", "bugfix"]
        ))
        registry.add_session("session-012", SessionMetadata(
            session_id="session-012",
            tags=["feature"]
        ))
        registry.add_session("session-013", SessionMetadata(
            session_id="session-013",
            tags=["urgent", "feature"]
        ))

        sessions = registry.list_sessions(tags=["urgent"])
        assert len(sessions) == 2
        session_ids = {s.session_id for s in sessions}
        assert "session-011" in session_ids
        assert "session-013" in session_ids

    def test_get_all_sessions(self, registry):
        """Test getting all sessions as dictionary."""
        registry.add_session("session-014")
        registry.add_session("session-015")

        all_sessions = registry.get_all_sessions()
        assert isinstance(all_sessions, dict)
        assert len(all_sessions) == 2
        assert "session-014" in all_sessions
        assert "session-015" in all_sessions

    def test_set_last_synced_with_timestamp(self, registry):
        """Test setting last_synced with custom timestamp."""
        registry.add_session("session-016")
        timestamp = "2026-01-20T15:30:00"

        result = registry.set_last_synced("session-016", timestamp)
        assert result is True

        metadata = registry.get_session("session-016")
        assert metadata.last_synced == timestamp

    def test_set_last_synced_auto_timestamp(self, registry):
        """Test setting last_synced with auto-generated timestamp."""
        registry.add_session("session-017")

        result = registry.set_last_synced("session-017")
        assert result is True

        metadata = registry.get_session("session-017")
        assert metadata.last_synced is not None
        # Verify it's a valid ISO timestamp
        datetime.fromisoformat(metadata.last_synced)

    def test_set_last_synced_nonexistent(self, registry):
        """Test setting last_synced for non-existent session."""
        result = registry.set_last_synced("nonexistent")
        assert result is False

    def test_get_stats_empty(self, registry):
        """Test getting stats from empty registry."""
        stats = registry.get_stats()
        assert stats['total_sessions'] == 0
        assert stats['total_chunks'] == 0
        assert stats['total_messages'] == 0
        assert stats['total_projects'] == 0
        assert stats['projects'] == []

    def test_get_stats_with_data(self, registry):
        """Test getting stats with data."""
        registry.add_session("session-018", SessionMetadata(
            session_id="session-018",
            project="project-a",
            chunk_count=10,
            message_count=50
        ))
        registry.add_session("session-019", SessionMetadata(
            session_id="session-019",
            project="project-b",
            chunk_count=20,
            message_count=100
        ))
        registry.add_session("session-020", SessionMetadata(
            session_id="session-020",
            project="project-a",
            chunk_count=5,
            message_count=25
        ))

        stats = registry.get_stats()
        assert stats['total_sessions'] == 3
        assert stats['total_chunks'] == 35
        assert stats['total_messages'] == 175
        assert stats['total_projects'] == 2
        assert set(stats['projects']) == {"project-a", "project-b"}

    def test_clear(self, registry):
        """Test clearing all sessions."""
        registry.add_session("session-021")
        registry.add_session("session-022")
        assert len(registry.get_all_sessions()) == 2

        registry.clear()
        assert len(registry.get_all_sessions()) == 0

    def test_persistence(self, temp_registry_path):
        """Test that registry persists to disk."""
        # Create registry and add session
        registry1 = SessionRegistry(registry_path=temp_registry_path)
        registry1.add_session("session-023", SessionMetadata(
            session_id="session-023",
            project="persistent-project",
            chunk_count=99
        ))

        # Create new registry instance and verify data persists
        registry2 = SessionRegistry(registry_path=temp_registry_path)
        metadata = registry2.get_session("session-023")
        assert metadata is not None
        assert metadata.project == "persistent-project"
        assert metadata.chunk_count == 99

    def test_persistence_after_update(self, temp_registry_path):
        """Test that updates persist to disk."""
        registry1 = SessionRegistry(registry_path=temp_registry_path)
        registry1.add_session("session-024")
        registry1.update_session("session-024", chunk_count=42)

        registry2 = SessionRegistry(registry_path=temp_registry_path)
        metadata = registry2.get_session("session-024")
        assert metadata.chunk_count == 42

    def test_corrupted_registry_file(self, temp_registry_path):
        """Test handling of corrupted registry file."""
        # Create corrupted JSON file
        with open(temp_registry_path, 'w') as f:
            f.write("{ invalid json }")

        # Should start fresh without crashing
        registry = SessionRegistry(registry_path=temp_registry_path)
        assert len(registry.get_all_sessions()) == 0

    def test_thread_safety(self, registry):
        """Test thread safety with concurrent operations."""
        import threading

        def add_sessions(start_id, count):
            for i in range(count):
                session_id = f"session-{start_id + i}"
                registry.add_session(session_id)

        threads = []
        for i in range(5):
            t = threading.Thread(target=add_sessions, args=(i * 100, 10))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should have 50 sessions total
        assert len(registry.get_all_sessions()) == 50

    def test_json_structure(self, temp_registry_path):
        """Test the structure of the saved JSON file."""
        registry = SessionRegistry(registry_path=temp_registry_path)
        registry.add_session("session-025", SessionMetadata(
            session_id="session-025",
            project="test"
        ))

        # Read and verify JSON structure
        with open(temp_registry_path, 'r') as f:
            data = json.load(f)

        assert 'sessions' in data
        assert 'last_updated' in data
        assert 'session-025' in data['sessions']
        assert data['sessions']['session-025']['project'] == 'test'
