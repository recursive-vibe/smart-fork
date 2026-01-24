"""
Tests for BackgroundIndexer class.
"""

import unittest
import tempfile
import time
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from smart_fork.background_indexer import (
    BackgroundIndexer,
    IndexingTask,
    SessionFileHandler
)
from smart_fork.session_parser import SessionParser, SessionMessage
from smart_fork.chunking_service import ChunkingService
from smart_fork.embedding_service import EmbeddingService
from smart_fork.vector_db_service import VectorDBService
from smart_fork.session_registry import SessionRegistry


class TestIndexingTask(unittest.TestCase):
    """Test IndexingTask dataclass."""

    def test_needs_indexing_new_messages(self):
        """Test that task needs indexing when there are new messages."""
        task = IndexingTask(
            file_path=Path('/tmp/test.jsonl'),
            last_modified=time.time(),
            message_count=100,
            last_indexed_count=50
        )
        self.assertTrue(task.needs_indexing())

    def test_needs_indexing_no_new_messages(self):
        """Test that task doesn't need indexing when up-to-date."""
        task = IndexingTask(
            file_path=Path('/tmp/test.jsonl'),
            last_modified=time.time(),
            message_count=100,
            last_indexed_count=100
        )
        self.assertFalse(task.needs_indexing())

    def test_needs_indexing_new_file(self):
        """Test that new file needs indexing."""
        task = IndexingTask(
            file_path=Path('/tmp/test.jsonl'),
            last_modified=time.time(),
            message_count=50,
            last_indexed_count=0
        )
        self.assertTrue(task.needs_indexing())


class TestSessionFileHandler(unittest.TestCase):
    """Test SessionFileHandler class."""

    def test_on_modified_jsonl_file(self):
        """Test that callback is called for modified .jsonl files."""
        callback = Mock()
        handler = SessionFileHandler(callback)

        event = Mock()
        event.is_directory = False
        event.src_path = '/tmp/session.jsonl'

        handler.on_modified(event)
        callback.assert_called_once()

    def test_on_modified_non_jsonl_file(self):
        """Test that callback is not called for non-.jsonl files."""
        callback = Mock()
        handler = SessionFileHandler(callback)

        event = Mock()
        event.is_directory = False
        event.src_path = '/tmp/session.txt'

        handler.on_modified(event)
        callback.assert_not_called()

    def test_on_modified_directory(self):
        """Test that callback is not called for directories."""
        callback = Mock()
        handler = SessionFileHandler(callback)

        event = Mock()
        event.is_directory = True
        event.src_path = '/tmp/sessions'

        handler.on_modified(event)
        callback.assert_not_called()

    def test_on_created_jsonl_file(self):
        """Test that callback is called for created .jsonl files."""
        callback = Mock()
        handler = SessionFileHandler(callback)

        event = Mock()
        event.is_directory = False
        event.src_path = '/tmp/session.jsonl'

        handler.on_created(event)
        callback.assert_called_once()


class TestBackgroundIndexer(unittest.TestCase):
    """Test BackgroundIndexer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.claude_dir = Path(self.temp_dir) / '.claude'
        self.claude_dir.mkdir(parents=True, exist_ok=True)

        # Create mock services
        self.vector_db = Mock(spec=VectorDBService)
        self.session_registry = Mock(spec=SessionRegistry)
        self.embedding_service = Mock(spec=EmbeddingService)
        self.chunking_service = Mock(spec=ChunkingService)
        self.session_parser = Mock(spec=SessionParser)

        # Create indexer
        self.indexer = BackgroundIndexer(
            claude_dir=self.claude_dir,
            vector_db=self.vector_db,
            session_registry=self.session_registry,
            embedding_service=self.embedding_service,
            chunking_service=self.chunking_service,
            session_parser=self.session_parser,
            debounce_seconds=0.5,
            checkpoint_interval=10,
            max_workers=1
        )

    def tearDown(self):
        """Clean up after tests."""
        if self.indexer.is_running():
            self.indexer.stop()

        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Test indexer initialization."""
        self.assertEqual(self.indexer.claude_dir, self.claude_dir)
        self.assertEqual(self.indexer.debounce_seconds, 0.5)
        self.assertEqual(self.indexer.checkpoint_interval, 10)
        self.assertEqual(self.indexer.max_workers, 1)
        self.assertFalse(self.indexer.is_running())

    def test_start_stop(self):
        """Test starting and stopping the indexer."""
        self.indexer.start()
        self.assertTrue(self.indexer.is_running())

        self.indexer.stop()
        self.assertFalse(self.indexer.is_running())

    def test_start_when_already_running(self):
        """Test starting when already running."""
        self.indexer.start()
        self.assertTrue(self.indexer.is_running())

        # Should not raise an error
        self.indexer.start()
        self.assertTrue(self.indexer.is_running())

        self.indexer.stop()

    def test_stop_when_not_running(self):
        """Test stopping when not running."""
        self.assertFalse(self.indexer.is_running())
        # Should not raise an error
        self.indexer.stop()
        self.assertFalse(self.indexer.is_running())

    def test_count_messages(self):
        """Test counting messages in a session file."""
        test_file = self.claude_dir / 'test.jsonl'

        # Write test messages
        with open(test_file, 'w', encoding='utf-8') as f:
            for i in range(5):
                f.write(json.dumps({'role': 'user', 'content': f'Message {i}'}) + '\n')

        count = self.indexer._count_messages(test_file)
        self.assertEqual(count, 5)

    def test_count_messages_with_empty_lines(self):
        """Test counting messages with empty lines."""
        test_file = self.claude_dir / 'test.jsonl'

        # Write test messages with empty lines
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps({'role': 'user', 'content': 'Message 1'}) + '\n')
            f.write('\n')
            f.write(json.dumps({'role': 'assistant', 'content': 'Message 2'}) + '\n')
            f.write('  \n')
            f.write(json.dumps({'role': 'user', 'content': 'Message 3'}) + '\n')

        count = self.indexer._count_messages(test_file)
        self.assertEqual(count, 3)

    def test_count_messages_nonexistent_file(self):
        """Test counting messages in a nonexistent file."""
        count = self.indexer._count_messages(Path('/nonexistent/file.jsonl'))
        self.assertEqual(count, 0)

    def test_on_file_changed(self):
        """Test file change handler."""
        test_file = self.claude_dir / 'test_session.jsonl'

        # Write test messages
        with open(test_file, 'w', encoding='utf-8') as f:
            for i in range(10):
                f.write(json.dumps({'role': 'user', 'content': f'Message {i}'}) + '\n')

        # Mock registry to return no existing session
        self.session_registry.get_session.return_value = None

        # Trigger file change
        self.indexer._on_file_changed(test_file)

        # Check that task was added
        self.assertEqual(self.indexer.get_pending_count(), 1)

    def test_on_file_changed_nonexistent_file(self):
        """Test file change handler with nonexistent file."""
        test_file = self.claude_dir / 'nonexistent.jsonl'

        # Should not raise an error
        self.indexer._on_file_changed(test_file)
        self.assertEqual(self.indexer.get_pending_count(), 0)

    def test_on_file_changed_update_existing_task(self):
        """Test updating an existing task."""
        test_file = self.claude_dir / 'test_session.jsonl'

        # Write initial messages
        with open(test_file, 'w', encoding='utf-8') as f:
            for i in range(5):
                f.write(json.dumps({'role': 'user', 'content': f'Message {i}'}) + '\n')

        self.session_registry.get_session.return_value = None

        # First change
        self.indexer._on_file_changed(test_file)
        self.assertEqual(self.indexer.get_pending_count(), 1)

        # Add more messages
        time.sleep(0.01)  # Ensure different mtime
        with open(test_file, 'a', encoding='utf-8') as f:
            for i in range(5, 10):
                f.write(json.dumps({'role': 'user', 'content': f'Message {i}'}) + '\n')

        # Second change
        self.indexer._on_file_changed(test_file)
        # Should still be 1 task (updated, not added)
        self.assertEqual(self.indexer.get_pending_count(), 1)

    def test_index_file_success(self):
        """Test successful file indexing."""
        test_file = self.claude_dir / 'test_session.jsonl'

        # Write test messages
        with open(test_file, 'w', encoding='utf-8') as f:
            for i in range(20):
                f.write(json.dumps({'role': 'user', 'content': f'Message {i}'}) + '\n')

        # Mock session data
        mock_messages = [
            SessionMessage(role='user', content=f'Message {i}')
            for i in range(20)
        ]
        mock_session = Mock()
        mock_session.session_id = 'test_session'
        mock_session.messages = mock_messages
        mock_session.created_at = datetime.now()

        self.session_parser.parse_file.return_value = mock_session

        # Mock chunks
        mock_chunks = [Mock(text=f'Chunk {i}', start_idx=i, end_idx=i+1, token_count=100) for i in range(3)]
        self.chunking_service.chunk_messages.return_value = mock_chunks

        # Mock embeddings
        mock_embeddings = [[0.1] * 384 for _ in range(3)]
        self.embedding_service.embed_texts.return_value = mock_embeddings

        # Mock registry
        self.session_registry.get_session.return_value = None

        # Index file
        self.indexer.index_file(test_file, force=True)

        # Verify calls
        self.session_parser.parse_file.assert_called_once()
        self.chunking_service.chunk_messages.assert_called_once()
        self.embedding_service.embed_texts.assert_called_once()
        self.vector_db.delete_session_chunks.assert_called_once_with('test_session')
        self.vector_db.add_chunks.assert_called_once()
        self.session_registry.add_session.assert_called_once()

    def test_index_file_nonexistent(self):
        """Test indexing a nonexistent file."""
        with self.assertRaises(FileNotFoundError):
            self.indexer.index_file(Path('/nonexistent/file.jsonl'))

    def test_index_file_already_indexed(self):
        """Test indexing a file that's already up-to-date."""
        test_file = self.claude_dir / 'test_session.jsonl'

        # Write test messages
        with open(test_file, 'w', encoding='utf-8') as f:
            for i in range(10):
                f.write(json.dumps({'role': 'user', 'content': f'Message {i}'}) + '\n')

        # Mock registry to return session with same message count
        mock_metadata = Mock()
        mock_metadata.message_count = 10
        self.session_registry.get_session.return_value = mock_metadata

        # Index file (without force)
        self.indexer.index_file(test_file, force=False)

        # Should not parse or index
        self.session_parser.parse_file.assert_not_called()

    def test_scan_directory(self):
        """Test scanning directory for session files."""
        # Create test files
        for i in range(3):
            test_file = self.claude_dir / f'session_{i}.jsonl'
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(json.dumps({'role': 'user', 'content': f'Message {i}'}) + '\n')

        # Mock to avoid actual indexing
        with patch.object(self.indexer, 'index_file') as mock_index:
            self.indexer.scan_directory()
            self.assertEqual(mock_index.call_count, 3)

    def test_scan_directory_nonexistent(self):
        """Test scanning a nonexistent directory."""
        indexer = BackgroundIndexer(
            claude_dir=Path('/nonexistent/dir'),
            vector_db=self.vector_db,
            session_registry=self.session_registry,
            embedding_service=self.embedding_service,
            chunking_service=self.chunking_service,
            session_parser=self.session_parser
        )

        # Should not raise an error
        indexer.scan_directory()

    def test_get_stats(self):
        """Test getting indexer statistics."""
        stats = self.indexer.get_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn('files_indexed', stats)
        self.assertIn('chunks_added', stats)
        self.assertIn('errors', stats)
        self.assertIn('last_index_time', stats)

    def test_get_pending_count(self):
        """Test getting pending task count."""
        self.assertEqual(self.indexer.get_pending_count(), 0)

        test_file = self.claude_dir / 'test.jsonl'
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps({'role': 'user', 'content': 'Test'}) + '\n')

        self.session_registry.get_session.return_value = None
        self.indexer._on_file_changed(test_file)

        self.assertEqual(self.indexer.get_pending_count(), 1)

    def test_checkpoint_indexing(self):
        """Test that checkpoint indexing only processes sufficient new messages."""
        test_file = self.claude_dir / 'test_session.jsonl'

        # Write test messages
        with open(test_file, 'w', encoding='utf-8') as f:
            for i in range(15):
                f.write(json.dumps({'role': 'user', 'content': f'Message {i}'}) + '\n')

        # Mock session data with 15 messages, but 10 already indexed
        mock_messages = [
            SessionMessage(role='user', content=f'Message {i}')
            for i in range(15)
        ]
        mock_session = Mock()
        mock_session.session_id = 'test_session'
        mock_session.messages = mock_messages
        mock_session.created_at = datetime.now()

        self.session_parser.parse_file.return_value = mock_session

        # Create task with 10 already indexed (5 new messages, below checkpoint)
        task = IndexingTask(
            file_path=test_file,
            last_modified=time.time(),
            message_count=15,
            last_indexed_count=10
        )

        # Should skip indexing because only 5 new messages (< checkpoint of 10)
        self.indexer._index_session(task)

        # Verify no indexing calls made
        self.vector_db.add_chunks.assert_not_called()


class TestBackgroundIndexerIntegration(unittest.TestCase):
    """Integration tests for BackgroundIndexer."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.claude_dir = Path(self.temp_dir) / '.claude'
        self.claude_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Clean up after tests."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_debouncing(self):
        """Test that debouncing delays processing."""
        # Create mock services
        vector_db = Mock(spec=VectorDBService)
        session_registry = Mock(spec=SessionRegistry)
        embedding_service = Mock(spec=EmbeddingService)
        chunking_service = Mock(spec=ChunkingService)
        session_parser = Mock(spec=SessionParser)

        indexer = BackgroundIndexer(
            claude_dir=self.claude_dir,
            vector_db=vector_db,
            session_registry=session_registry,
            embedding_service=embedding_service,
            chunking_service=chunking_service,
            session_parser=session_parser,
            debounce_seconds=0.5,
            max_workers=1
        )

        test_file = self.claude_dir / 'test.jsonl'
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps({'role': 'user', 'content': 'Test'}) + '\n')

        session_registry.get_session.return_value = None

        # Add file change
        indexer._on_file_changed(test_file)
        self.assertEqual(indexer.get_pending_count(), 1)

        # Start monitoring
        indexer.start()
        time.sleep(0.2)  # Less than debounce time

        # Should still be pending
        self.assertEqual(indexer.get_pending_count(), 1)

        # Wait for debounce to complete
        time.sleep(0.5)

        # Should be processed now
        self.assertEqual(indexer.get_pending_count(), 0)

        indexer.stop()


if __name__ == '__main__':
    unittest.main()
