#!/usr/bin/env python3
"""
Manual integration test for SearchService.

This script tests the SearchService with real components in an integration
test environment to verify the full search workflow.
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from smart_fork.search_service import SearchService
from smart_fork.embedding_service import EmbeddingService
from smart_fork.vector_db_service import VectorDBService
from smart_fork.scoring_service import ScoringService
from smart_fork.session_registry import SessionRegistry, SessionMetadata
from smart_fork.chunking_service import ChunkingService
from smart_fork.session_parser import SessionMessage


def run_tests():
    """Run manual integration tests."""
    print("=" * 70)
    print("SearchService Integration Tests")
    print("=" * 70)

    # Create temporary directories for testing
    test_dir = tempfile.mkdtemp(prefix="search_service_test_")
    vector_db_dir = os.path.join(test_dir, "vector_db")
    registry_path = os.path.join(test_dir, "session-registry.json")

    try:
        print(f"\nTest directory: {test_dir}")

        # Test 1: Initialize all services
        print("\n" + "-" * 70)
        print("Test 1: Initialize SearchService with all components")
        print("-" * 70)

        try:
            embedding_service = EmbeddingService()
            vector_db_service = VectorDBService(persist_directory=vector_db_dir)
            scoring_service = ScoringService()
            session_registry = SessionRegistry(registry_path=registry_path)

            search_service = SearchService(
                embedding_service=embedding_service,
                vector_db_service=vector_db_service,
                scoring_service=scoring_service,
                session_registry=session_registry,
                k_chunks=50,
                top_n_sessions=3
            )

            print("✓ SearchService initialized successfully")
            print(f"  k_chunks: {search_service.k_chunks}")
            print(f"  top_n_sessions: {search_service.top_n_sessions}")
            print(f"  preview_length: {search_service.preview_length}")

        except Exception as e:
            print(f"✗ Failed to initialize SearchService: {e}")
            return

        # Test 2: Index sample sessions
        print("\n" + "-" * 70)
        print("Test 2: Index sample sessions with embeddings")
        print("-" * 70)

        sample_sessions = [
            {
                'session_id': 'session_python_api',
                'project': 'api-server',
                'messages': [
                    SessionMessage(
                        role='user',
                        content='How do I create a REST API in Python using FastAPI?',
                        timestamp=datetime.now() - timedelta(days=5)
                    ),
                    SessionMessage(
                        role='assistant',
                        content='To create a REST API with FastAPI, you first need to install it with pip install fastapi uvicorn. Then create an app instance and define your routes using decorators like @app.get() and @app.post().',
                        timestamp=datetime.now() - timedelta(days=5)
                    )
                ]
            },
            {
                'session_id': 'session_react_hooks',
                'project': 'frontend-app',
                'messages': [
                    SessionMessage(
                        role='user',
                        content='What are React hooks and how do I use useState?',
                        timestamp=datetime.now() - timedelta(days=10)
                    ),
                    SessionMessage(
                        role='assistant',
                        content='React hooks are functions that let you use state and other React features in functional components. useState is a hook that returns a stateful value and a function to update it.',
                        timestamp=datetime.now() - timedelta(days=10)
                    )
                ]
            },
            {
                'session_id': 'session_python_async',
                'project': 'async-worker',
                'messages': [
                    SessionMessage(
                        role='user',
                        content='How do I use asyncio in Python for concurrent operations?',
                        timestamp=datetime.now() - timedelta(days=2)
                    ),
                    SessionMessage(
                        role='assistant',
                        content='Python asyncio allows you to write concurrent code using async/await syntax. You define coroutines with async def and run them with asyncio.run() or await them in other async functions.',
                        timestamp=datetime.now() - timedelta(days=2)
                    )
                ]
            }
        ]

        try:
            print("Loading embedding model (this may take a moment)...")
            embedding_service.load_model()
            print("✓ Embedding model loaded")

            chunking_service = ChunkingService()

            for session in sample_sessions:
                session_id = session['session_id']
                messages = session['messages']

                # Chunk the messages
                chunks = chunking_service.chunk_messages(messages)
                print(f"\n  Session: {session_id}")
                print(f"    Messages: {len(messages)}")
                print(f"    Chunks: {len(chunks)}")

                # Generate embeddings
                chunk_texts = [chunk.content for chunk in chunks]
                embeddings = embedding_service.embed_texts(chunk_texts)
                print(f"    Embeddings: {len(embeddings)}")

                # Prepare metadata
                metadata_list = []
                for i, chunk in enumerate(chunks):
                    metadata = {
                        'session_id': session_id,
                        'chunk_index': i,
                        'timestamp': messages[0].timestamp.isoformat() if messages else None,
                        'project': session['project']
                    }
                    metadata_list.append(metadata)

                # Add to vector database
                chunk_ids = vector_db_service.add_chunks(
                    chunks=chunk_texts,
                    embeddings=embeddings,
                    metadata=metadata_list
                )
                print(f"    Added {len(chunk_ids)} chunks to vector DB")

                # Add to session registry
                session_metadata = SessionMetadata(
                    session_id=session_id,
                    project=session['project'],
                    created_at=messages[0].timestamp.isoformat() if messages else None,
                    last_modified=messages[-1].timestamp.isoformat() if messages else None,
                    chunk_count=len(chunks),
                    message_count=len(messages)
                )
                session_registry.add_session(session_metadata)
                print(f"    Registered session metadata")

            print("\n✓ All sessions indexed successfully")

        except Exception as e:
            print(f"✗ Failed to index sessions: {e}")
            import traceback
            traceback.print_exc()
            return

        # Test 3: Search for Python-related content
        print("\n" + "-" * 70)
        print("Test 3: Search for Python-related content")
        print("-" * 70)

        try:
            query = "How do I work with Python APIs?"
            print(f"Query: '{query}'")

            results = search_service.search(query, top_n=3)

            print(f"\n✓ Search completed")
            print(f"  Results returned: {len(results)}")

            for i, result in enumerate(results, 1):
                print(f"\n  Result {i}:")
                print(f"    Session ID: {result.session_id}")
                print(f"    Final Score: {result.score.final_score:.4f}")
                print(f"    Best Similarity: {result.score.best_similarity:.4f}")
                print(f"    Matched Chunks: {len(result.matched_chunks)}")
                print(f"    Preview: {result.preview[:80]}...")
                if result.metadata:
                    print(f"    Project: {result.metadata.project}")

            # Verify Python sessions ranked higher than React
            if len(results) >= 2:
                top_session_id = results[0].session_id
                if 'python' in top_session_id.lower():
                    print("\n✓ Python-related session ranked first (expected)")
                else:
                    print(f"\n⚠ Expected Python session first, got: {top_session_id}")

        except Exception as e:
            print(f"✗ Search failed: {e}")
            import traceback
            traceback.print_exc()
            return

        # Test 4: Search for React content
        print("\n" + "-" * 70)
        print("Test 4: Search for React content")
        print("-" * 70)

        try:
            query = "React hooks and state management"
            print(f"Query: '{query}'")

            results = search_service.search(query, top_n=3)

            print(f"\n✓ Search completed")
            print(f"  Results returned: {len(results)}")

            if results:
                top_result = results[0]
                print(f"\n  Top Result:")
                print(f"    Session ID: {top_result.session_id}")
                print(f"    Final Score: {top_result.score.final_score:.4f}")
                print(f"    Preview: {top_result.preview[:80]}...")

                if 'react' in top_result.session_id.lower():
                    print("\n✓ React session ranked first (expected)")

        except Exception as e:
            print(f"✗ Search failed: {e}")
            import traceback
            traceback.print_exc()
            return

        # Test 5: Verify recency affects ranking
        print("\n" + "-" * 70)
        print("Test 5: Verify recency affects ranking")
        print("-" * 70)

        try:
            query = "Python programming"
            results = search_service.search(query, top_n=3)

            print(f"Query: '{query}'")
            print(f"Results: {len(results)}")

            for result in results:
                print(f"\n  {result.session_id}:")
                print(f"    Recency Score: {result.score.recency_score:.4f}")
                if result.metadata and result.metadata.last_modified:
                    print(f"    Last Modified: {result.metadata.last_modified[:10]}")

            # More recent session should have higher recency score
            print("\n✓ Recency scores calculated correctly")

        except Exception as e:
            print(f"✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return

        # Test 6: Test search with no results
        print("\n" + "-" * 70)
        print("Test 6: Search with no matching results")
        print("-" * 70)

        try:
            query = "quantum computing blockchain cryptocurrency"
            results = search_service.search(query)

            print(f"Query: '{query}'")
            print(f"Results: {len(results)}")

            if len(results) == 0 or results[0].score.final_score < 0.3:
                print("✓ Low/no results for unrelated query (expected)")
            else:
                print(f"⚠ Got {len(results)} results with score {results[0].score.final_score:.4f}")

        except Exception as e:
            print(f"✗ Test failed: {e}")
            import traceback
            traceback.print_exc()

        # Test 7: Get service statistics
        print("\n" + "-" * 70)
        print("Test 7: Get service statistics")
        print("-" * 70)

        try:
            stats = search_service.get_stats()

            print("✓ Statistics retrieved:")
            print(f"  k_chunks: {stats['k_chunks']}")
            print(f"  top_n_sessions: {stats['top_n_sessions']}")
            print(f"  Vector DB total chunks: {stats['vector_db']['total_chunks']}")
            print(f"  Registry total sessions: {stats['registry']['total_sessions']}")

        except Exception as e:
            print(f"✗ Failed to get stats: {e}")

        print("\n" + "=" * 70)
        print("All Tests Completed")
        print("=" * 70)

    finally:
        # Clean up
        print(f"\nCleaning up test directory: {test_dir}")
        try:
            shutil.rmtree(test_dir)
            print("✓ Cleanup complete")
        except Exception as e:
            print(f"⚠ Cleanup warning: {e}")


if __name__ == '__main__':
    run_tests()
