#!/usr/bin/env python3
"""
Manual integration test for VectorDBService.

This script tests the VectorDBService with real ChromaDB operations
to verify CRUD functionality, search, and persistence.
"""

import os
import sys
import tempfile
import shutil

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from smart_fork.vector_db_service import VectorDBService


def create_sample_embedding(index: int, dim: int = 768):
    """Create a sample embedding vector."""
    embedding = [0.0] * dim
    # Set some values based on index
    for j in range(10):
        if (index * 10 + j) < dim:
            embedding[index * 10 + j] = 1.0
    return embedding


def test_basic_crud():
    """Test basic CRUD operations."""
    print("\n" + "="*60)
    print("TEST 1: Basic CRUD Operations")
    print("="*60)

    temp_dir = tempfile.mkdtemp(prefix="test_vdb_")
    try:
        service = VectorDBService(persist_directory=temp_dir)

        # Add chunks
        chunks = ["This is chunk 1", "This is chunk 2", "This is chunk 3"]
        embeddings = [create_sample_embedding(i) for i in range(3)]
        metadata = [
            {"session_id": "session_1", "chunk_index": 0, "topic": "testing"},
            {"session_id": "session_1", "chunk_index": 1, "topic": "testing"},
            {"session_id": "session_2", "chunk_index": 0, "topic": "other"}
        ]

        chunk_ids = service.add_chunks(chunks, embeddings, metadata)
        print(f"✓ Added 3 chunks: {chunk_ids}")

        # Get stats
        stats = service.get_stats()
        print(f"✓ Stats: {stats['total_chunks']} total chunks")

        # Get chunk by ID
        chunk = service.get_chunk_by_id(chunk_ids[0])
        if chunk:
            print(f"✓ Retrieved chunk: '{chunk.content}' from session {chunk.session_id}")
        else:
            print("✗ Failed to retrieve chunk")
            return False

        # Get session chunks
        session_chunks = service.get_session_chunks("session_1")
        print(f"✓ Found {len(session_chunks)} chunks for session_1")

        # Delete session
        deleted = service.delete_session_chunks("session_1")
        print(f"✓ Deleted {deleted} chunks from session_1")

        # Verify deletion
        stats = service.get_stats()
        print(f"✓ After deletion: {stats['total_chunks']} total chunks")

        print("✓ TEST 1 PASSED")
        return True

    except Exception as e:
        print(f"✗ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_search():
    """Test vector search functionality."""
    print("\n" + "="*60)
    print("TEST 2: Vector Search")
    print("="*60)

    temp_dir = tempfile.mkdtemp(prefix="test_vdb_")
    try:
        service = VectorDBService(persist_directory=temp_dir)

        # Add chunks with different embeddings
        chunks = [
            "Machine learning is fascinating",
            "Python is a great programming language",
            "Deep learning uses neural networks",
            "JavaScript is used for web development",
            "AI and ML are transforming technology"
        ]
        embeddings = [create_sample_embedding(i) for i in range(5)]
        metadata = [
            {"session_id": f"session_{i}", "chunk_index": 0}
            for i in range(5)
        ]

        service.add_chunks(chunks, embeddings, metadata)
        print(f"✓ Added {len(chunks)} chunks")

        # Search
        query_embedding = create_sample_embedding(0)
        results = service.search_chunks(query_embedding, k=3)

        print(f"✓ Search returned {len(results)} results")

        for i, result in enumerate(results):
            print(f"  {i+1}. '{result.content[:50]}...' (similarity: {result.similarity:.3f})")

        if len(results) > 0:
            print("✓ TEST 2 PASSED")
            return True
        else:
            print("✗ TEST 2 FAILED: No results")
            return False

    except Exception as e:
        print(f"✗ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_search_with_filters():
    """Test search with metadata filters."""
    print("\n" + "="*60)
    print("TEST 3: Search with Metadata Filters")
    print("="*60)

    temp_dir = tempfile.mkdtemp(prefix="test_vdb_")
    try:
        service = VectorDBService(persist_directory=temp_dir)

        # Add chunks from different sessions
        chunks = ["Chunk A1", "Chunk A2", "Chunk B1", "Chunk B2"]
        embeddings = [create_sample_embedding(i) for i in range(4)]
        metadata = [
            {"session_id": "session_a", "chunk_index": 0},
            {"session_id": "session_a", "chunk_index": 1},
            {"session_id": "session_b", "chunk_index": 0},
            {"session_id": "session_b", "chunk_index": 1}
        ]

        service.add_chunks(chunks, embeddings, metadata)
        print("✓ Added 4 chunks (2 per session)")

        # Search with filter
        query_embedding = create_sample_embedding(0)
        results = service.search_chunks(
            query_embedding,
            k=10,
            filter_metadata={"session_id": "session_a"}
        )

        print(f"✓ Filtered search returned {len(results)} results")

        # Verify all results are from session_a
        all_session_a = all(r.session_id == "session_a" for r in results)

        if all_session_a and len(results) == 2:
            print("✓ All results are from session_a")
            print("✓ TEST 3 PASSED")
            return True
        else:
            print("✗ TEST 3 FAILED: Filter didn't work correctly")
            return False

    except Exception as e:
        print(f"✗ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_persistence():
    """Test database persistence across instances."""
    print("\n" + "="*60)
    print("TEST 4: Database Persistence")
    print("="*60)

    temp_dir = tempfile.mkdtemp(prefix="test_vdb_")
    try:
        # First instance - add data
        service1 = VectorDBService(persist_directory=temp_dir)
        chunks = ["Persistent chunk"]
        embeddings = [create_sample_embedding(0)]
        metadata = [{"session_id": "test_session", "chunk_index": 0}]
        chunk_ids = service1.add_chunks(chunks, embeddings, metadata)
        print(f"✓ Added chunk with ID: {chunk_ids[0]}")

        # Second instance - read data
        service2 = VectorDBService(persist_directory=temp_dir)
        stats = service2.get_stats()
        print(f"✓ New instance sees {stats['total_chunks']} chunks")

        # Retrieve the chunk
        chunk = service2.get_chunk_by_id(chunk_ids[0])

        if chunk and chunk.content == "Persistent chunk":
            print("✓ Successfully retrieved persisted chunk")
            print("✓ TEST 4 PASSED")
            return True
        else:
            print("✗ TEST 4 FAILED: Could not retrieve persisted chunk")
            return False

    except Exception as e:
        print(f"✗ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_reset():
    """Test database reset functionality."""
    print("\n" + "="*60)
    print("TEST 5: Database Reset")
    print("="*60)

    temp_dir = tempfile.mkdtemp(prefix="test_vdb_")
    try:
        service = VectorDBService(persist_directory=temp_dir)

        # Add data
        chunks = ["Chunk 1", "Chunk 2"]
        embeddings = [create_sample_embedding(i) for i in range(2)]
        metadata = [{"session_id": "test", "chunk_index": i} for i in range(2)]
        service.add_chunks(chunks, embeddings, metadata)

        stats = service.get_stats()
        print(f"✓ Added {stats['total_chunks']} chunks")

        # Reset
        service.reset()
        print("✓ Database reset")

        # Check stats
        stats = service.get_stats()
        print(f"✓ After reset: {stats['total_chunks']} chunks")

        if stats['total_chunks'] == 0:
            print("✓ TEST 5 PASSED")
            return True
        else:
            print("✗ TEST 5 FAILED: Reset didn't clear all data")
            return False

    except Exception as e:
        print(f"✗ TEST 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_large_batch():
    """Test handling large batches of chunks."""
    print("\n" + "="*60)
    print("TEST 6: Large Batch Handling")
    print("="*60)

    temp_dir = tempfile.mkdtemp(prefix="test_vdb_")
    try:
        service = VectorDBService(persist_directory=temp_dir)

        # Add 100 chunks
        num_chunks = 100
        chunks = [f"Chunk number {i}" for i in range(num_chunks)]
        embeddings = [create_sample_embedding(i % 10) for i in range(num_chunks)]
        metadata = [
            {"session_id": f"session_{i // 10}", "chunk_index": i % 10}
            for i in range(num_chunks)
        ]

        chunk_ids = service.add_chunks(chunks, embeddings, metadata)
        print(f"✓ Added {len(chunk_ids)} chunks")

        stats = service.get_stats()
        print(f"✓ Database contains {stats['total_chunks']} chunks")

        # Search
        results = service.search_chunks(create_sample_embedding(0), k=10)
        print(f"✓ Search returned {len(results)} results")

        if stats['total_chunks'] == num_chunks and len(results) > 0:
            print("✓ TEST 6 PASSED")
            return True
        else:
            print("✗ TEST 6 FAILED")
            return False

    except Exception as e:
        print(f"✗ TEST 6 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """Run all manual tests."""
    print("\n" + "="*60)
    print("VectorDBService Manual Integration Tests")
    print("="*60)

    tests = [
        ("Basic CRUD Operations", test_basic_crud),
        ("Vector Search", test_search),
        ("Search with Filters", test_search_with_filters),
        ("Database Persistence", test_persistence),
        ("Database Reset", test_reset),
        ("Large Batch Handling", test_large_batch)
    ]

    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
