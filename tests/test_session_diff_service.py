"""
Tests for SessionDiffService.
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock
from smart_fork.session_diff_service import (
    SessionDiffService,
    SessionDiff,
    MessageMatch
)


@pytest.fixture
def mock_vector_db():
    """Create a mock VectorDBService."""
    vector_db = Mock()
    vector_db.collection = Mock()
    return vector_db


@pytest.fixture
def mock_session_registry():
    """Create a mock SessionRegistry."""
    registry = Mock()
    return registry


@pytest.fixture
def mock_embedding_service():
    """Create a mock EmbeddingService."""
    embedding_service = Mock()
    return embedding_service


@pytest.fixture
def diff_service(mock_vector_db, mock_session_registry, mock_embedding_service):
    """Create a SessionDiffService instance with mocks."""
    return SessionDiffService(
        vector_db_service=mock_vector_db,
        session_registry=mock_session_registry,
        embedding_service=mock_embedding_service,
        similarity_threshold=0.75,
        min_message_length=20
    )


class TestSessionDiffService:
    """Tests for SessionDiffService."""

    def test_initialization(self, diff_service):
        """Test service initialization."""
        assert diff_service.similarity_threshold == 0.75
        assert diff_service.min_message_length == 20

    def test_compare_sessions_not_found(self, diff_service, mock_session_registry):
        """Test comparing sessions when one doesn't exist."""
        mock_session_registry.get_session.return_value = None

        result = diff_service.compare_sessions("session-1", "session-2")

        assert result is None

    def test_compare_sessions_no_chunks(self, diff_service, mock_session_registry, mock_vector_db):
        """Test comparing sessions when one has no chunks."""
        # Sessions exist
        mock_session_1 = Mock()
        mock_session_2 = Mock()
        mock_session_registry.get_session.side_effect = [mock_session_1, mock_session_2]

        # But no chunks
        mock_vector_db.get_session_chunks.return_value = []

        result = diff_service.compare_sessions("session-1", "session-2")

        assert result is None

    def test_compare_identical_sessions(self, diff_service, mock_session_registry, mock_vector_db):
        """Test comparing two identical sessions."""
        # Setup sessions
        mock_session_1 = Mock()
        mock_session_2 = Mock()
        mock_session_registry.get_session.side_effect = [mock_session_1, mock_session_2]

        # Create identical chunks
        chunk_1 = Mock()
        chunk_1.chunk_id = "chunk-1"
        chunk_1.content = "This is a test message about React components and state management."

        chunk_2 = Mock()
        chunk_2.chunk_id = "chunk-2"
        chunk_2.content = "This is a test message about React components and state management."

        mock_vector_db.get_session_chunks.side_effect = [[chunk_1], [chunk_2]]

        # Create identical embeddings
        embedding = np.array([1.0, 0.0, 0.0])
        mock_vector_db.collection.get.return_value = {
            "embeddings": [[1.0, 0.0, 0.0]]
        }

        result = diff_service.compare_sessions("session-1", "session-2")

        assert result is not None
        assert result.similarity_score > 0.9  # Should be very high
        assert len(result.common_messages) == 1
        assert len(result.unique_to_1) == 0
        assert len(result.unique_to_2) == 0

    def test_compare_completely_different_sessions(self, diff_service, mock_session_registry, mock_vector_db):
        """Test comparing two completely different sessions."""
        # Setup sessions
        mock_session_1 = Mock()
        mock_session_2 = Mock()
        mock_session_registry.get_session.side_effect = [mock_session_1, mock_session_2]

        # Create different chunks
        chunk_1 = Mock()
        chunk_1.chunk_id = "chunk-1"
        chunk_1.content = "This message discusses React frontend development and hooks."

        chunk_2 = Mock()
        chunk_2.chunk_id = "chunk-2"
        chunk_2.content = "This message discusses Python backend API development and databases."

        mock_vector_db.get_session_chunks.side_effect = [[chunk_1], [chunk_2]]

        # Create orthogonal embeddings (no similarity)
        mock_vector_db.collection.get.side_effect = [
            {"embeddings": [[1.0, 0.0, 0.0]]},  # First session
            {"embeddings": [[0.0, 1.0, 0.0]]}   # Second session (orthogonal)
        ]

        result = diff_service.compare_sessions("session-1", "session-2")

        assert result is not None
        assert result.similarity_score < 0.5  # Should be low
        assert len(result.common_messages) == 0  # No matches above threshold
        assert len(result.unique_to_1) == 1
        assert len(result.unique_to_2) == 1

    def test_compare_partial_overlap(self, diff_service, mock_session_registry, mock_vector_db):
        """Test comparing sessions with partial overlap."""
        # Setup sessions
        mock_session_1 = Mock()
        mock_session_2 = Mock()
        mock_session_registry.get_session.side_effect = [mock_session_1, mock_session_2]

        # Session 1: 3 chunks (2 unique, 1 shared)
        chunk_1a = Mock()
        chunk_1a.chunk_id = "chunk-1a"
        chunk_1a.content = "Unique to session 1 - discussing authentication implementation details."

        chunk_1b = Mock()
        chunk_1b.chunk_id = "chunk-1b"
        chunk_1b.content = "Shared content about React state management using hooks and context."

        chunk_1c = Mock()
        chunk_1c.chunk_id = "chunk-1c"
        chunk_1c.content = "Another unique message specific to session 1 about testing strategies."

        # Session 2: 2 chunks (1 unique, 1 shared)
        chunk_2a = Mock()
        chunk_2a.chunk_id = "chunk-2a"
        chunk_2a.content = "Shared content about React state management using hooks and context."

        chunk_2b = Mock()
        chunk_2b.chunk_id = "chunk-2b"
        chunk_2b.content = "Unique to session 2 - discussing database schema design patterns."

        mock_vector_db.get_session_chunks.side_effect = [
            [chunk_1a, chunk_1b, chunk_1c],
            [chunk_2a, chunk_2b]
        ]

        # Setup embeddings - shared chunks have high similarity
        # Chunk order: 1a, 1b, 1c from session 1, then 2a, 2b from session 2
        def get_embeddings_side_effect(ids, include):
            if "chunk-1a" in ids:
                # Session 1 embeddings
                return {
                    "embeddings": [
                        [1.0, 0.0, 0.0],  # 1a - unique
                        [0.0, 1.0, 0.0],  # 1b - shared
                        [0.0, 0.0, 1.0]   # 1c - unique
                    ]
                }
            else:
                # Session 2 embeddings
                return {
                    "embeddings": [
                        [0.0, 1.0, 0.0],  # 2a - shared (matches 1b)
                        [1.0, 1.0, 0.0]   # 2b - unique
                    ]
                }

        mock_vector_db.collection.get.side_effect = get_embeddings_side_effect

        result = diff_service.compare_sessions("session-1", "session-2")

        assert result is not None
        # Should have moderate similarity (some overlap)
        assert 0.3 < result.similarity_score < 0.7
        assert len(result.common_messages) == 1  # 1b matches 2a
        assert len(result.unique_to_1) == 2  # 1a and 1c
        assert len(result.unique_to_2) == 1  # 2b

    def test_extract_topics(self, diff_service):
        """Test topic extraction from text."""
        texts = [
            "I need to implement React hooks for state management.",
            "The React application uses TypeScript for type safety.",
            "We're building a REST API with FastAPI and PostgreSQL."
        ]

        topics = diff_service._extract_topics(texts, top_k=5)

        assert len(topics) <= 5
        assert "react" in topics
        # Stop words should be filtered
        assert "the" not in topics
        assert "for" not in topics

    def test_extract_topics_empty(self, diff_service):
        """Test topic extraction with empty input."""
        topics = diff_service._extract_topics([], top_k=5)
        assert topics == []

    def test_extract_topics_filters_stop_words(self, diff_service):
        """Test that stop words are filtered from topics."""
        texts = [
            "The application needs to have proper authentication and authorization.",
            "We should implement the security features with JWT tokens."
        ]

        topics = diff_service._extract_topics(texts, top_k=10)

        # Common stop words should not appear
        stop_words = ["the", "to", "have", "with", "and", "should"]
        for word in stop_words:
            assert word not in topics

    def test_get_message_content(self, diff_service, mock_vector_db):
        """Test getting message content for specific indices."""
        # Create mock chunks
        chunk_1 = Mock()
        chunk_1.content = "First message content"

        chunk_2 = Mock()
        chunk_2.content = "Second message content"

        chunk_3 = Mock()
        chunk_3.content = "Third message content"

        mock_vector_db.get_session_chunks.return_value = [chunk_1, chunk_2, chunk_3]

        messages = diff_service.get_message_content("session-1", [0, 2], max_length=100)

        assert len(messages) == 2
        assert messages[0] == "First message content"
        assert messages[1] == "Third message content"

    def test_get_message_content_truncation(self, diff_service, mock_vector_db):
        """Test message content truncation."""
        chunk = Mock()
        chunk.content = "A" * 300  # Long content

        mock_vector_db.get_session_chunks.return_value = [chunk]

        messages = diff_service.get_message_content("session-1", [0], max_length=50)

        assert len(messages) == 1
        assert len(messages[0]) == 53  # 50 + "..."
        assert messages[0].endswith("...")

    def test_get_message_content_invalid_indices(self, diff_service, mock_vector_db):
        """Test handling of invalid message indices."""
        chunk = Mock()
        chunk.content = "Valid content"

        mock_vector_db.get_session_chunks.return_value = [chunk]

        # Request indices outside range
        messages = diff_service.get_message_content("session-1", [0, 5, 10], max_length=100)

        # Should only return valid index (0)
        assert len(messages) == 1
        assert messages[0] == "Valid content"

    def test_get_message_content_no_chunks(self, diff_service, mock_vector_db):
        """Test getting message content when session has no chunks."""
        mock_vector_db.get_session_chunks.return_value = []

        messages = diff_service.get_message_content("session-1", [0, 1], max_length=100)

        assert messages == []

    def test_similarity_threshold_filtering(self, diff_service, mock_session_registry, mock_vector_db):
        """Test that similarity threshold filters matches correctly."""
        # Setup sessions
        mock_session_1 = Mock()
        mock_session_2 = Mock()
        mock_session_registry.get_session.side_effect = [mock_session_1, mock_session_2]

        # Create chunks
        chunk_1 = Mock()
        chunk_1.chunk_id = "chunk-1"
        chunk_1.content = "Message about React component architecture and design patterns today."

        chunk_2 = Mock()
        chunk_2.chunk_id = "chunk-2"
        chunk_2.content = "Different message about Python backend services and API development."

        mock_vector_db.get_session_chunks.side_effect = [[chunk_1], [chunk_2]]

        # Create embeddings with similarity just below threshold
        # Using angle that gives ~0.7 similarity (below 0.75 threshold)
        mock_vector_db.collection.get.side_effect = [
            {"embeddings": [[1.0, 0.0, 0.0]]},
            {"embeddings": [[0.7, 0.714, 0.0]]}  # ~0.7 cosine similarity
        ]

        result = diff_service.compare_sessions("session-1", "session-2")

        assert result is not None
        # Should not match due to threshold
        assert len(result.common_messages) == 0
        assert len(result.unique_to_1) == 1
        assert len(result.unique_to_2) == 1

    def test_min_message_length_filtering(self, diff_service, mock_session_registry, mock_vector_db):
        """Test that messages below minimum length are filtered."""
        # Setup sessions
        mock_session_1 = Mock()
        mock_session_2 = Mock()
        mock_session_registry.get_session.side_effect = [mock_session_1, mock_session_2]

        # Create chunks - one too short
        chunk_1 = Mock()
        chunk_1.chunk_id = "chunk-1"
        chunk_1.content = "Short"  # Too short (< 20 chars)

        chunk_2 = Mock()
        chunk_2.chunk_id = "chunk-2"
        chunk_2.content = "This is a longer message that meets the minimum length requirement."

        mock_vector_db.get_session_chunks.side_effect = [[chunk_1], [chunk_2]]

        # Even with identical embeddings, short message should be filtered
        mock_vector_db.collection.get.return_value = {
            "embeddings": [[1.0, 0.0, 0.0]]
        }

        result = diff_service.compare_sessions("session-1", "session-2")

        assert result is not None
        assert len(result.common_messages) == 0  # Filtered due to length

    def test_session_diff_to_dict(self):
        """Test SessionDiff to_dict conversion."""
        match = MessageMatch(
            session_1_index=0,
            session_2_index=1,
            similarity=0.85,
            content_1="First message content here",
            content_2="Second message content here"
        )

        diff = SessionDiff(
            session_id_1="session-1",
            session_id_2="session-2",
            similarity_score=0.75,
            common_messages=[match],
            unique_to_1=[2, 3],
            unique_to_2=[4],
            topics_1=["react", "typescript"],
            topics_2=["python", "fastapi"],
            common_topics=["testing"]
        )

        result = diff.to_dict()

        assert result["session_id_1"] == "session-1"
        assert result["session_id_2"] == "session-2"
        assert result["similarity_score"] == 0.75
        assert len(result["common_messages"]) == 1
        assert result["unique_to_1"] == [2, 3]
        assert result["unique_to_2"] == [4]
        assert result["topics_1"] == ["react", "typescript"]
        assert result["topics_2"] == ["python", "fastapi"]
        assert result["common_topics"] == ["testing"]

    def test_topic_overlap_calculation(self, diff_service, mock_session_registry, mock_vector_db):
        """Test that topic overlap contributes to similarity score."""
        # Setup sessions
        mock_session_1 = Mock()
        mock_session_2 = Mock()
        mock_session_registry.get_session.side_effect = [mock_session_1, mock_session_2]

        # Create chunks with overlapping topics
        chunk_1 = Mock()
        chunk_1.chunk_id = "chunk-1"
        chunk_1.content = "Discussion about React, TypeScript, and Jest testing frameworks implementation."

        chunk_2 = Mock()
        chunk_2.chunk_id = "chunk-2"
        chunk_2.content = "Exploring React, TypeScript, and Pytest with different implementation approaches."

        mock_vector_db.get_session_chunks.side_effect = [[chunk_1], [chunk_2]]

        # Use embeddings with moderate similarity
        mock_vector_db.collection.get.side_effect = [
            {"embeddings": [[1.0, 0.0, 0.0]]},
            {"embeddings": [[0.8, 0.6, 0.0]]}  # Moderate similarity
        ]

        result = diff_service.compare_sessions("session-1", "session-2")

        assert result is not None
        # Should have common topics (react, typescript)
        assert len(result.common_topics) >= 2
        assert "react" in result.common_topics or "typescript" in result.common_topics
        # Similarity score includes 30% topic overlap
        assert result.similarity_score > 0.0

    def test_custom_threshold_and_min_length(self, mock_vector_db, mock_session_registry, mock_embedding_service):
        """Test service with custom threshold and minimum length."""
        service = SessionDiffService(
            vector_db_service=mock_vector_db,
            session_registry=mock_session_registry,
            embedding_service=mock_embedding_service,
            similarity_threshold=0.9,
            min_message_length=50
        )

        assert service.similarity_threshold == 0.9
        assert service.min_message_length == 50
