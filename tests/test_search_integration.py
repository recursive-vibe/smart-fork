"""
Integration tests for end-to-end search flow.

Tests the complete search pipeline:
1. Creating test sessions
2. Indexing into ChromaDB
3. Running search queries
4. Verifying ranking order
5. Testing memory boost effects
6. Testing recency factor effects
7. Performance benchmarks (<3s target)
"""

import os
import pytest
import tempfile
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

from smart_fork.session_parser import SessionParser, SessionMessage
from smart_fork.chunking_service import ChunkingService
from smart_fork.embedding_service import EmbeddingService
from smart_fork.vector_db_service import VectorDBService
from smart_fork.scoring_service import ScoringService
from smart_fork.session_registry import SessionRegistry
from smart_fork.search_service import SearchService


class TestSearchIntegration:
    """Integration tests for the complete search flow."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test data."""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def test_sessions(self):
        """Create 10 sample test sessions with varying characteristics."""
        now = datetime.now()

        sessions = [
            # Session 1: Recent, Python debugging (high relevance for Python queries)
            {
                "session_id": "session_001",
                "project": "python-app",
                "created_at": (now - timedelta(days=2)).isoformat(),
                "messages": [
                    SessionMessage(
                        role="user",
                        content="I'm getting a TypeError in my Python script when processing data",
                        timestamp=(now - timedelta(days=2)).isoformat()
                    ),
                    SessionMessage(
                        role="assistant",
                        content="Let me help debug that. This is a WORKING_SOLUTION: Check your data types. The pattern for fixing type errors is to validate inputs first.",
                        timestamp=(now - timedelta(days=2)).isoformat()
                    ),
                    SessionMessage(
                        role="user",
                        content="Thanks, that fixed it!",
                        timestamp=(now - timedelta(days=2)).isoformat()
                    )
                ],
                "tags": ["python", "debugging", "types"]
            },

            # Session 2: Old session, JavaScript (low recency)
            {
                "session_id": "session_002",
                "project": "js-app",
                "created_at": (now - timedelta(days=90)).isoformat(),
                "messages": [
                    SessionMessage(
                        role="user",
                        content="How do I implement async/await in JavaScript?",
                        timestamp=(now - timedelta(days=90)).isoformat()
                    ),
                    SessionMessage(
                        role="assistant",
                        content="Here's the design pattern for async operations in JavaScript using promises and async/await.",
                        timestamp=(now - timedelta(days=90)).isoformat()
                    )
                ],
                "tags": ["javascript", "async"]
            },

            # Session 3: Very recent, React components (very high recency)
            {
                "session_id": "session_003",
                "project": "react-app",
                "created_at": (now - timedelta(hours=12)).isoformat(),
                "messages": [
                    SessionMessage(
                        role="user",
                        content="How do I create a reusable React component for form validation?",
                        timestamp=(now - timedelta(hours=12)).isoformat()
                    ),
                    SessionMessage(
                        role="assistant",
                        content="Here's a PATTERN for creating reusable form components with validation hooks. This is a WORKING_SOLUTION that handles all edge cases.",
                        timestamp=(now - timedelta(hours=12)).isoformat()
                    )
                ],
                "tags": ["react", "components", "validation"]
            },

            # Session 4: Moderate age, database queries
            {
                "session_id": "session_004",
                "project": "backend-api",
                "created_at": (now - timedelta(days=15)).isoformat(),
                "messages": [
                    SessionMessage(
                        role="user",
                        content="What's the best approach for optimizing database queries?",
                        timestamp=(now - timedelta(days=15)).isoformat()
                    ),
                    SessionMessage(
                        role="assistant",
                        content="The strategy for query optimization involves indexing and query planning. Here's a tested approach that works well.",
                        timestamp=(now - timedelta(days=15)).isoformat()
                    )
                ],
                "tags": ["database", "performance"]
            },

            # Session 5: Old, machine learning (low recency, but PATTERN marker)
            {
                "session_id": "session_005",
                "project": "ml-project",
                "created_at": (now - timedelta(days=60)).isoformat(),
                "messages": [
                    SessionMessage(
                        role="user",
                        content="How do I implement a neural network for classification?",
                        timestamp=(now - timedelta(days=60)).isoformat()
                    ),
                    SessionMessage(
                        role="assistant",
                        content="Here's the architecture PATTERN for building classification models. This design pattern is widely used in production systems.",
                        timestamp=(now - timedelta(days=60)).isoformat()
                    )
                ],
                "tags": ["machine-learning", "neural-networks"]
            },

            # Session 6: Recent, API design (WAITING marker)
            {
                "session_id": "session_006",
                "project": "rest-api",
                "created_at": (now - timedelta(days=5)).isoformat(),
                "messages": [
                    SessionMessage(
                        role="user",
                        content="I need to design a REST API for user management",
                        timestamp=(now - timedelta(days=5)).isoformat()
                    ),
                    SessionMessage(
                        role="assistant",
                        content="Here's the approach for RESTful design. WAITING on your decision about authentication method before proceeding.",
                        timestamp=(now - timedelta(days=5)).isoformat()
                    )
                ],
                "tags": ["api", "rest", "design"]
            },

            # Session 7: Moderate age, testing strategies
            {
                "session_id": "session_007",
                "project": "test-suite",
                "created_at": (now - timedelta(days=20)).isoformat(),
                "messages": [
                    SessionMessage(
                        role="user",
                        content="What's the best strategy for writing integration tests?",
                        timestamp=(now - timedelta(days=20)).isoformat()
                    ),
                    SessionMessage(
                        role="assistant",
                        content="The testing strategy involves fixtures and mocks. Here's a comprehensive approach with examples.",
                        timestamp=(now - timedelta(days=20)).isoformat()
                    )
                ],
                "tags": ["testing", "integration"]
            },

            # Session 8: Very recent, performance optimization (multiple memory markers)
            {
                "session_id": "session_008",
                "project": "optimization",
                "created_at": (now - timedelta(days=1)).isoformat(),
                "messages": [
                    SessionMessage(
                        role="user",
                        content="My application is running slowly, how can I optimize it?",
                        timestamp=(now - timedelta(days=1)).isoformat()
                    ),
                    SessionMessage(
                        role="assistant",
                        content="Here's a WORKING_SOLUTION for performance optimization. The PATTERN involves profiling first, then optimizing bottlenecks. This is a tested and verified approach.",
                        timestamp=(now - timedelta(days=1)).isoformat()
                    )
                ],
                "tags": ["performance", "optimization"]
            },

            # Session 9: Old, Docker setup
            {
                "session_id": "session_009",
                "project": "devops",
                "created_at": (now - timedelta(days=45)).isoformat(),
                "messages": [
                    SessionMessage(
                        role="user",
                        content="How do I containerize my application with Docker?",
                        timestamp=(now - timedelta(days=45)).isoformat()
                    ),
                    SessionMessage(
                        role="assistant",
                        content="Here's the approach for Docker containerization with multi-stage builds.",
                        timestamp=(now - timedelta(days=45)).isoformat()
                    )
                ],
                "tags": ["docker", "devops"]
            },

            # Session 10: Recent, security practices (PATTERN + WORKING_SOLUTION)
            {
                "session_id": "session_010",
                "project": "security",
                "created_at": (now - timedelta(days=3)).isoformat(),
                "messages": [
                    SessionMessage(
                        role="user",
                        content="What are the best security practices for web applications?",
                        timestamp=(now - timedelta(days=3)).isoformat()
                    ),
                    SessionMessage(
                        role="assistant",
                        content="Here's a comprehensive PATTERN for web security. This WORKING_SOLUTION includes input validation, CSRF protection, and secure authentication.",
                        timestamp=(now - timedelta(days=3)).isoformat()
                    )
                ],
                "tags": ["security", "web", "best-practices"]
            }
        ]

        return sessions

    @pytest.fixture
    def services(self, temp_dir):
        """Initialize all services for testing."""
        embedding_service = EmbeddingService()
        vector_db_service = VectorDBService(storage_path=temp_dir)
        scoring_service = ScoringService()
        registry_path = os.path.join(temp_dir, "session-registry.json")
        session_registry = SessionRegistry(registry_path=registry_path)
        search_service = SearchService(
            embedding_service=embedding_service,
            vector_db_service=vector_db_service,
            scoring_service=scoring_service,
            session_registry=session_registry
        )

        return {
            "embedding": embedding_service,
            "vector_db": vector_db_service,
            "scoring": scoring_service,
            "registry": session_registry,
            "search": search_service,
            "chunking": ChunkingService()
        }

    def test_index_sessions(self, test_sessions, services):
        """Test indexing all test sessions into ChromaDB."""
        chunking = services["chunking"]
        embedding = services["embedding"]
        vector_db = services["vector_db"]
        registry = services["registry"]

        total_chunks = 0

        for session in test_sessions:
            # Chunk messages
            chunks = chunking.chunk_messages(session["messages"])

            # Add to registry
            registry.add_session(
                session_id=session["session_id"],
                project=session["project"],
                created_at=session["created_at"],
                message_count=len(session["messages"]),
                chunk_count=len(chunks),
                tags=session["tags"]
            )

            # Generate embeddings
            texts = [chunk.text for chunk in chunks]
            embeddings = embedding.embed_texts(texts)

            # Store in vector database
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                vector_db.add_chunks(
                    embeddings=[emb],
                    texts=[chunk.text],
                    metadatas=[{
                        "session_id": session["session_id"],
                        "project": session["project"],
                        "chunk_index": i,
                        "memory_types": ",".join(chunk.memory_types) if chunk.memory_types else ""
                    }]
                )

            total_chunks += len(chunks)

        # Verify indexing
        stats = vector_db.get_stats()
        assert stats["total_chunks"] == total_chunks, f"Expected {total_chunks} chunks, got {stats['total_chunks']}"
        assert stats["total_chunks"] > 0, "No chunks were indexed"

        registry_stats = registry.get_stats()
        assert registry_stats["total_sessions"] == 10, f"Expected 10 sessions, got {registry_stats['total_sessions']}"

    def test_search_ranking_order(self, test_sessions, services):
        """Test that search results are ranked correctly."""
        # First, index all sessions
        self.test_index_sessions(test_sessions, services)

        search = services["search"]

        # Query: "Python debugging TypeError"
        # Expected: session_001 should rank highly (recent + exact match + WORKING_SOLUTION)
        results = search.search("Python debugging TypeError", top_n_sessions=5)

        assert len(results) > 0, "No search results returned"

        # The top result should be session_001 or another highly relevant session
        top_result = results[0]
        assert top_result.session_id in ["session_001", "session_003", "session_008", "session_010"], \
            f"Expected highly relevant session, got {top_result.session_id}"

        # Verify scores are in descending order
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True), "Results are not sorted by score"

    def test_search_performance(self, test_sessions, services):
        """Test that search completes within 3-second target."""
        # Index all sessions
        self.test_index_sessions(test_sessions, services)

        search = services["search"]

        # Run search and measure time
        start_time = time.time()
        results = search.search("How do I optimize database performance?", top_n_sessions=5)
        elapsed_time = time.time() - start_time

        assert elapsed_time < 3.0, f"Search took {elapsed_time:.2f}s, exceeds 3s target"
        assert len(results) > 0, "No search results returned"

    def test_memory_boost_affects_ranking(self, test_sessions, services):
        """Test that memory markers boost session rankings."""
        # Index all sessions
        self.test_index_sessions(test_sessions, services)

        search = services["search"]

        # Query for patterns/solutions
        # Sessions with PATTERN and WORKING_SOLUTION markers should rank higher
        results = search.search("design pattern for optimization", top_n_sessions=5)

        assert len(results) > 0, "No search results returned"

        # Check that sessions with memory markers are present in top results
        top_session_ids = [r.session_id for r in results[:3]]

        # Sessions 003, 005, 008, 010 have memory markers
        memory_sessions = {"session_003", "session_005", "session_008", "session_010"}
        top_with_memory = len(memory_sessions.intersection(set(top_session_ids)))

        # At least one session with memory markers should be in top 3
        assert top_with_memory >= 1, "No sessions with memory markers in top 3 results"

    def test_recency_factor_affects_ranking(self, test_sessions, services):
        """Test that recent sessions rank higher than old ones."""
        # Index all sessions
        self.test_index_sessions(test_sessions, services)

        search = services["search"]

        # Query that matches both recent and old sessions
        results = search.search("design pattern architecture", top_n_sessions=5)

        assert len(results) >= 2, "Need at least 2 results to compare recency"

        # Check score breakdown for top results
        # Recent sessions (1-5 days old) should have higher recency scores than old ones (60-90 days)
        recent_sessions = {"session_001", "session_003", "session_006", "session_008", "session_010"}
        old_sessions = {"session_002", "session_005", "session_009"}

        # Find recent and old sessions in results
        recent_result = None
        old_result = None

        for result in results:
            if result.session_id in recent_sessions and recent_result is None:
                recent_result = result
            if result.session_id in old_sessions and old_result is None:
                old_result = result

        # If we have both types, verify recency scoring works
        if recent_result and old_result:
            # Recent sessions should have higher recency component
            assert recent_result.score_breakdown["recency"] > old_result.score_breakdown["recency"], \
                f"Recent session recency ({recent_result.score_breakdown['recency']:.3f}) not higher than old session ({old_result.score_breakdown['recency']:.3f})"

    def test_search_with_no_results(self, services):
        """Test search with query that matches nothing."""
        # Don't index anything, just search
        search = services["search"]

        results = search.search("xyzabc123 nonexistent query", top_n_sessions=5)

        # Should return empty list
        assert len(results) == 0, f"Expected no results, got {len(results)}"

    def test_search_multiple_queries(self, test_sessions, services):
        """Test multiple different search queries."""
        # Index all sessions
        self.test_index_sessions(test_sessions, services)

        search = services["search"]

        queries = [
            "React components validation",  # Should match session_003
            "database optimization",  # Should match session_004
            "security best practices",  # Should match session_010
            "testing strategy",  # Should match session_007
        ]

        for query in queries:
            results = search.search(query, top_n_sessions=3)
            assert len(results) > 0, f"No results for query: {query}"

            # Each query should return relevant results
            assert results[0].score > 0, f"Top result score is 0 for query: {query}"


class TestSearchIntegrationEdgeCases:
    """Edge case tests for search integration."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test data."""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def services(self, temp_dir):
        """Initialize all services for testing."""
        embedding_service = EmbeddingService()
        vector_db_service = VectorDBService(storage_path=temp_dir)
        scoring_service = ScoringService()
        registry_path = os.path.join(temp_dir, "session-registry.json")
        session_registry = SessionRegistry(registry_path=registry_path)
        search_service = SearchService(
            embedding_service=embedding_service,
            vector_db_service=vector_db_service,
            scoring_service=scoring_service,
            session_registry=session_registry
        )

        return {
            "search": search_service,
            "vector_db": vector_db_service,
            "registry": session_registry
        }

    def test_search_empty_database(self, services):
        """Test search on empty database."""
        search = services["search"]

        results = search.search("test query", top_n_sessions=5)

        assert len(results) == 0, "Expected no results from empty database"

    def test_search_with_metadata_filter(self, services):
        """Test search with metadata filtering."""
        # This is a placeholder - metadata filtering is in the implementation
        search = services["search"]

        # Search with project filter
        results = search.search("test query", top_n_sessions=5, metadata_filter={"project": "nonexistent"})

        # Should return empty (no sessions indexed)
        assert len(results) == 0, "Expected no results with filter"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
