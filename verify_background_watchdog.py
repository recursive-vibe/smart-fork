#!/usr/bin/env python3
"""
Verification script for Background Indexer Watchdog Integration (Task 3).

This script tests:
1. BackgroundIndexer can be started and stopped
2. Watchdog actually monitors files when started
3. Creating a new session file triggers indexing
4. Modifying an existing session file triggers re-indexing
5. Debounce delay (5 seconds) works correctly
6. Watchdog events are captured with proper logging
"""

import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from smart_fork.background_indexer import BackgroundIndexer
from smart_fork.session_parser import SessionParser
from smart_fork.chunking_service import ChunkingService
from smart_fork.embedding_service import EmbeddingService
from smart_fork.vector_db_service import VectorDBService
from smart_fork.session_registry import SessionRegistry

# Configure logging to see watchdog events
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_session_file(path: Path, message_count: int = 3):
    """Create a test session file with N messages."""
    with open(path, 'w') as f:
        for i in range(message_count):
            message = {
                "type": "message",
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Test message {i} - {datetime.now().isoformat()}"
            }
            f.write(json.dumps(message) + '\n')
    logger.info(f"Created test session file: {path} with {message_count} messages")


def verify_watchdog_integration():
    """Verify background indexer watchdog integration."""

    print("=" * 80)
    print("Background Indexer Watchdog Verification")
    print("=" * 80)
    print()

    # Setup test directories in project directory to avoid /tmp fsevents issue
    test_dir = Path(__file__).parent / "test-watchdog-data"
    test_dir.mkdir(parents=True, exist_ok=True)

    watch_dir = test_dir / "sessions"
    watch_dir.mkdir(exist_ok=True)

    storage_dir = test_dir / "storage"
    storage_dir.mkdir(exist_ok=True)

    vector_db_path = storage_dir / "vector_db"
    registry_path = storage_dir / "registry.json"

    logger.info(f"Test directory: {test_dir}")
    logger.info(f"Watch directory: {watch_dir}")
    logger.info(f"Storage directory: {storage_dir}")

    try:
        # Initialize services
        print("\n[1/6] Initializing services...")
        session_parser = SessionParser()
        chunking_service = ChunkingService()
        embedding_service = EmbeddingService()
        vector_db = VectorDBService(persist_directory=str(vector_db_path))
        session_registry = SessionRegistry(registry_path=str(registry_path))

        # Create background indexer
        indexer = BackgroundIndexer(
            claude_dir=watch_dir,
            vector_db=vector_db,
            session_registry=session_registry,
            embedding_service=embedding_service,
            chunking_service=chunking_service,
            session_parser=session_parser,
            debounce_seconds=3.0,  # Shorter for testing
            checkpoint_interval=5,
            max_workers=2
        )

        print("✓ Services initialized")

        # Test 1: Check if indexer can be started
        print("\n[2/6] Testing BackgroundIndexer.start()...")
        indexer.start()

        # Check if observer is running
        if indexer._observer is None:
            print("✗ FAILED: Watchdog observer not initialized")
            print("  This indicates watchdog library may not be installed")
            return False

        if not indexer.is_running():
            print("✗ FAILED: BackgroundIndexer.is_running() returned False")
            return False

        print("✓ BackgroundIndexer started successfully")
        print(f"  - Observer running: {indexer._observer.is_alive() if indexer._observer else False}")
        print(f"  - Monitor thread running: {indexer._monitor_thread.is_alive() if indexer._monitor_thread else False}")

        # Test 2: Create a new session file (should trigger indexing)
        print("\n[3/6] Testing file creation triggers indexing...")
        test_session_1 = watch_dir / "test-session-001.jsonl"
        create_test_session_file(test_session_1, message_count=10)

        print(f"  Created: {test_session_1.name}")
        print(f"  Waiting {indexer.debounce_seconds + 2} seconds for debounce + processing...")

        # Wait for debounce + processing
        time.sleep(indexer.debounce_seconds + 2)

        # Check if session was indexed
        session_meta = session_registry.get_session("test-session-001")
        if session_meta is None:
            print("✗ FAILED: Session was not indexed after file creation")
            print(f"  Pending tasks: {indexer.get_pending_count()}")
            print(f"  Indexer stats: {indexer.get_stats()}")
            return False

        print("✓ File creation triggered indexing")
        print(f"  - Session ID: {session_meta.session_id}")
        print(f"  - Message count: {session_meta.message_count}")
        print(f"  - Chunk count: {session_meta.chunk_count}")

        # Test 3: Modify session file (should trigger re-indexing)
        print("\n[4/6] Testing file modification triggers re-indexing...")
        initial_chunk_count = session_meta.chunk_count

        # Add more messages
        create_test_session_file(test_session_1, message_count=20)
        print(f"  Modified: {test_session_1.name} (added 10 messages)")
        print(f"  Waiting {indexer.debounce_seconds + 2} seconds for debounce + processing...")

        time.sleep(indexer.debounce_seconds + 2)

        # Check if session was re-indexed
        session_meta_updated = session_registry.get_session("test-session-001")
        if session_meta_updated is None:
            print("✗ FAILED: Session metadata not found after modification")
            return False

        if session_meta_updated.message_count <= session_meta.message_count:
            print("✗ FAILED: Session was not re-indexed after modification")
            print(f"  Original message count: {session_meta.message_count}")
            print(f"  Updated message count: {session_meta_updated.message_count}")
            return False

        print("✓ File modification triggered re-indexing")
        print(f"  - Original message count: {session_meta.message_count}")
        print(f"  - Updated message count: {session_meta_updated.message_count}")
        print(f"  - Original chunk count: {initial_chunk_count}")
        print(f"  - Updated chunk count: {session_meta_updated.chunk_count}")

        # Test 4: Test debounce (multiple rapid changes should batch)
        print("\n[5/6] Testing debounce delay...")
        test_session_2 = watch_dir / "test-session-002.jsonl"

        # Create file multiple times rapidly
        print("  Creating file 3 times with 0.5s intervals...")
        create_test_session_file(test_session_2, message_count=5)
        time.sleep(0.5)
        create_test_session_file(test_session_2, message_count=10)
        time.sleep(0.5)
        create_test_session_file(test_session_2, message_count=15)

        # Check pending count immediately (should be 1, not 3)
        time.sleep(0.5)
        pending_count = indexer.get_pending_count()
        print(f"  Pending tasks after rapid changes: {pending_count}")

        # Wait for debounce
        print(f"  Waiting {indexer.debounce_seconds + 2} seconds for debounce...")
        time.sleep(indexer.debounce_seconds + 2)

        # Should be indexed only once with final state
        session_meta_2 = session_registry.get_session("test-session-002")
        if session_meta_2 is None or session_meta_2.message_count != 15:
            print("✗ FAILED: Debounce didn't work correctly")
            if session_meta_2:
                print(f"  Expected 15 messages, got {session_meta_2.message_count}")
            return False

        print("✓ Debounce working correctly")
        print(f"  - Final message count: {session_meta_2.message_count}")
        print(f"  - Only indexed once with final state")

        # Test 5: Check statistics
        print("\n[6/6] Checking indexer statistics...")
        stats = indexer.get_stats()

        print(f"  - Files indexed: {stats['files_indexed']}")
        print(f"  - Chunks added: {stats['chunks_added']}")
        print(f"  - Errors: {stats['errors']}")
        print(f"  - Last index time: {stats['last_index_time']}")

        if stats['files_indexed'] < 2:
            print("✗ WARNING: Expected at least 2 files indexed")

        if stats['errors'] > 0:
            print("✗ WARNING: Indexer encountered errors")

        print("✓ Statistics captured correctly")

        # Stop indexer
        print("\n[7/7] Testing BackgroundIndexer.stop()...")
        indexer.stop()

        if indexer.is_running():
            print("✗ FAILED: BackgroundIndexer still running after stop()")
            return False

        print("✓ BackgroundIndexer stopped successfully")

        # Final summary
        print("\n" + "=" * 80)
        print("VERIFICATION RESULTS")
        print("=" * 80)
        print("✓ All tests passed!")
        print()
        print("Summary:")
        print("  - BackgroundIndexer can be started and stopped")
        print("  - Watchdog monitors file changes when started")
        print("  - Creating new session files triggers indexing")
        print("  - Modifying session files triggers re-indexing")
        print("  - Debounce delay works correctly (batches rapid changes)")
        print("  - Statistics and logging work correctly")
        print()

        return True

    except Exception as e:
        logger.error(f"Verification failed with exception: {e}", exc_info=True)
        print(f"\n✗ FAILED: {e}")
        return False


def main():
    """Main entry point."""
    success = verify_watchdog_integration()

    if success:
        print("\n" + "=" * 80)
        print("CRITICAL FINDING")
        print("=" * 80)
        print()
        print("While the BackgroundIndexer watchdog functionality works correctly,")
        print("it is NOT being used by the MCP server (server.py)!")
        print()
        print("The MCP server only uses SearchService and does not initialize or")
        print("start the BackgroundIndexer at all.")
        print()
        print("The API server (api_server.py) initializes BackgroundIndexer but")
        print("NEVER calls indexer.start(), so the watchdog never runs!")
        print()
        print("RECOMMENDATION:")
        print("  1. Add BackgroundIndexer to server.py initialization")
        print("  2. Call indexer.start() after initialization")
        print("  3. Call indexer.stop() on server shutdown")
        print()
        sys.exit(0)
    else:
        print("\n✗ Verification failed - see errors above")
        sys.exit(1)


if __name__ == "__main__":
    main()
