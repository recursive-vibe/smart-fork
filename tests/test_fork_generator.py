"""
Tests for fork command generator.
"""

import unittest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from smart_fork.fork_generator import ForkGenerator, ForkCommand
from smart_fork.session_registry import SessionMetadata


class TestForkCommand(unittest.TestCase):
    """Test ForkCommand dataclass."""

    def test_fork_command_creation(self):
        """Test creating a ForkCommand."""
        cmd = ForkCommand(
            session_id="test-123",
            terminal_command="claude --resume test-123 --fork-session",
            in_session_command="/fork test-123 /path/to/session.jsonl",
            session_path="/path/to/session.jsonl",
            metadata={'project': 'test-project'}
        )

        self.assertEqual(cmd.session_id, "test-123")
        self.assertEqual(cmd.terminal_command, "claude --resume test-123 --fork-session")
        self.assertEqual(cmd.in_session_command, "/fork test-123 /path/to/session.jsonl")
        self.assertEqual(cmd.session_path, "/path/to/session.jsonl")
        self.assertEqual(cmd.metadata['project'], 'test-project')

    def test_fork_command_minimal(self):
        """Test creating a minimal ForkCommand."""
        cmd = ForkCommand(
            session_id="test-456",
            terminal_command="claude --resume test-456 --fork-session",
            in_session_command="/fork test-456 /path.jsonl"
        )

        self.assertEqual(cmd.session_id, "test-456")
        self.assertIsNone(cmd.session_path)
        self.assertIsNone(cmd.metadata)


class TestForkGeneratorInit(unittest.TestCase):
    """Test ForkGenerator initialization."""

    def test_init_default(self):
        """Test initialization with default sessions directory."""
        generator = ForkGenerator()

        expected_dir = os.path.expanduser("~/.claude")
        self.assertEqual(generator.claude_sessions_dir, expected_dir)

    def test_init_custom_dir(self):
        """Test initialization with custom sessions directory."""
        custom_dir = "/custom/path/to/sessions"
        generator = ForkGenerator(claude_sessions_dir=custom_dir)

        self.assertEqual(generator.claude_sessions_dir, custom_dir)

    def test_init_expands_home(self):
        """Test that ~ is expanded in sessions directory."""
        generator = ForkGenerator(claude_sessions_dir="~/custom/claude")

        # Should expand ~
        self.assertNotIn("~", generator.claude_sessions_dir)
        self.assertTrue(generator.claude_sessions_dir.startswith("/"))


class TestFindSessionPath(unittest.TestCase):
    """Test session path finding."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.generator = ForkGenerator(claude_sessions_dir=self.temp_dir)

    def test_find_session_direct_path(self):
        """Test finding session in direct path."""
        session_id = "test-session-123"
        session_file = os.path.join(self.temp_dir, f"{session_id}.jsonl")

        # Create the file
        with open(session_file, 'w') as f:
            f.write('{"test": "data"}\n')

        path = self.generator.find_session_path(session_id)
        self.assertEqual(path, session_file)
        self.assertTrue(os.path.exists(path))

    def test_find_session_project_path(self):
        """Test finding session in project subdirectory."""
        session_id = "test-session-456"
        project = "my-project"

        # Create project directory structure
        project_dir = os.path.join(self.temp_dir, "projects", project)
        os.makedirs(project_dir, exist_ok=True)

        session_file = os.path.join(project_dir, f"{session_id}.jsonl")
        with open(session_file, 'w') as f:
            f.write('{"test": "data"}\n')

        path = self.generator.find_session_path(session_id, project=project)
        self.assertEqual(path, session_file)
        self.assertTrue(os.path.exists(path))

    def test_find_session_sessions_subdirectory(self):
        """Test finding session in sessions subdirectory."""
        session_id = "test-session-789"

        # Create sessions subdirectory
        sessions_dir = os.path.join(self.temp_dir, "sessions")
        os.makedirs(sessions_dir, exist_ok=True)

        session_file = os.path.join(sessions_dir, f"{session_id}.jsonl")
        with open(session_file, 'w') as f:
            f.write('{"test": "data"}\n')

        path = self.generator.find_session_path(session_id)
        self.assertEqual(path, session_file)
        self.assertTrue(os.path.exists(path))

    def test_find_session_not_found_returns_likely_path(self):
        """Test that when session not found, returns likely path."""
        session_id = "nonexistent-session"

        path = self.generator.find_session_path(session_id)

        # Should return constructed path even if doesn't exist
        self.assertIsNotNone(path)
        self.assertIn(session_id, path)
        self.assertTrue(path.endswith(".jsonl"))

    def test_find_session_not_found_with_project(self):
        """Test that when session not found with project, returns project path."""
        session_id = "nonexistent-session"
        project = "test-project"

        path = self.generator.find_session_path(session_id, project=project)

        # Should include project in path
        self.assertIsNotNone(path)
        self.assertIn(session_id, path)
        self.assertIn(project, path)
        self.assertTrue(path.endswith(".jsonl"))


class TestGenerateCommands(unittest.TestCase):
    """Test command generation methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.generator = ForkGenerator()

    def test_generate_terminal_command(self):
        """Test terminal command generation."""
        session_id = "abc-123-def-456"
        cmd = self.generator.generate_terminal_command(session_id)

        expected = f"claude --resume {session_id} --fork-session"
        self.assertEqual(cmd, expected)

    def test_generate_in_session_command(self):
        """Test in-session command generation."""
        session_id = "abc-123-def-456"
        session_path = "/home/user/.claude/abc-123-def-456.jsonl"
        cmd = self.generator.generate_in_session_command(session_id, session_path)

        expected = f"/fork {session_id} {session_path}"
        self.assertEqual(cmd, expected)

    def test_generate_in_session_command_with_spaces(self):
        """Test in-session command with path containing spaces."""
        session_id = "abc-123"
        session_path = "/home/user/My Documents/.claude/abc-123.jsonl"
        cmd = self.generator.generate_in_session_command(session_id, session_path)

        expected = f"/fork {session_id} {session_path}"
        self.assertEqual(cmd, expected)
        self.assertIn("My Documents", cmd)


class TestFormatMetadata(unittest.TestCase):
    """Test metadata formatting."""

    def setUp(self):
        """Set up test fixtures."""
        self.generator = ForkGenerator()

    def test_format_metadata_complete(self):
        """Test formatting complete metadata."""
        metadata = SessionMetadata(
            session_id="test-123",
            project="test-project",
            created_at="2026-01-20T15:30:00Z",
            last_synced="2026-01-20T15:30:00Z",
            message_count=42,
            chunk_count=15,
            tags=["important", "feature-x"]
        )

        formatted = self.generator.format_metadata(metadata)

        self.assertIn("test-project", formatted)
        self.assertIn("2026-01-20", formatted)
        self.assertIn("42", formatted)
        self.assertIn("15", formatted)
        self.assertIn("important", formatted)
        self.assertIn("feature-x", formatted)

    def test_format_metadata_minimal(self):
        """Test formatting minimal metadata."""
        metadata = SessionMetadata(
            session_id="test-456",
            project=None,
            created_at="2026-01-20T15:30:00Z",
            last_synced="2026-01-20T15:30:00Z",
            message_count=10,
            chunk_count=3,
            tags=[]
        )

        formatted = self.generator.format_metadata(metadata)

        self.assertIn("Unknown", formatted)
        self.assertIn("10", formatted)
        self.assertIn("3", formatted)

    def test_format_metadata_none(self):
        """Test formatting None metadata."""
        formatted = self.generator.format_metadata(None)

        self.assertEqual(formatted, "No metadata available")

    def test_format_metadata_invalid_date(self):
        """Test formatting metadata with invalid date."""
        metadata = SessionMetadata(
            session_id="test-789",
            project="test-project",
            created_at="invalid-date",
            last_synced="invalid-date",
            message_count=5,
            chunk_count=2,
            tags=[]
        )

        formatted = self.generator.format_metadata(metadata)

        # Should include the raw date string
        self.assertIn("invalid-date", formatted)


class TestGenerateForkCommand(unittest.TestCase):
    """Test full fork command generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.generator = ForkGenerator(claude_sessions_dir=self.temp_dir)

    def test_generate_fork_command_basic(self):
        """Test generating fork command without metadata."""
        session_id = "test-session-123"

        fork_cmd = self.generator.generate_fork_command(session_id)

        self.assertEqual(fork_cmd.session_id, session_id)
        self.assertEqual(fork_cmd.terminal_command, f"claude --resume {session_id} --fork-session")
        self.assertIn(session_id, fork_cmd.in_session_command)
        self.assertIsNotNone(fork_cmd.session_path)
        self.assertIsNone(fork_cmd.metadata)

    def test_generate_fork_command_with_metadata(self):
        """Test generating fork command with metadata."""
        session_id = "test-session-456"
        metadata = SessionMetadata(
            session_id=session_id,
            project="my-project",
            created_at="2026-01-20T15:30:00Z",
            last_synced="2026-01-20T15:30:00Z",
            message_count=25,
            chunk_count=10,
            tags=["test", "important"]
        )

        fork_cmd = self.generator.generate_fork_command(session_id, metadata)

        self.assertEqual(fork_cmd.session_id, session_id)
        self.assertIsNotNone(fork_cmd.metadata)
        self.assertEqual(fork_cmd.metadata['project'], 'my-project')
        self.assertEqual(fork_cmd.metadata['message_count'], 25)
        self.assertEqual(fork_cmd.metadata['chunk_count'], 10)
        self.assertEqual(fork_cmd.metadata['tags'], ["test", "important"])

    def test_generate_fork_command_uses_project_path(self):
        """Test that fork command uses project when finding path."""
        session_id = "test-session-789"
        project = "test-project"

        # Create project directory structure
        project_dir = os.path.join(self.temp_dir, "projects", project)
        os.makedirs(project_dir, exist_ok=True)

        session_file = os.path.join(project_dir, f"{session_id}.jsonl")
        with open(session_file, 'w') as f:
            f.write('{"test": "data"}\n')

        metadata = SessionMetadata(
            session_id=session_id,
            project=project,
            created_at="2026-01-20T15:30:00Z",
            last_synced="2026-01-20T15:30:00Z",
            message_count=10,
            chunk_count=5,
            tags=[]
        )

        fork_cmd = self.generator.generate_fork_command(session_id, metadata)

        # Should find the file in project directory
        self.assertEqual(fork_cmd.session_path, session_file)
        self.assertTrue(os.path.exists(fork_cmd.session_path))


class TestFormatForkOutput(unittest.TestCase):
    """Test fork command output formatting."""

    def setUp(self):
        """Set up test fixtures."""
        self.generator = ForkGenerator()

    def test_format_fork_output_basic(self):
        """Test formatting basic fork output."""
        fork_cmd = ForkCommand(
            session_id="test-123",
            terminal_command="claude --resume test-123 --fork-session",
            in_session_command="/fork test-123 /path/to/session.jsonl",
            session_path="/path/to/session.jsonl"
        )

        output = self.generator.format_fork_output(fork_cmd)

        self.assertIn("test-123", output)
        self.assertIn("claude --resume test-123 --fork-session", output)
        self.assertIn("/fork test-123 /path/to/session.jsonl", output)
        self.assertIn("Option 1: New Terminal Fork", output)
        self.assertIn("Option 2: In-Session Fork", output)

    def test_format_fork_output_with_metadata(self):
        """Test formatting fork output with metadata."""
        fork_cmd = ForkCommand(
            session_id="test-456",
            terminal_command="claude --resume test-456 --fork-session",
            in_session_command="/fork test-456 /path.jsonl",
            session_path="/path.jsonl",
            metadata={
                'project': 'test-project',
                'created_at': '2026-01-20T15:30:00Z',
                'message_count': 30,
                'chunk_count': 12,
                'tags': ['feature', 'important']
            }
        )

        output = self.generator.format_fork_output(fork_cmd)

        self.assertIn("Session Details:", output)
        self.assertIn("test-project", output)
        self.assertIn("30", output)
        self.assertIn("12", output)

    def test_format_fork_output_with_execution_time(self):
        """Test formatting fork output with execution time."""
        fork_cmd = ForkCommand(
            session_id="test-789",
            terminal_command="claude --resume test-789 --fork-session",
            in_session_command="/fork test-789 /path.jsonl"
        )

        output = self.generator.format_fork_output(fork_cmd, execution_time=5.5)

        self.assertIn("✨", output)
        self.assertIn("6s", output)  # 5.5 rounds to 6

    def test_format_fork_output_with_long_execution_time(self):
        """Test formatting fork output with long execution time."""
        fork_cmd = ForkCommand(
            session_id="test-999",
            terminal_command="claude --resume test-999 --fork-session",
            in_session_command="/fork test-999 /path.jsonl"
        )

        output = self.generator.format_fork_output(fork_cmd, execution_time=73.0)

        self.assertIn("✨", output)
        self.assertIn("1m 13s", output)


class TestGenerateAndFormat(unittest.TestCase):
    """Test combined generation and formatting."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.generator = ForkGenerator(claude_sessions_dir=self.temp_dir)

    def test_generate_and_format_complete(self):
        """Test generating and formatting in one step."""
        session_id = "test-complete-123"
        metadata = SessionMetadata(
            session_id=session_id,
            project="complete-project",
            created_at="2026-01-20T15:30:00Z",
            last_synced="2026-01-20T15:30:00Z",
            message_count=50,
            chunk_count=20,
            tags=["complete"]
        )

        output = self.generator.generate_and_format(
            session_id,
            metadata=metadata,
            execution_time=2.5
        )

        # Should contain all elements
        self.assertIn(session_id, output)
        self.assertIn("complete-project", output)
        self.assertIn("50", output)
        self.assertIn("20", output)
        self.assertIn("claude --resume", output)
        self.assertIn("/fork", output)
        self.assertIn("✨", output)
        self.assertIn("2s", output)

    def test_generate_and_format_minimal(self):
        """Test generating and formatting with minimal inputs."""
        session_id = "test-minimal-456"

        output = self.generator.generate_and_format(session_id)

        # Should contain basic elements
        self.assertIn(session_id, output)
        self.assertIn("claude --resume", output)
        self.assertIn("/fork", output)

    def test_generate_and_format_no_execution_time(self):
        """Test generating and formatting without execution time."""
        session_id = "test-no-time-789"

        output = self.generator.generate_and_format(session_id)

        # Should not contain execution time marker
        self.assertNotIn("✨", output)


if __name__ == '__main__':
    unittest.main()
