"""
Integration tests for SessionDiffService with real components.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from smart_fork.vector_db_service import VectorDBService
from smart_fork.session_registry import SessionRegistry, SessionMetadata
from smart_fork.embedding_service import EmbeddingService
from smart_fork.session_diff_service import SessionDiffService


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def vector_db(temp_storage):
    """Create a real VectorDBService."""
    db_path = Path(temp_storage) / "vector_db"
    return VectorDBService(persist_directory=str(db_path))


@pytest.fixture
def session_registry(temp_storage):
    """Create a real SessionRegistry."""
    registry_path = Path(temp_storage) / "session-registry.json"
    return SessionRegistry(registry_path=str(registry_path))


@pytest.fixture
def embedding_service(temp_storage):
    """Create a real EmbeddingService with test cache directory."""
    cache_dir = Path(temp_storage) / "embedding_cache"
    return EmbeddingService(cache_dir=str(cache_dir))


@pytest.fixture
def diff_service(vector_db, session_registry, embedding_service):
    """Create a SessionDiffService with real components."""
    return SessionDiffService(
        vector_db_service=vector_db,
        session_registry=session_registry,
        embedding_service=embedding_service,
        similarity_threshold=0.75
    )


class TestSessionDiffIntegration:
    """Integration tests for SessionDiffService."""

    def test_compare_real_sessions(
        self,
        diff_service,
        vector_db,
        session_registry,
        embedding_service
    ):
        """Test comparing real sessions with embeddings."""
        # Create session 1
        session_1_id = "test-session-1"
        texts_1 = [
            "I need to implement React hooks for state management.",
            "The component should use useState and useEffect hooks.",
            "We also need TypeScript type definitions for the props."
        ]

        # Generate embeddings and add to vector DB
        embeddings_1 = [embedding_service.embed_single(text) for text in texts_1]
        metadata_1 = [
            {
                "session_id": session_1_id,
                "chunk_index": i,
                "content": text
            }
            for i, text in enumerate(texts_1)
        ]

        chunk_ids_1 = vector_db.add_chunks(
            chunks=texts_1,
            embeddings=embeddings_1,
            metadata=metadata_1
        )

        # Register session 1
        session_registry.add_session(SessionMetadata(
            session_id=session_1_id,
            project="test-project",
            chunk_count=len(texts_1),
            message_count=len(texts_1)
        ))

        # Create session 2 with partial overlap
        session_2_id = "test-session-2"
        texts_2 = [
            "I need to implement React hooks for state management.",  # Same as session 1
            "The application uses Redux for global state instead.",   # Different
            "Python backend API is also needed for data fetching."    # Different
        ]

        embeddings_2 = [embedding_service.embed_single(text) for text in texts_2]
        metadata_2 = [
            {
                "session_id": session_2_id,
                "chunk_index": i,
                "content": text
            }
            for i, text in enumerate(texts_2)
        ]

        chunk_ids_2 = vector_db.add_chunks(
            chunks=texts_2,
            embeddings=embeddings_2,
            metadata=metadata_2
        )

        # Register session 2
        session_registry.add_session(SessionMetadata(
            session_id=session_2_id,
            project="test-project",
            chunk_count=len(texts_2),
            message_count=len(texts_2)
        ))

        # Compare sessions
        diff = diff_service.compare_sessions(session_1_id, session_2_id)

        # Assertions
        assert diff is not None
        assert diff.session_id_1 == session_1_id
        assert diff.session_id_2 == session_2_id

        # Should have moderate similarity (some overlap)
        assert 0.2 < diff.similarity_score < 0.8

        # Should detect the matching first message
        assert len(diff.common_messages) >= 1

        # Should have unique messages in both
        assert len(diff.unique_to_1) >= 1
        assert len(diff.unique_to_2) >= 1

        # Should extract topics
        assert len(diff.common_topics) >= 1
        assert "react" in diff.common_topics or "hooks" in diff.common_topics

    def test_compare_identical_real_sessions(
        self,
        diff_service,
        vector_db,
        session_registry,
        embedding_service
    ):
        """Test comparing two identical sessions."""
        # Create identical sessions
        texts = [
            "Implementing authentication with JWT tokens in a FastAPI application.",
            "The authentication flow includes login, logout, and token refresh.",
            "Database models are defined using SQLAlchemy ORM for user management."
        ]

        # Session 1
        session_1_id = "identical-session-1"
        embeddings_1 = [embedding_service.get_embedding(text) for text in texts]
        metadata_1 = [
            {"session_id": session_1_id, "chunk_index": i, "content": text}
            for i, text in enumerate(texts)
        ]
        vector_db.add_chunks(chunks=texts, embeddings=embeddings_1, metadata=metadata_1)
        session_registry.add_session(SessionMetadata(
            session_id=session_1_id,
            project="test-project",
            chunk_count=len(texts),
            message_count=len(texts)
        ))

        # Session 2 (identical)
        session_2_id = "identical-session-2"
        embeddings_2 = [embedding_service.get_embedding(text) for text in texts]
        metadata_2 = [
            {"session_id": session_2_id, "chunk_index": i, "content": text}
            for i, text in enumerate(texts)
        ]
        vector_db.add_chunks(chunks=texts, embeddings=embeddings_2, metadata=metadata_2)
        session_registry.add_session(SessionMetadata(
            session_id=session_2_id,
            project="test-project",
            chunk_count=len(texts),
            message_count=len(texts)
        ))

        # Compare
        diff = diff_service.compare_sessions(session_1_id, session_2_id)

        assert diff is not None
        # Should have very high similarity
        assert diff.similarity_score > 0.85
        # Most messages should match
        assert len(diff.common_messages) >= 2
        # Few or no unique messages
        assert len(diff.unique_to_1) <= 1
        assert len(diff.unique_to_2) <= 1

    def test_compare_different_real_sessions(
        self,
        diff_service,
        vector_db,
        session_registry,
        embedding_service
    ):
        """Test comparing completely different sessions."""
        # Session 1: React frontend
        session_1_id = "frontend-session"
        texts_1 = [
            "Building a React application with TypeScript and Material-UI components.",
            "The frontend uses Redux Toolkit for state management and API calls.",
            "Component testing is done with Jest and React Testing Library."
        ]
        embeddings_1 = [embedding_service.embed_single(text) for text in texts_1]
        metadata_1 = [
            {"session_id": session_1_id, "chunk_index": i, "content": text}
            for i, text in enumerate(texts_1)
        ]
        vector_db.add_chunks(chunks=texts_1, embeddings=embeddings_1, metadata=metadata_1)
        session_registry.add_session(SessionMetadata(
            session_id=session_1_id,
            project="test-project",
            chunk_count=len(texts_1),
            message_count=len(texts_1)
        ))

        # Session 2: Python backend
        session_2_id = "backend-session"
        texts_2 = [
            "Creating a Python FastAPI backend with PostgreSQL database integration.",
            "The API uses SQLAlchemy for database operations and Alembic for migrations.",
            "Authentication is implemented with OAuth2 and password hashing using bcrypt."
        ]
        embeddings_2 = [embedding_service.embed_single(text) for text in texts_2]
        metadata_2 = [
            {"session_id": session_2_id, "chunk_index": i, "content": text}
            for i, text in enumerate(texts_2)
        ]
        vector_db.add_chunks(chunks=texts_2, embeddings=embeddings_2, metadata=metadata_2)
        session_registry.add_session(SessionMetadata(
            session_id=session_2_id,
            project="test-project",
            chunk_count=len(texts_2),
            message_count=len(texts_2)
        ))

        # Compare
        diff = diff_service.compare_sessions(session_1_id, session_2_id)

        assert diff is not None
        # Should have low similarity (different topics)
        assert diff.similarity_score < 0.6
        # Should have mostly unique content
        assert len(diff.unique_to_1) >= 2
        assert len(diff.unique_to_2) >= 2
        # Different technology stacks
        assert len(diff.topics_1) > 0
        assert len(diff.topics_2) > 0

    def test_get_message_content_real(
        self,
        diff_service,
        vector_db,
        session_registry,
        embedding_service
    ):
        """Test getting real message content."""
        session_id = "content-test-session"
        texts = [
            "First message with some content.",
            "Second message with different content.",
            "Third message with more information."
        ]

        embeddings = [embedding_service.embed_single(text) for text in texts]
        metadata = [
            {"session_id": session_id, "chunk_index": i, "content": text}
            for i, text in enumerate(texts)
        ]
        vector_db.add_chunks(chunks=texts, embeddings=embeddings, metadata=metadata)
        session_registry.add_session(SessionMetadata(
            session_id=session_id,
            project="test-project",
            chunk_count=len(texts),
            message_count=len(texts)
        ))

        # Get specific messages
        messages = diff_service.get_message_content(session_id, [0, 2], max_length=100)

        assert len(messages) == 2
        assert "First message" in messages[0]
        assert "Third message" in messages[1]

    def test_topic_extraction_real(self, diff_service):
        """Test topic extraction with real text."""
        texts = [
            "I'm working on a React application using TypeScript and Redux.",
            "The React components use hooks like useState and useEffect.",
            "TypeScript provides type safety and better developer experience with React."
        ]

        topics = diff_service._extract_topics(texts, top_k=8)

        # Should extract key technologies
        assert len(topics) > 0
        # Common terms should appear
        tech_terms = ["react", "typescript", "redux", "hooks"]
        found_terms = [t for t in tech_terms if t in topics]
        assert len(found_terms) >= 2  # At least 2 tech terms should be found

    def test_diff_to_dict_real(
        self,
        diff_service,
        vector_db,
        session_registry,
        embedding_service
    ):
        """Test converting real diff to dictionary."""
        # Create simple sessions
        session_1_id = "dict-test-1"
        session_2_id = "dict-test-2"

        texts_1 = ["Testing the to_dict conversion method with real session data here."]
        texts_2 = ["Different content for the second session used in dictionary test."]

        # Add session 1
        embeddings_1 = [embedding_service.embed_single(text) for text in texts_1]
        metadata_1 = [{"session_id": session_1_id, "chunk_index": i, "content": text} for i, text in enumerate(texts_1)]
        vector_db.add_chunks(chunks=texts_1, embeddings=embeddings_1, metadata=metadata_1)
        session_registry.add_session(SessionMetadata(
            session_id=session_1_id, project="test", chunk_count=1, message_count=1
        ))

        # Add session 2
        embeddings_2 = [embedding_service.embed_single(text) for text in texts_2]
        metadata_2 = [{"session_id": session_2_id, "chunk_index": i, "content": text} for i, text in enumerate(texts_2)]
        vector_db.add_chunks(chunks=texts_2, embeddings=embeddings_2, metadata=metadata_2)
        session_registry.add_session(SessionMetadata(
            session_id=session_2_id, project="test", chunk_count=1, message_count=1
        ))

        # Compare and convert to dict
        diff = diff_service.compare_sessions(session_1_id, session_2_id)
        assert diff is not None

        result_dict = diff.to_dict()

        # Verify dict structure
        assert "session_id_1" in result_dict
        assert "session_id_2" in result_dict
        assert "similarity_score" in result_dict
        assert "common_messages" in result_dict
        assert "unique_to_1" in result_dict
        assert "unique_to_2" in result_dict
        assert "topics_1" in result_dict
        assert "topics_2" in result_dict
        assert "common_topics" in result_dict

        assert result_dict["session_id_1"] == session_1_id
        assert result_dict["session_id_2"] == session_2_id
        assert isinstance(result_dict["similarity_score"], float)
