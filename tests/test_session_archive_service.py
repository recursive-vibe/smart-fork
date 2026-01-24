"""
Unit tests for SessionArchiveService.
"""

import pytest
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from smart_fork.session_archive_service import SessionArchiveService, ArchiveStats
from smart_fork.session_registry import SessionRegistry, SessionMetadata
from smart_fork.vector_db_service import VectorDBService


@pytest.fixture
def temp_dirs():
    """Create temporary directories for test databases."""
    temp_db_dir = tempfile.mkdtemp(prefix="test_archive_db_")
    temp_registry_dir = tempfile.mkdtemp(prefix="test_archive_reg_")
    yield temp_db_dir, temp_registry_dir
    # Cleanup
    if os.path.exists(temp_db_dir):
        shutil.rmtree(temp_db_dir)
    if os.path.exists(temp_registry_dir):
        shutil.rmtree(temp_registry_dir)


@pytest.fixture
def vector_db_service(temp_dirs):
    """Create a VectorDBService instance for testing."""
    temp_db_dir, _ = temp_dirs
    service = VectorDBService(persist_directory=temp_db_dir)
    yield service
    try:
        service.reset()
    except Exception:
        pass


@pytest.fixture
def session_registry(temp_dirs):
    """Create a SessionRegistry instance for testing."""
    _, temp_registry_dir = temp_dirs
    registry_path = os.path.join(temp_registry_dir, "test-registry.json")
    registry = SessionRegistry(registry_path=registry_path)
    yield registry
    try:
        registry.clear()
    except Exception:
        pass


@pytest.fixture
def archive_service(vector_db_service, session_registry):
    """Create a SessionArchiveService instance for testing."""
    return SessionArchiveService(
        vector_db_service=vector_db_service,
        session_registry=session_registry,
        archive_threshold_days=365
    )


@pytest.fixture
def sample_embeddings():
    """Generate sample embeddings for testing."""
    embeddings = []
    for i in range(5):
        embedding = [0.0] * 384
        for j in range(10):
            embedding[i * 10 + j] = 1.0
        embeddings.append(embedding)
    return embeddings


class TestSessionArchiveService:
    """Test SessionArchiveService functionality."""

    def test_initialization(self, archive_service):
        """Test that SessionArchiveService initializes correctly."""
        assert archive_service is not None
        assert archive_service.archive_threshold_days == 365
        assert archive_service.archive_collection is not None

    def test_is_session_old_recent(self, archive_service, session_registry):
        """Test that recent sessions are not considered old."""
        # Create a session with recent last_modified
        recent_date = datetime.utcnow() - timedelta(days=30)
        metadata = SessionMetadata(
            session_id="recent-session",
            last_modified=recent_date.isoformat()
        )
        session_registry.add_session("recent-session", metadata)

        # Should not be considered old
        assert not archive_service._is_session_old(metadata)

    def test_is_session_old_ancient(self, archive_service, session_registry):
        """Test that old sessions are considered old."""
        # Create a session with old last_modified (2 years ago)
        old_date = datetime.utcnow() - timedelta(days=730)
        metadata = SessionMetadata(
            session_id="old-session",
            last_modified=old_date.isoformat()
        )
        session_registry.add_session("old-session", metadata)

        # Should be considered old
        assert archive_service._is_session_old(metadata)

    def test_is_session_old_uses_created_at(self, archive_service):
        """Test that created_at is used when last_modified is missing."""
        # Session with only created_at (old)
        old_date = datetime.utcnow() - timedelta(days=730)
        metadata = SessionMetadata(
            session_id="old-session-created",
            created_at=old_date.isoformat()
        )

        assert archive_service._is_session_old(metadata)

    def test_is_session_old_no_dates(self, archive_service):
        """Test that sessions without dates are not considered old."""
        metadata = SessionMetadata(session_id="no-dates")
        assert not archive_service._is_session_old(metadata)

    def test_archive_session_basic(self, archive_service, vector_db_service, session_registry, sample_embeddings):
        """Test archiving a single session."""
        session_id = "test-session-1"

        # Add session to registry
        old_date = datetime.utcnow() - timedelta(days=730)
        metadata = SessionMetadata(
            session_id=session_id,
            last_modified=old_date.isoformat(),
            chunk_count=3
        )
        session_registry.add_session(session_id, metadata)

        # Add chunks to vector DB
        chunks = ["This is chunk 1", "This is chunk 2", "This is chunk 3"]
        metadatas = [
            {"session_id": session_id, "chunk_index": i}
            for i in range(3)
        ]
        vector_db_service.add_chunks(
            chunks=chunks,
            embeddings=sample_embeddings[:3],
            metadata=metadatas
        )

        # Archive the session
        chunks_moved = archive_service._archive_session(session_id)

        # Verify chunks were moved
        assert chunks_moved == 3

        # Verify chunks are gone from active DB
        active_chunks = vector_db_service.get_session_chunks(session_id)
        assert len(active_chunks) == 0

        # Verify chunks are in archive
        archive_results = archive_service.archive_collection.get(
            where={"session_id": session_id}
        )
        assert len(archive_results["ids"]) == 3

        # Verify session is marked as archived
        updated_metadata = session_registry.get_session(session_id)
        assert updated_metadata.archived is True

    def test_archive_old_sessions_dry_run(self, archive_service, session_registry):
        """Test dry run mode for archiving."""
        # Add old session
        old_date = datetime.utcnow() - timedelta(days=730)
        metadata = SessionMetadata(
            session_id="old-session",
            last_modified=old_date.isoformat()
        )
        session_registry.add_session("old-session", metadata)

        # Add recent session
        recent_date = datetime.utcnow() - timedelta(days=30)
        metadata2 = SessionMetadata(
            session_id="recent-session",
            last_modified=recent_date.isoformat()
        )
        session_registry.add_session("recent-session", metadata2)

        # Dry run
        result = archive_service.archive_old_sessions(dry_run=True)

        assert result["dry_run"] is True
        assert "old-session" in result["sessions_archived"]
        assert "recent-session" not in result["sessions_archived"]
        assert result["chunks_moved"] == 0

    def test_archive_old_sessions_actual(self, archive_service, vector_db_service, session_registry, sample_embeddings):
        """Test actual archiving of old sessions."""
        # Add old session with chunks
        old_date = datetime.utcnow() - timedelta(days=730)
        session_id = "old-session-to-archive"
        metadata = SessionMetadata(
            session_id=session_id,
            last_modified=old_date.isoformat(),
            chunk_count=2
        )
        session_registry.add_session(session_id, metadata)

        chunks = ["Old chunk 1", "Old chunk 2"]
        metadatas = [
            {"session_id": session_id, "chunk_index": i}
            for i in range(2)
        ]
        vector_db_service.add_chunks(
            chunks=chunks,
            embeddings=sample_embeddings[:2],
            metadata=metadatas
        )

        # Archive
        result = archive_service.archive_old_sessions(dry_run=False)

        assert result["dry_run"] is False
        assert session_id in result["sessions_archived"]
        assert result["chunks_moved"] >= 2

    def test_restore_session(self, archive_service, vector_db_service, session_registry, sample_embeddings):
        """Test restoring an archived session."""
        session_id = "session-to-restore"

        # Create and archive a session
        old_date = datetime.utcnow() - timedelta(days=730)
        metadata = SessionMetadata(
            session_id=session_id,
            last_modified=old_date.isoformat(),
            chunk_count=2
        )
        session_registry.add_session(session_id, metadata)

        chunks = ["Restore chunk 1", "Restore chunk 2"]
        metadatas = [
            {"session_id": session_id, "chunk_index": i}
            for i in range(2)
        ]
        vector_db_service.add_chunks(
            chunks=chunks,
            embeddings=sample_embeddings[:2],
            metadata=metadatas
        )

        # Archive it
        archive_service._archive_session(session_id)

        # Verify it's archived
        assert session_registry.get_session(session_id).archived is True

        # Restore it
        result = archive_service.restore_session(session_id)

        # Verify restore was successful
        assert result["success"] is True
        assert result["chunks_restored"] == 2

        # Verify chunks are back in active DB
        active_chunks = vector_db_service.get_session_chunks(session_id)
        assert len(active_chunks) == 2

        # Verify chunks are gone from archive
        archive_results = archive_service.archive_collection.get(
            where={"session_id": session_id}
        )
        assert len(archive_results["ids"]) == 0

        # Verify session is marked as not archived
        updated_metadata = session_registry.get_session(session_id)
        assert updated_metadata.archived is False

    def test_restore_nonexistent_session(self, archive_service):
        """Test restoring a session that doesn't exist in archive."""
        result = archive_service.restore_session("nonexistent-session")

        assert result["success"] is False
        assert "error" in result
        assert result["chunks_restored"] == 0

    def test_search_archive(self, archive_service, vector_db_service, session_registry, sample_embeddings):
        """Test searching archived sessions."""
        session_id = "searchable-archive"

        # Create and archive a session
        old_date = datetime.utcnow() - timedelta(days=730)
        metadata = SessionMetadata(
            session_id=session_id,
            last_modified=old_date.isoformat(),
            chunk_count=2
        )
        session_registry.add_session(session_id, metadata)

        chunks = ["Searchable content here", "More searchable content"]
        metadatas = [
            {"session_id": session_id, "chunk_index": i}
            for i in range(2)
        ]
        vector_db_service.add_chunks(
            chunks=chunks,
            embeddings=sample_embeddings[:2],
            metadata=metadatas
        )

        # Archive it
        archive_service._archive_session(session_id)

        # Search the archive
        query_embedding = sample_embeddings[0]
        results = archive_service.search_archive(query_embedding, k=10)

        # Should find results in archive
        assert len(results) > 0
        assert any(r.session_id == session_id for r in results)

    def test_get_archive_stats_empty(self, archive_service):
        """Test getting stats when archive is empty."""
        stats = archive_service.get_archive_stats()

        assert isinstance(stats, ArchiveStats)
        assert stats.total_archived_sessions == 0
        assert stats.total_archived_chunks == 0
        assert stats.oldest_session_date is None
        assert stats.newest_session_date is None

    def test_get_archive_stats_with_data(self, archive_service, vector_db_service, session_registry, sample_embeddings):
        """Test getting stats with archived sessions."""
        # Archive two sessions
        for i in range(2):
            session_id = f"archived-{i}"
            old_date = datetime.utcnow() - timedelta(days=730 + i * 10)
            metadata = SessionMetadata(
                session_id=session_id,
                last_modified=old_date.isoformat(),
                chunk_count=2
            )
            session_registry.add_session(session_id, metadata)

            chunks = [f"Chunk {j}" for j in range(2)]
            metadatas = [
                {"session_id": session_id, "chunk_index": j}
                for j in range(2)
            ]
            vector_db_service.add_chunks(
                chunks=chunks,
                embeddings=sample_embeddings[:2],
                metadata=metadatas
            )

            archive_service._archive_session(session_id)

        stats = archive_service.get_archive_stats()

        assert stats.total_archived_sessions == 2
        assert stats.total_archived_chunks == 4
        assert stats.oldest_session_date is not None
        assert stats.newest_session_date is not None

    def test_list_archived_sessions(self, archive_service, vector_db_service, session_registry, sample_embeddings):
        """Test listing all archived sessions."""
        # Archive one session
        session_id = "archived-session"
        old_date = datetime.utcnow() - timedelta(days=730)
        metadata = SessionMetadata(
            session_id=session_id,
            last_modified=old_date.isoformat(),
            chunk_count=1
        )
        session_registry.add_session(session_id, metadata)

        chunks = ["Archived chunk"]
        metadatas = [{"session_id": session_id, "chunk_index": 0}]
        vector_db_service.add_chunks(
            chunks=chunks,
            embeddings=sample_embeddings[:1],
            metadata=metadatas
        )

        archive_service._archive_session(session_id)

        # Add a non-archived session
        recent_metadata = SessionMetadata(
            session_id="recent-session",
            last_modified=datetime.utcnow().isoformat()
        )
        session_registry.add_session("recent-session", recent_metadata)

        # List archived sessions
        archived = archive_service.list_archived_sessions()

        assert len(archived) == 1
        assert archived[0].session_id == session_id

    def test_is_session_archived(self, archive_service, vector_db_service, session_registry, sample_embeddings):
        """Test checking if a session is archived."""
        session_id = "check-archived"

        # Create session
        old_date = datetime.utcnow() - timedelta(days=730)
        metadata = SessionMetadata(
            session_id=session_id,
            last_modified=old_date.isoformat(),
            chunk_count=1
        )
        session_registry.add_session(session_id, metadata)

        chunks = ["Check chunk"]
        metadatas = [{"session_id": session_id, "chunk_index": 0}]
        vector_db_service.add_chunks(
            chunks=chunks,
            embeddings=sample_embeddings[:1],
            metadata=metadatas
        )

        # Should not be archived yet
        assert not archive_service.is_session_archived(session_id)

        # Archive it
        archive_service._archive_session(session_id)

        # Now should be archived
        assert archive_service.is_session_archived(session_id)

    def test_archive_empty_session(self, archive_service, session_registry):
        """Test archiving a session with no chunks."""
        session_id = "empty-session"

        # Add session to registry (old)
        old_date = datetime.utcnow() - timedelta(days=730)
        metadata = SessionMetadata(
            session_id=session_id,
            last_modified=old_date.isoformat(),
            chunk_count=0
        )
        session_registry.add_session(session_id, metadata)

        # Archive (should handle gracefully)
        chunks_moved = archive_service._archive_session(session_id)

        assert chunks_moved == 0

    def test_custom_threshold_days(self, vector_db_service, session_registry):
        """Test custom archive threshold."""
        # Create service with 30-day threshold
        service = SessionArchiveService(
            vector_db_service=vector_db_service,
            session_registry=session_registry,
            archive_threshold_days=30
        )

        # Session that's 60 days old
        old_date = datetime.utcnow() - timedelta(days=60)
        metadata = SessionMetadata(
            session_id="60-day-old",
            last_modified=old_date.isoformat()
        )

        # Should be considered old with 30-day threshold
        assert service._is_session_old(metadata)

        # Session that's 15 days old
        recent_date = datetime.utcnow() - timedelta(days=15)
        metadata2 = SessionMetadata(
            session_id="15-day-old",
            last_modified=recent_date.isoformat()
        )

        # Should not be considered old with 30-day threshold
        assert not service._is_session_old(metadata2)
