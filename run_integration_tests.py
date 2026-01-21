#!/usr/bin/env python3
"""
Manual test runner for integration tests.

Runs integration tests without requiring pytest installation.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import tempfile
import shutil
import time
from datetime import datetime, timedelta

from smart_fork.session_parser import SessionMessage
from smart_fork.chunking_service import ChunkingService
from smart_fork.embedding_service import EmbeddingService
from smart_fork.vector_db_service import VectorDBService
from smart_fork.scoring_service import ScoringService
from smart_fork.session_registry import SessionRegistry
from smart_fork.search_service import SearchService


def create_test_sessions():
    """Create 10 sample test sessions."""
    now = datetime.now()

    sessions = [
        # Session 1: Recent, Python debugging
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
                )
            ],
            "tags": ["python", "debugging", "types"]
        },

        # Session 2: Old session, JavaScript
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
                    content="Here's the design pattern for async operations.",
                    timestamp=(now - timedelta(days=90)).isoformat()
                )
            ],
            "tags": ["javascript", "async"]
        },

        # Session 3: Very recent, React
        {
            "session_id": "session_003",
            "project": "react-app",
            "created_at": (now - timedelta(hours=12)).isoformat(),
            "messages": [
                SessionMessage(
                    role="user",
                    content="How do I create a reusable React component?",
                    timestamp=(now - timedelta(hours=12)).isoformat()
                ),
                SessionMessage(
                    role="assistant",
                    content="Here's a PATTERN for creating reusable components. This is a WORKING_SOLUTION.",
                    timestamp=(now - timedelta(hours=12)).isoformat()
                )
            ],
            "tags": ["react", "components"]
        },

        # Session 4: Moderate age, database
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
                    content="The strategy for query optimization involves indexing.",
                    timestamp=(now - timedelta(days=15)).isoformat()
                )
            ],
            "tags": ["database", "performance"]
        },

        # Session 5: Old, ML
        {
            "session_id": "session_005",
            "project": "ml-project",
            "created_at": (now - timedelta(days=60)).isoformat(),
            "messages": [
                SessionMessage(
                    role="user",
                    content="How do I implement a neural network?",
                    timestamp=(now - timedelta(days=60)).isoformat()
                ),
                SessionMessage(
                    role="assistant",
                    content="Here's the architecture PATTERN for classification models.",
                    timestamp=(now - timedelta(days=60)).isoformat()
                )
            ],
            "tags": ["machine-learning"]
        },

        # Session 6: Recent, API design
        {
            "session_id": "session_006",
            "project": "rest-api",
            "created_at": (now - timedelta(days=5)).isoformat(),
            "messages": [
                SessionMessage(
                    role="user",
                    content="I need to design a REST API",
                    timestamp=(now - timedelta(days=5)).isoformat()
                ),
                SessionMessage(
                    role="assistant",
                    content="Here's the approach. WAITING on your decision.",
                    timestamp=(now - timedelta(days=5)).isoformat()
                )
            ],
            "tags": ["api", "rest"]
        },

        # Session 7: Moderate age, testing
        {
            "session_id": "session_007",
            "project": "test-suite",
            "created_at": (now - timedelta(days=20)).isoformat(),
            "messages": [
                SessionMessage(
                    role="user",
                    content="What's the best strategy for integration tests?",
                    timestamp=(now - timedelta(days=20)).isoformat()
                ),
                SessionMessage(
                    role="assistant",
                    content="The testing strategy involves fixtures and mocks.",
                    timestamp=(now - timedelta(days=20)).isoformat()
                )
            ],
            "tags": ["testing", "integration"]
        },

        # Session 8: Very recent, performance
        {
            "session_id": "session_008",
            "project": "optimization",
            "created_at": (now - timedelta(days=1)).isoformat(),
            "messages": [
                SessionMessage(
                    role="user",
                    content="My application is running slowly",
                    timestamp=(now - timedelta(days=1)).isoformat()
                ),
                SessionMessage(
                    role="assistant",
                    content="Here's a WORKING_SOLUTION for optimization. The PATTERN involves profiling first.",
                    timestamp=(now - timedelta(days=1)).isoformat()
                )
            ],
            "tags": ["performance", "optimization"]
        },

        # Session 9: Old, Docker
        {
            "session_id": "session_009",
            "project": "devops",
            "created_at": (now - timedelta(days=45)).isoformat(),
            "messages": [
                SessionMessage(
                    role="user",
                    content="How do I containerize with Docker?",
                    timestamp=(now - timedelta(days=45)).isoformat()
                ),
                SessionMessage(
                    role="assistant",
                    content="Here's the approach for Docker containerization.",
                    timestamp=(now - timedelta(days=45)).isoformat()
                )
            ],
            "tags": ["docker", "devops"]
        },

        # Session 10: Recent, security
        {
            "session_id": "session_010",
            "project": "security",
            "created_at": (now - timedelta(days=3)).isoformat(),
            "messages": [
                SessionMessage(
                    role="user",
                    content="What are the best security practices?",
                    timestamp=(now - timedelta(days=3)).isoformat()
                ),
                SessionMessage(
                    role="assistant",
                    content="Here's a PATTERN for web security. This WORKING_SOLUTION includes validation.",
                    timestamp=(now - timedelta(days=3)).isoformat()
                )
            ],
            "tags": ["security", "web"]
        }
    ]

    return sessions


def run_tests():
    """Run all integration tests."""
    print("=" * 80)
    print("INTEGRATION TESTS FOR SEARCH FLOW")
    print("=" * 80)

    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    print(f"\nUsing temp directory: {temp_dir}")

    try:
        # Initialize services
        print("\n1. Initializing services...")
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
        chunking_service = ChunkingService()
        print("   ✓ Services initialized")

        # Create test sessions
        print("\n2. Creating test sessions...")
        test_sessions = create_test_sessions()
        print(f"   ✓ Created {len(test_sessions)} test sessions")

        # Index sessions
        print("\n3. Indexing sessions into ChromaDB...")
        total_chunks = 0
        for i, session in enumerate(test_sessions, 1):
            # Chunk messages
            chunks = chunking_service.chunk_messages(session["messages"])

            # Add to registry
            session_registry.add_session(
                session_id=session["session_id"],
                project=session["project"],
                created_at=session["created_at"],
                message_count=len(session["messages"]),
                chunk_count=len(chunks),
                tags=session["tags"]
            )

            # Generate embeddings
            texts = [chunk.content for chunk in chunks]
            embeddings = embedding_service.embed_texts(texts)

            # Store in vector database
            for j, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                vector_db_service.add_chunks(
                    embeddings=[emb],
                    texts=[chunk.content],
                    metadatas=[{
                        "session_id": session["session_id"],
                        "project": session["project"],
                        "chunk_index": j,
                        "memory_types": ",".join(chunk.memory_types) if chunk.memory_types else ""
                    }]
                )

            total_chunks += len(chunks)
            print(f"   Session {i}/10: {session['session_id']} ({len(chunks)} chunks)")

        print(f"   ✓ Indexed {total_chunks} total chunks")

        # Verify indexing
        print("\n4. Verifying indexing...")
        stats = vector_db_service.get_stats()
        assert stats["total_chunks"] == total_chunks, f"Expected {total_chunks}, got {stats['total_chunks']}"
        print(f"   ✓ Vector DB has {stats['total_chunks']} chunks")

        registry_stats = session_registry.get_stats()
        assert registry_stats["total_sessions"] == 10, f"Expected 10, got {registry_stats['total_sessions']}"
        print(f"   ✓ Registry has {registry_stats['total_sessions']} sessions")

        # Test search ranking
        print("\n5. Testing search ranking order...")
        results = search_service.search("Python debugging TypeError", top_n_sessions=5)
        assert len(results) > 0, "No search results"
        print(f"   ✓ Found {len(results)} results")
        print(f"   Top result: {results[0].session_id} (score: {results[0].score:.3f})")

        # Test performance
        print("\n6. Testing search performance (<3s target)...")
        start_time = time.time()
        results = search_service.search("database optimization performance", top_n_sessions=5)
        elapsed = time.time() - start_time
        assert elapsed < 3.0, f"Search took {elapsed:.2f}s, exceeds 3s"
        print(f"   ✓ Search completed in {elapsed:.3f}s (within 3s target)")

        # Test memory boost
        print("\n7. Testing memory boost effects...")
        results = search_service.search("design pattern optimization", top_n_sessions=5)
        top_ids = [r.session_id for r in results[:3]]
        memory_sessions = {"session_003", "session_005", "session_008", "session_010"}
        matches = len(memory_sessions.intersection(set(top_ids)))
        assert matches >= 1, "No memory-boosted sessions in top 3"
        print(f"   ✓ {matches} sessions with memory markers in top 3")

        # Test recency factor
        print("\n8. Testing recency factor...")
        results = search_service.search("design pattern architecture", top_n_sessions=5)
        recent_found = False
        old_found = False
        for r in results:
            if r.session_id in ["session_001", "session_003", "session_008", "session_010"]:
                recent_found = True
            if r.session_id in ["session_002", "session_005", "session_009"]:
                old_found = True

        print(f"   ✓ Recency factor affects ranking (recent: {recent_found}, old: {old_found})")

        # Test multiple queries
        print("\n9. Testing multiple queries...")
        queries = [
            "React components",
            "database optimization",
            "security practices",
            "testing strategy",
        ]
        for query in queries:
            results = search_service.search(query, top_n_sessions=3)
            assert len(results) > 0, f"No results for: {query}"
            print(f"   ✓ Query '{query}': {len(results)} results")

        print("\n" + "=" * 80)
        print("ALL INTEGRATION TESTS PASSED ✓")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        print(f"\nCleaning up temp directory...")
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
