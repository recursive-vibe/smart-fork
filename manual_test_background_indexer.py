#!/usr/bin/env python3
"""
Manual test script for BackgroundIndexer.

This script tests the background indexer with real file system monitoring.
"""

import sys
import tempfile
import time
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from smart_fork.background_indexer import BackgroundIndexer, IndexingTask
from smart_fork.session_parser import SessionParser
from smart_fork.chunking_service import ChunkingService
from smart_fork.embedding_service import EmbeddingService
from smart_fork.vector_db_service import VectorDBService
from smart_fork.session_registry import SessionRegistry


def print_test(name):
    """Print test header."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print('='*60)


def print_result(passed, message=""):
    """Print test result."""
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status}: {message}")


def test_indexing_task():
    """Test IndexingTask dataclass."""
    print_test("IndexingTask dataclass")

    # Test needs_indexing with new messages
    task = IndexingTask(
        file_path=Path('/tmp/test.jsonl'),
        last_modified=time.time(),
        message_count=100,
        last_indexed_count=50
    )
    print_result(task.needs_indexing(), "Needs indexing with new messages")

    # Test needs_indexing when up-to-date
    task2 = IndexingTask(
        file_path=Path('/tmp/test.jsonl'),
        last_modified=time.time(),
        message_count=100,
        last_indexed_count=100
    )
    print_result(not task2.needs_indexing(), "Doesn't need indexing when up-to-date")


def test_basic_initialization():
    """Test basic initialization of BackgroundIndexer."""
    print_test("Basic Initialization")

    temp_dir = tempfile.mkdtemp()
    claude_dir = Path(temp_dir) / '.claude'
    claude_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Create mock services (using actual classes but won't run full pipeline)
        from unittest.mock import Mock

        vector_db = Mock(spec=VectorDBService)
        session_registry = Mock(spec=SessionRegistry)
        embedding_service = Mock(spec=EmbeddingService)
        chunking_service = Mock(spec=ChunkingService)
        session_parser = Mock(spec=SessionParser)

        indexer = BackgroundIndexer(
            claude_dir=claude_dir,
            vector_db=vector_db,
            session_registry=session_registry,
            embedding_service=embedding_service,
            chunking_service=chunking_service,
            session_parser=session_parser,
            debounce_seconds=1.0,
            checkpoint_interval=10,
            max_workers=2
        )

        print_result(indexer.claude_dir == claude_dir, "Claude directory set correctly")
        print_result(indexer.debounce_seconds == 1.0, "Debounce seconds set correctly")
        print_result(indexer.checkpoint_interval == 10, "Checkpoint interval set correctly")
        print_result(not indexer.is_running(), "Initially not running")

    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_start_stop():
    """Test starting and stopping the indexer."""
    print_test("Start and Stop")

    temp_dir = tempfile.mkdtemp()
    claude_dir = Path(temp_dir) / '.claude'
    claude_dir.mkdir(parents=True, exist_ok=True)

    try:
        from unittest.mock import Mock

        vector_db = Mock(spec=VectorDBService)
        session_registry = Mock(spec=SessionRegistry)
        embedding_service = Mock(spec=EmbeddingService)
        chunking_service = Mock(spec=ChunkingService)
        session_parser = Mock(spec=SessionParser)

        indexer = BackgroundIndexer(
            claude_dir=claude_dir,
            vector_db=vector_db,
            session_registry=session_registry,
            embedding_service=embedding_service,
            chunking_service=chunking_service,
            session_parser=session_parser
        )

        # Test start
        indexer.start()
        print_result(indexer.is_running(), "Started successfully")

        # Test stop
        indexer.stop()
        print_result(not indexer.is_running(), "Stopped successfully")

        # Test multiple starts
        indexer.start()
        indexer.start()  # Should not error
        print_result(indexer.is_running(), "Multiple starts handled gracefully")

        indexer.stop()

    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_count_messages():
    """Test message counting."""
    print_test("Message Counting")

    temp_dir = tempfile.mkdtemp()
    claude_dir = Path(temp_dir) / '.claude'
    claude_dir.mkdir(parents=True, exist_ok=True)

    try:
        from unittest.mock import Mock

        vector_db = Mock(spec=VectorDBService)
        session_registry = Mock(spec=SessionRegistry)
        embedding_service = Mock(spec=EmbeddingService)
        chunking_service = Mock(spec=ChunkingService)
        session_parser = Mock(spec=SessionParser)

        indexer = BackgroundIndexer(
            claude_dir=claude_dir,
            vector_db=vector_db,
            session_registry=session_registry,
            embedding_service=embedding_service,
            chunking_service=chunking_service,
            session_parser=session_parser
        )

        # Create test file
        test_file = claude_dir / 'test.jsonl'
        with open(test_file, 'w', encoding='utf-8') as f:
            for i in range(10):
                f.write(json.dumps({'role': 'user', 'content': f'Message {i}'}) + '\n')

        count = indexer._count_messages(test_file)
        print_result(count == 10, f"Counted messages correctly: {count}")

        # Test with empty lines
        test_file2 = claude_dir / 'test2.jsonl'
        with open(test_file2, 'w', encoding='utf-8') as f:
            f.write(json.dumps({'role': 'user', 'content': 'Message 1'}) + '\n')
            f.write('\n')
            f.write(json.dumps({'role': 'user', 'content': 'Message 2'}) + '\n')
            f.write('  \n')

        count2 = indexer._count_messages(test_file2)
        print_result(count2 == 2, f"Skipped empty lines correctly: {count2}")

    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_file_change_detection():
    """Test file change detection."""
    print_test("File Change Detection")

    temp_dir = tempfile.mkdtemp()
    claude_dir = Path(temp_dir) / '.claude'
    claude_dir.mkdir(parents=True, exist_ok=True)

    try:
        from unittest.mock import Mock

        vector_db = Mock(spec=VectorDBService)
        session_registry = Mock(spec=SessionRegistry)
        embedding_service = Mock(spec=EmbeddingService)
        chunking_service = Mock(spec=ChunkingService)
        session_parser = Mock(spec=SessionParser)

        indexer = BackgroundIndexer(
            claude_dir=claude_dir,
            vector_db=vector_db,
            session_registry=session_registry,
            embedding_service=embedding_service,
            chunking_service=chunking_service,
            session_parser=session_parser
        )

        # Create test file
        test_file = claude_dir / 'session1.jsonl'
        with open(test_file, 'w', encoding='utf-8') as f:
            for i in range(5):
                f.write(json.dumps({'role': 'user', 'content': f'Message {i}'}) + '\n')

        # Mock registry
        session_registry.get_session.return_value = None

        # Trigger file change
        indexer._on_file_changed(test_file)
        count = indexer.get_pending_count()
        print_result(count == 1, f"Detected file change, pending count: {count}")

        # Update file
        time.sleep(0.01)
        with open(test_file, 'a', encoding='utf-8') as f:
            for i in range(5, 10):
                f.write(json.dumps({'role': 'user', 'content': f'Message {i}'}) + '\n')

        # Trigger another change
        indexer._on_file_changed(test_file)
        count2 = indexer.get_pending_count()
        print_result(count2 == 1, f"Updated existing task, pending count still: {count2}")

    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_debouncing():
    """Test debouncing mechanism."""
    print_test("Debouncing Mechanism")

    temp_dir = tempfile.mkdtemp()
    claude_dir = Path(temp_dir) / '.claude'
    claude_dir.mkdir(parents=True, exist_ok=True)

    try:
        from unittest.mock import Mock

        vector_db = Mock(spec=VectorDBService)
        session_registry = Mock(spec=SessionRegistry)
        embedding_service = Mock(spec=EmbeddingService)
        chunking_service = Mock(spec=ChunkingService)
        session_parser = Mock(spec=SessionParser)

        indexer = BackgroundIndexer(
            claude_dir=claude_dir,
            vector_db=vector_db,
            session_registry=session_registry,
            embedding_service=embedding_service,
            chunking_service=chunking_service,
            session_parser=session_parser,
            debounce_seconds=0.5
        )

        # Create test file
        test_file = claude_dir / 'session1.jsonl'
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps({'role': 'user', 'content': 'Test'}) + '\n')

        session_registry.get_session.return_value = None

        # Add file change
        indexer._on_file_changed(test_file)
        initial_count = indexer.get_pending_count()
        print_result(initial_count == 1, f"Task added, pending count: {initial_count}")

        # Start monitoring
        indexer.start()
        time.sleep(0.2)  # Less than debounce time

        # Should still be pending
        during_count = indexer.get_pending_count()
        print_result(during_count == 1, f"Still pending during debounce: {during_count}")

        # Wait for debounce to complete
        time.sleep(0.5)

        # Should be processed now (pending count should be 0)
        after_count = indexer.get_pending_count()
        print_result(after_count == 0, f"Processed after debounce: {after_count}")

        indexer.stop()

    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_statistics():
    """Test statistics tracking."""
    print_test("Statistics Tracking")

    temp_dir = tempfile.mkdtemp()
    claude_dir = Path(temp_dir) / '.claude'
    claude_dir.mkdir(parents=True, exist_ok=True)

    try:
        from unittest.mock import Mock

        vector_db = Mock(spec=VectorDBService)
        session_registry = Mock(spec=SessionRegistry)
        embedding_service = Mock(spec=EmbeddingService)
        chunking_service = Mock(spec=ChunkingService)
        session_parser = Mock(spec=SessionParser)

        indexer = BackgroundIndexer(
            claude_dir=claude_dir,
            vector_db=vector_db,
            session_registry=session_registry,
            embedding_service=embedding_service,
            chunking_service=chunking_service,
            session_parser=session_parser
        )

        stats = indexer.get_stats()
        print_result('files_indexed' in stats, "Has files_indexed stat")
        print_result('chunks_added' in stats, "Has chunks_added stat")
        print_result('errors' in stats, "Has errors stat")
        print_result('last_index_time' in stats, "Has last_index_time stat")
        print_result(stats['files_indexed'] == 0, f"Initial files_indexed: {stats['files_indexed']}")

    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """Run all manual tests."""
    print("="*60)
    print("Background Indexer Manual Tests")
    print("="*60)

    tests = [
        test_indexing_task,
        test_basic_initialization,
        test_start_stop,
        test_count_messages,
        test_file_change_detection,
        test_debouncing,
        test_statistics,
    ]

    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"✗ FAIL: Exception in {test.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print("Manual tests completed")
    print("="*60)


if __name__ == '__main__':
    main()
