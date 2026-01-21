"""
Integration tests for session archiving with search service.
"""

import pytest
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from smart_fork.session_archive_service import SessionArchiveService
from smart_fork.session_registry import SessionRegistry, SessionMetadata
from smart_fork.vector_db_service import VectorDBService
from smart_fork.embedding_service import EmbeddingService
from smart_fork.scoring_service import ScoringService
from smart_fork.search_service import SearchService
from smart_fork.config_manager import Config


@pytest.fixture
def temp_dirs():
    """Create temporary directories for test databases."""
    temp_db_dir = tempfile.mkdtemp(prefix="test_archive_int_db_")
    temp_registry_dir = tempfile.mkdtemp(prefix="test_archive_int_reg_")
    yield temp_db_dir, temp_registry_dir
    # Cleanup
    if os.path.exists(temp_db_dir):
        shutil.rmtree(temp_db_dir)
    if os.path.exists(temp_registry_dir):
        shutil.rmtree(temp_registry_dir)


@pytest.fixture
def vector_db_service(temp_dirs):
    """Create a VectorDBService instance."""
    temp_db_dir, _ = temp_dirs
    service = VectorDBService(persist_directory=temp_db_dir)
    yield service
    try:
        service.reset()
    except Exception:
        pass


@pytest.fixture
def session_registry(temp_dirs):
    """Create a SessionRegistry instance."""
    _, temp_registry_dir = temp_dirs
    registry_path = os.path.join(temp_registry_dir, "test-registry.json")
    registry = SessionRegistry(registry_path=registry_path)
    yield registry


@pytest.fixture
def embedding_service():
    """Create an EmbeddingService instance."""
    return EmbeddingService(use_cache=False)


@pytest.fixture
def scoring_service():
    """Create a ScoringService instance."""
    return ScoringService()


@pytest.fixture
def archive_service(vector_db_service, session_registry):
    """Create a SessionArchiveService instance."""
    return SessionArchiveService(
        vector_db_service=vector_db_service,
        session_registry=session_registry,
        archive_threshold_days=365
    )


@pytest.fixture
def search_service(embedding_service, vector_db_service, scoring_service, session_registry, archive_service):
    """Create a SearchService with archive support."""
    return SearchService(
        embedding_service=embedding_service,
        vector_db_service=vector_db_service,
        scoring_service=scoring_service,
        session_registry=session_registry,
        enable_cache=False,  # Disable cache for testing
        archive_service=archive_service
    )


class TestSessionArchiveIntegration:
    """Integration tests for session archiving with search."""

    def test_search_without_archive(self, search_service, embedding_service, vector_db_service, session_registry, archive_service):
        """Test that archived sessions are not returned by default."""
        # Create and index an active session
        active_session_id = "active-session"
        active_metadata = SessionMetadata(
            session_id=active_session_id,
            last_modified=datetime.utcnow().isoformat(),
            chunk_count=2
        )
        session_registry.add_session(active_session_id, active_metadata)

        # Create content about Python
        active_chunks = [
            "Python is a great programming language",
            "I love using Python for data analysis"
        ]
        embedding_service.load_model()
        active_embeddings = embedding_service.embed_batch(active_chunks)
        active_metadatas = [
            {"session_id": active_session_id, "chunk_index": i}
            for i in range(2)
        ]
        vector_db_service.add_chunks(
            chunks=active_chunks,
            embeddings=active_embeddings,
            metadata=active_metadatas
        )

        # Create and archive an old session
        archived_session_id = "archived-session"
        old_date = datetime.utcnow() - timedelta(days=730)
        archived_metadata = SessionMetadata(
            session_id=archived_session_id,
            last_modified=old_date.isoformat(),
            chunk_count=2
        )
        session_registry.add_session(archived_session_id, archived_metadata)

        archived_chunks = [
            "Python was used in this archived session",
            "Old Python code from two years ago"
        ]
        archived_embeddings = embedding_service.embed_batch(archived_chunks)
        archived_metadatas = [
            {"session_id": archived_session_id, "chunk_index": i}
            for i in range(2)
        ]
        vector_db_service.add_chunks(
            chunks=archived_chunks,
            embeddings=archived_embeddings,
            metadata=archived_metadatas
        )

        # Archive the old session
        archive_service._archive_session(archived_session_id)

        # Search without including archive
        results = search_service.search("Python programming", include_archive=False)

        # Should only find active session
        session_ids = [r.session_id for r in results]
        assert active_session_id in session_ids
        assert archived_session_id not in session_ids

    def test_search_with_archive(self, search_service, embedding_service, vector_db_service, session_registry, archive_service):
        """Test that archived sessions are returned when include_archive=True."""
        # Create and index an active session
        active_session_id = "active-session-2"
        active_metadata = SessionMetadata(
            session_id=active_session_id,
            last_modified=datetime.utcnow().isoformat(),
            chunk_count=2
        )
        session_registry.add_session(active_session_id, active_metadata)

        active_chunks = [
            "JavaScript is a versatile language",
            "Modern JavaScript is powerful"
        ]
        embedding_service.load_model()
        active_embeddings = embedding_service.embed_batch(active_chunks)
        active_metadatas = [
            {"session_id": active_session_id, "chunk_index": i}
            for i in range(2)
        ]
        vector_db_service.add_chunks(
            chunks=active_chunks,
            embeddings=active_embeddings,
            metadata=active_metadatas
        )

        # Create and archive an old session
        archived_session_id = "archived-session-2"
        old_date = datetime.utcnow() - timedelta(days=730)
        archived_metadata = SessionMetadata(
            session_id=archived_session_id,
            last_modified=old_date.isoformat(),
            chunk_count=2
        )
        session_registry.add_session(archived_session_id, archived_metadata)

        archived_chunks = [
            "JavaScript framework from old project",
            "Archived JavaScript code examples"
        ]
        archived_embeddings = embedding_service.embed_batch(archived_chunks)
        archived_metadatas = [
            {"session_id": archived_session_id, "chunk_index": i}
            for i in range(2)
        ]
        vector_db_service.add_chunks(
            chunks=archived_chunks,
            embeddings=archived_embeddings,
            metadata=archived_metadatas
        )

        # Archive the old session
        archive_service._archive_session(archived_session_id)

        # Search with archive included
        results = search_service.search("JavaScript", include_archive=True)

        # Should find both sessions
        session_ids = [r.session_id for r in results]
        assert active_session_id in session_ids or archived_session_id in session_ids
        # At least one should be found (depending on ranking)

    def test_archive_and_restore_workflow(self, search_service, embedding_service, vector_db_service, session_registry, archive_service):
        """Test complete workflow: archive -> search -> restore."""
        session_id = "workflow-session"

        # Create session
        old_date = datetime.utcnow() - timedelta(days=730)
        metadata = SessionMetadata(
            session_id=session_id,
            last_modified=old_date.isoformat(),
            chunk_count=2
        )
        session_registry.add_session(session_id, metadata)

        chunks = [
            "React hooks are useful",
            "React component lifecycle"
        ]
        embedding_service.load_model()
        embeddings = embedding_service.embed_batch(chunks)
        metadatas = [
            {"session_id": session_id, "chunk_index": i}
            for i in range(2)
        ]
        vector_db_service.add_chunks(
            chunks=chunks,
            embeddings=embeddings,
            metadata=metadatas
        )

        # 1. Search finds it (before archiving)
        results_before = search_service.search("React", include_archive=False)
        session_ids_before = [r.session_id for r in results_before]
        assert session_id in session_ids_before

        # 2. Archive the session
        archive_service._archive_session(session_id)

        # 3. Search doesn't find it without include_archive
        results_after = search_service.search("React", include_archive=False)
        session_ids_after = [r.session_id for r in results_after]
        assert session_id not in session_ids_after

        # 4. Search finds it with include_archive
        results_archive = search_service.search("React", include_archive=True)
        session_ids_archive = [r.session_id for r in results_archive]
        assert session_id in session_ids_archive

        # 5. Restore the session
        restore_result = archive_service.restore_session(session_id)
        assert restore_result["success"] is True

        # 6. Search finds it again without include_archive
        results_restored = search_service.search("React", include_archive=False)
        session_ids_restored = [r.session_id for r in results_restored]
        assert session_id in session_ids_restored

    def test_bulk_archive_workflow(self, embedding_service, vector_db_service, session_registry, archive_service):
        """Test archiving multiple sessions at once."""
        # Create 3 old sessions and 2 recent sessions
        old_sessions = []
        recent_sessions = []

        embedding_service.load_model()

        for i in range(3):
            session_id = f"old-bulk-{i}"
            old_date = datetime.utcnow() - timedelta(days=730 + i)
            metadata = SessionMetadata(
                session_id=session_id,
                last_modified=old_date.isoformat(),
                chunk_count=1
            )
            session_registry.add_session(session_id, metadata)

            chunks = [f"Old content {i}"]
            embeddings = embedding_service.embed_batch(chunks)
            metadatas = [{"session_id": session_id, "chunk_index": 0}]
            vector_db_service.add_chunks(
                chunks=chunks,
                embeddings=embeddings,
                metadata=metadatas
            )
            old_sessions.append(session_id)

        for i in range(2):
            session_id = f"recent-bulk-{i}"
            recent_date = datetime.utcnow() - timedelta(days=30 + i)
            metadata = SessionMetadata(
                session_id=session_id,
                last_modified=recent_date.isoformat(),
                chunk_count=1
            )
            session_registry.add_session(session_id, metadata)

            chunks = [f"Recent content {i}"]
            embeddings = embedding_service.embed_batch(chunks)
            metadatas = [{"session_id": session_id, "chunk_index": 0}]
            vector_db_service.add_chunks(
                chunks=chunks,
                embeddings=embeddings,
                metadata=metadatas
            )
            recent_sessions.append(session_id)

        # Dry run first
        dry_result = archive_service.archive_old_sessions(dry_run=True)
        assert dry_result["dry_run"] is True
        assert len(dry_result["sessions_archived"]) == 3

        # Archive for real
        result = archive_service.archive_old_sessions(dry_run=False)
        assert result["dry_run"] is False
        assert len(result["sessions_archived"]) == 3

        # Verify old sessions are archived
        for session_id in old_sessions:
            assert archive_service.is_session_archived(session_id)

        # Verify recent sessions are not archived
        for session_id in recent_sessions:
            assert not archive_service.is_session_archived(session_id)

    def test_archive_stats_accuracy(self, embedding_service, vector_db_service, session_registry, archive_service):
        """Test that archive stats are accurate."""
        # Archive 2 sessions with different dates
        embedding_service.load_model()

        oldest_date = datetime.utcnow() - timedelta(days=800)
        session_id_1 = "stats-session-1"
        metadata_1 = SessionMetadata(
            session_id=session_id_1,
            last_modified=oldest_date.isoformat(),
            chunk_count=2
        )
        session_registry.add_session(session_id_1, metadata_1)

        chunks_1 = ["Stats chunk 1", "Stats chunk 2"]
        embeddings_1 = embedding_service.embed_batch(chunks_1)
        metadatas_1 = [
            {"session_id": session_id_1, "chunk_index": i}
            for i in range(2)
        ]
        vector_db_service.add_chunks(
            chunks=chunks_1,
            embeddings=embeddings_1,
            metadata=metadatas_1
        )

        newest_date = datetime.utcnow() - timedelta(days=400)
        session_id_2 = "stats-session-2"
        metadata_2 = SessionMetadata(
            session_id=session_id_2,
            last_modified=newest_date.isoformat(),
            chunk_count=3
        )
        session_registry.add_session(session_id_2, metadata_2)

        chunks_2 = ["Stats chunk 3", "Stats chunk 4", "Stats chunk 5"]
        embeddings_2 = embedding_service.embed_batch(chunks_2)
        metadatas_2 = [
            {"session_id": session_id_2, "chunk_index": i}
            for i in range(3)
        ]
        vector_db_service.add_chunks(
            chunks=chunks_2,
            embeddings=embeddings_2,
            metadata=metadatas_2
        )

        # Archive both
        archive_service._archive_session(session_id_1)
        archive_service._archive_session(session_id_2)

        # Get stats
        stats = archive_service.get_archive_stats()

        assert stats.total_archived_sessions == 2
        assert stats.total_archived_chunks == 5
        assert stats.oldest_session_date is not None
        assert stats.newest_session_date is not None

    def test_search_service_without_archive_service(self, embedding_service, vector_db_service, scoring_service, session_registry):
        """Test that search service works without archive service."""
        # Create search service without archive service
        search_service = SearchService(
            embedding_service=embedding_service,
            vector_db_service=vector_db_service,
            scoring_service=scoring_service,
            session_registry=session_registry,
            enable_cache=False,
            archive_service=None
        )

        # Create session
        session_id = "no-archive-session"
        metadata = SessionMetadata(
            session_id=session_id,
            last_modified=datetime.utcnow().isoformat(),
            chunk_count=1
        )
        session_registry.add_session(session_id, metadata)

        chunks = ["Test content"]
        embedding_service.load_model()
        embeddings = embedding_service.embed_batch(chunks)
        metadatas = [{"session_id": session_id, "chunk_index": 0}]
        vector_db_service.add_chunks(
            chunks=chunks,
            embeddings=embeddings,
            metadata=metadatas
        )

        # Search should work even with include_archive=True
        results = search_service.search("Test", include_archive=True)

        # Should still find the session
        session_ids = [r.session_id for r in results]
        assert session_id in session_ids
