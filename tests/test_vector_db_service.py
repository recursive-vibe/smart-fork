"""
Tests for VectorDBService class.

This module contains comprehensive tests for the ChromaDB vector database
service, including CRUD operations, search functionality, and edge cases.
"""

import pytest
import os
import tempfile
import shutil
from typing import List
from smart_fork.vector_db_service import VectorDBService, ChunkSearchResult


@pytest.fixture
def temp_db_dir():
    """Create a temporary directory for test database."""
    temp_dir = tempfile.mkdtemp(prefix="test_vector_db_")
    yield temp_dir
    # Cleanup after test
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def db_service(temp_db_dir):
    """Create a VectorDBService instance for testing."""
    service = VectorDBService(persist_directory=temp_db_dir)
    yield service
    # Reset after each test
    try:
        service.reset()
    except Exception:
        pass


@pytest.fixture
def sample_embeddings():
    """Generate sample embeddings for testing."""
    # Create 5 sample embeddings (384 dimensions)
    embeddings = []
    for i in range(5):
        # Simple pattern: mostly zeros with a few ones
        embedding = [0.0] * 384
        # Set some values based on index
        for j in range(10):
            embedding[i * 10 + j] = 1.0
        embeddings.append(embedding)
    return embeddings


class TestVectorDBServiceInitialization:
    """Test VectorDBService initialization."""

    def test_init_with_custom_directory(self, temp_db_dir):
        """Test initialization with custom directory."""
        service = VectorDBService(persist_directory=temp_db_dir)
        assert service.persist_directory == temp_db_dir
        assert os.path.exists(temp_db_dir)
        assert service.collection is not None
        assert service.collection.name == "session_chunks"

    def test_init_with_default_directory(self):
        """Test initialization with default directory."""
        service = VectorDBService()
        expected_dir = os.path.join(os.path.expanduser("~"), ".smart-fork", "vector_db")
        assert service.persist_directory == expected_dir
        # Note: We don't create this in tests to avoid modifying user's home directory

    def test_init_creates_directory(self, temp_db_dir):
        """Test that initialization creates the directory if it doesn't exist."""
        db_path = os.path.join(temp_db_dir, "new_db")
        assert not os.path.exists(db_path)

        service = VectorDBService(persist_directory=db_path)
        assert os.path.exists(db_path)
        assert service.persist_directory == db_path


class TestAddChunks:
    """Test add_chunks method."""

    def test_add_single_chunk(self, db_service, sample_embeddings):
        """Test adding a single chunk."""
        chunks = ["This is a test chunk"]
        embeddings = [sample_embeddings[0]]
        metadata = [{"session_id": "test_session_1", "chunk_index": 0}]

        chunk_ids = db_service.add_chunks(chunks, embeddings, metadata)

        assert len(chunk_ids) == 1
        assert chunk_ids[0] == "test_session_1_chunk_0"

        # Verify it was added
        stats = db_service.get_stats()
        assert stats["total_chunks"] == 1

    def test_add_multiple_chunks(self, db_service, sample_embeddings):
        """Test adding multiple chunks."""
        chunks = [f"Chunk {i}" for i in range(5)]
        metadata = [
            {"session_id": "session_1", "chunk_index": i}
            for i in range(5)
        ]

        chunk_ids = db_service.add_chunks(chunks, sample_embeddings, metadata)

        assert len(chunk_ids) == 5
        assert all(id.startswith("session_1_chunk_") for id in chunk_ids)

        stats = db_service.get_stats()
        assert stats["total_chunks"] == 5

    def test_add_chunks_with_custom_ids(self, db_service, sample_embeddings):
        """Test adding chunks with custom IDs."""
        chunks = ["Chunk 1", "Chunk 2"]
        embeddings = sample_embeddings[:2]
        metadata = [
            {"session_id": "session_1", "chunk_index": 0},
            {"session_id": "session_1", "chunk_index": 1}
        ]
        custom_ids = ["custom_id_1", "custom_id_2"]

        chunk_ids = db_service.add_chunks(chunks, embeddings, metadata, chunk_ids=custom_ids)

        assert chunk_ids == custom_ids

    def test_add_empty_chunks(self, db_service):
        """Test adding empty chunks list."""
        chunk_ids = db_service.add_chunks([], [], [])
        assert chunk_ids == []

    def test_add_chunks_length_mismatch_embeddings(self, db_service, sample_embeddings):
        """Test error when chunks and embeddings lengths don't match."""
        chunks = ["Chunk 1", "Chunk 2"]
        embeddings = [sample_embeddings[0]]  # Only one embedding
        metadata = [{"session_id": "s1"}, {"session_id": "s1"}]

        with pytest.raises(ValueError, match="must match embeddings count"):
            db_service.add_chunks(chunks, embeddings, metadata)

    def test_add_chunks_length_mismatch_metadata(self, db_service, sample_embeddings):
        """Test error when chunks and metadata lengths don't match."""
        chunks = ["Chunk 1", "Chunk 2"]
        embeddings = sample_embeddings[:2]
        metadata = [{"session_id": "s1"}]  # Only one metadata

        with pytest.raises(ValueError, match="must match metadata count"):
            db_service.add_chunks(chunks, embeddings, metadata)

    def test_add_chunks_length_mismatch_ids(self, db_service, sample_embeddings):
        """Test error when chunk_ids length doesn't match."""
        chunks = ["Chunk 1", "Chunk 2"]
        embeddings = sample_embeddings[:2]
        metadata = [{"session_id": "s1"}, {"session_id": "s1"}]
        chunk_ids = ["id1"]  # Only one ID

        with pytest.raises(ValueError, match="must match chunks count"):
            db_service.add_chunks(chunks, embeddings, metadata, chunk_ids=chunk_ids)

    def test_add_chunks_with_various_metadata_types(self, db_service, sample_embeddings):
        """Test adding chunks with various metadata types."""
        chunks = ["Test chunk"]
        embeddings = [sample_embeddings[0]]
        metadata = [{
            "session_id": "test",
            "chunk_index": 0,
            "string_field": "value",
            "int_field": 42,
            "float_field": 3.14,
            "bool_field": True,
            "none_field": None
        }]

        chunk_ids = db_service.add_chunks(chunks, embeddings, metadata)
        assert len(chunk_ids) == 1

        # Verify metadata was stored
        result = db_service.get_chunk_by_id(chunk_ids[0])
        assert result is not None
        assert result.metadata["string_field"] == "value"
        assert result.metadata["int_field"] == 42
        assert result.metadata["float_field"] == 3.14
        assert result.metadata["bool_field"] is True


class TestSearchChunks:
    """Test search_chunks method."""

    def test_search_empty_database(self, db_service, sample_embeddings):
        """Test searching an empty database."""
        results = db_service.search_chunks(sample_embeddings[0], k=10)
        assert results == []

    def test_search_returns_results(self, db_service, sample_embeddings):
        """Test that search returns results."""
        # Add some chunks
        chunks = [f"Chunk {i}" for i in range(5)]
        metadata = [{"session_id": "session_1", "chunk_index": i} for i in range(5)]
        db_service.add_chunks(chunks, sample_embeddings, metadata)

        # Search with the first embedding
        results = db_service.search_chunks(sample_embeddings[0], k=5)

        assert len(results) > 0
        assert all(isinstance(r, ChunkSearchResult) for r in results)

    def test_search_respects_k_parameter(self, db_service, sample_embeddings):
        """Test that search respects the k parameter."""
        # Add 5 chunks
        chunks = [f"Chunk {i}" for i in range(5)]
        metadata = [{"session_id": "session_1", "chunk_index": i} for i in range(5)]
        db_service.add_chunks(chunks, sample_embeddings, metadata)

        # Search for top 3
        results = db_service.search_chunks(sample_embeddings[0], k=3)
        assert len(results) <= 3

    def test_search_with_k_zero(self, db_service, sample_embeddings):
        """Test search with k=0."""
        results = db_service.search_chunks(sample_embeddings[0], k=0)
        assert results == []

    def test_search_result_structure(self, db_service, sample_embeddings):
        """Test that search results have correct structure."""
        chunks = ["Test chunk"]
        metadata = [{"session_id": "session_1", "chunk_index": 0, "custom_field": "value"}]
        db_service.add_chunks(chunks, sample_embeddings[:1], metadata)

        results = db_service.search_chunks(sample_embeddings[0], k=1)

        assert len(results) == 1
        result = results[0]
        assert result.chunk_id is not None
        assert result.session_id == "session_1"
        assert result.content == "Test chunk"
        assert result.metadata["custom_field"] == "value"
        assert result.similarity > 0.0
        assert result.chunk_index == 0

    def test_search_similarity_scores(self, db_service, sample_embeddings):
        """Test that similarity scores are reasonable."""
        chunks = [f"Chunk {i}" for i in range(3)]
        metadata = [{"session_id": "session_1", "chunk_index": i} for i in range(3)]
        db_service.add_chunks(chunks, sample_embeddings[:3], metadata)

        results = db_service.search_chunks(sample_embeddings[0], k=3)

        # Similarity scores should be between 0 and 1
        assert all(0.0 <= r.similarity <= 1.0 for r in results)

    def test_search_with_filter_metadata(self, db_service, sample_embeddings):
        """Test searching with metadata filters."""
        # Add chunks from different sessions
        chunks = ["Chunk 1", "Chunk 2", "Chunk 3"]
        metadata = [
            {"session_id": "session_1", "chunk_index": 0},
            {"session_id": "session_2", "chunk_index": 0},
            {"session_id": "session_1", "chunk_index": 1}
        ]
        db_service.add_chunks(chunks, sample_embeddings[:3], metadata)

        # Search only session_1
        results = db_service.search_chunks(
            sample_embeddings[0],
            k=10,
            filter_metadata={"session_id": "session_1"}
        )

        assert all(r.session_id == "session_1" for r in results)
        assert len(results) == 2


class TestDeleteSessionChunks:
    """Test delete_session_chunks method."""

    def test_delete_session_chunks(self, db_service, sample_embeddings):
        """Test deleting chunks for a session."""
        # Add chunks from two sessions
        chunks = ["Chunk 1", "Chunk 2", "Chunk 3"]
        metadata = [
            {"session_id": "session_1", "chunk_index": 0},
            {"session_id": "session_2", "chunk_index": 0},
            {"session_id": "session_1", "chunk_index": 1}
        ]
        db_service.add_chunks(chunks, sample_embeddings[:3], metadata)

        # Delete session_1
        deleted_count = db_service.delete_session_chunks("session_1")

        assert deleted_count == 2

        # Verify only session_2 chunks remain
        stats = db_service.get_stats()
        assert stats["total_chunks"] == 1

    def test_delete_nonexistent_session(self, db_service):
        """Test deleting a session that doesn't exist."""
        deleted_count = db_service.delete_session_chunks("nonexistent")
        assert deleted_count == 0


class TestGetChunkById:
    """Test get_chunk_by_id method."""

    def test_get_existing_chunk(self, db_service, sample_embeddings):
        """Test getting an existing chunk by ID."""
        chunks = ["Test chunk"]
        metadata = [{"session_id": "session_1", "chunk_index": 0}]
        chunk_ids = db_service.add_chunks(chunks, sample_embeddings[:1], metadata)

        result = db_service.get_chunk_by_id(chunk_ids[0])

        assert result is not None
        assert result.chunk_id == chunk_ids[0]
        assert result.content == "Test chunk"
        assert result.session_id == "session_1"

    def test_get_nonexistent_chunk(self, db_service):
        """Test getting a chunk that doesn't exist."""
        result = db_service.get_chunk_by_id("nonexistent_id")
        assert result is None


class TestGetSessionChunks:
    """Test get_session_chunks method."""

    def test_get_session_chunks(self, db_service, sample_embeddings):
        """Test getting all chunks for a session."""
        chunks = ["Chunk 0", "Chunk 1", "Chunk 2"]
        metadata = [
            {"session_id": "session_1", "chunk_index": 2},
            {"session_id": "session_1", "chunk_index": 0},
            {"session_id": "session_1", "chunk_index": 1}
        ]
        db_service.add_chunks(chunks, sample_embeddings[:3], metadata)

        results = db_service.get_session_chunks("session_1")

        assert len(results) == 3
        # Should be sorted by chunk_index
        assert results[0].chunk_index == 0
        assert results[1].chunk_index == 1
        assert results[2].chunk_index == 2

    def test_get_session_chunks_empty(self, db_service):
        """Test getting chunks for a session with no chunks."""
        results = db_service.get_session_chunks("nonexistent")
        assert results == []


class TestGetStats:
    """Test get_stats method."""

    def test_get_stats_empty(self, db_service):
        """Test stats for empty database."""
        stats = db_service.get_stats()

        assert stats["total_chunks"] == 0
        assert stats["collection_name"] == "session_chunks"
        assert stats["persist_directory"] == db_service.persist_directory

    def test_get_stats_with_data(self, db_service, sample_embeddings):
        """Test stats with data in database."""
        chunks = [f"Chunk {i}" for i in range(5)]
        metadata = [{"session_id": "session_1", "chunk_index": i} for i in range(5)]
        db_service.add_chunks(chunks, sample_embeddings, metadata)

        stats = db_service.get_stats()
        assert stats["total_chunks"] == 5


class TestReset:
    """Test reset method."""

    def test_reset_clears_database(self, db_service, sample_embeddings):
        """Test that reset clears all data."""
        chunks = [f"Chunk {i}" for i in range(5)]
        metadata = [{"session_id": "session_1", "chunk_index": i} for i in range(5)]
        db_service.add_chunks(chunks, sample_embeddings, metadata)

        # Verify data exists
        stats = db_service.get_stats()
        assert stats["total_chunks"] == 5

        # Reset
        db_service.reset()

        # Verify data is gone
        stats = db_service.get_stats()
        assert stats["total_chunks"] == 0


class TestPersistence:
    """Test database persistence."""

    def test_data_persists_across_instances(self, temp_db_dir, sample_embeddings):
        """Test that data persists when recreating the service."""
        # Create first instance and add data
        service1 = VectorDBService(persist_directory=temp_db_dir)
        chunks = ["Test chunk"]
        metadata = [{"session_id": "session_1", "chunk_index": 0}]
        chunk_ids = service1.add_chunks(chunks, sample_embeddings[:1], metadata)

        # Create second instance with same directory
        service2 = VectorDBService(persist_directory=temp_db_dir)
        stats = service2.get_stats()

        # Data should still be there
        assert stats["total_chunks"] == 1

        # Should be able to retrieve the chunk
        result = service2.get_chunk_by_id(chunk_ids[0])
        assert result is not None
        assert result.content == "Test chunk"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_add_chunk_with_empty_content(self, db_service, sample_embeddings):
        """Test adding a chunk with empty content."""
        chunks = [""]
        metadata = [{"session_id": "session_1", "chunk_index": 0}]

        chunk_ids = db_service.add_chunks(chunks, sample_embeddings[:1], metadata)
        assert len(chunk_ids) == 1

    def test_add_chunk_with_very_long_content(self, db_service, sample_embeddings):
        """Test adding a chunk with very long content."""
        chunks = ["A" * 10000]  # 10k characters
        metadata = [{"session_id": "session_1", "chunk_index": 0}]

        chunk_ids = db_service.add_chunks(chunks, sample_embeddings[:1], metadata)
        assert len(chunk_ids) == 1

        result = db_service.get_chunk_by_id(chunk_ids[0])
        assert result is not None
        assert len(result.content) == 10000

    def test_add_chunk_with_unicode(self, db_service, sample_embeddings):
        """Test adding chunks with Unicode characters."""
        chunks = ["Hello 世界 🌍 café"]
        metadata = [{"session_id": "session_1", "chunk_index": 0}]

        chunk_ids = db_service.add_chunks(chunks, sample_embeddings[:1], metadata)
        result = db_service.get_chunk_by_id(chunk_ids[0])

        assert result is not None
        assert result.content == "Hello 世界 🌍 café"
