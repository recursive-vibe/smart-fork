"""
Unit tests for SessionParser.

Tests cover:
- Valid JSONL parsing
- Malformed JSON handling
- UTF-8 encoding
- Incomplete sessions
- Missing timestamps
- Edge cases
"""

import json
import pytest
from pathlib import Path
from datetime import datetime
from smart_fork.session_parser import SessionParser, SessionMessage, SessionData


@pytest.fixture
def temp_session_file(tmp_path):
    """Create a temporary session file for testing."""
    def _create_file(content: str, filename: str = "test-session.jsonl"):
        file_path = tmp_path / filename
        file_path.write_text(content, encoding='utf-8')
        return file_path
    return _create_file


@pytest.fixture
def parser():
    """Create a SessionParser instance."""
    return SessionParser(strict=False)


@pytest.fixture
def strict_parser():
    """Create a strict SessionParser instance."""
    return SessionParser(strict=True)


class TestSessionMessage:
    """Test SessionMessage dataclass."""

    def test_valid_message(self):
        """Test creating a valid message."""
        msg = SessionMessage(
            role="user",
            content="Hello, world!",
            timestamp=datetime.now()
        )
        assert msg.role == "user"
        assert msg.content == "Hello, world!"
        assert msg.timestamp is not None

    def test_message_without_timestamp(self):
        """Test message without timestamp."""
        msg = SessionMessage(role="assistant", content="Hi there!")
        assert msg.role == "assistant"
        assert msg.content == "Hi there!"
        assert msg.timestamp is None

    def test_message_with_metadata(self):
        """Test message with metadata."""
        msg = SessionMessage(
            role="assistant",
            content="Response",
            metadata={"model": "claude-3", "tokens": 100}
        )
        assert msg.metadata["model"] == "claude-3"
        assert msg.metadata["tokens"] == 100

    def test_empty_role_raises_error(self):
        """Test that empty role raises ValueError."""
        with pytest.raises(ValueError, match="role cannot be empty"):
            SessionMessage(role="", content="test")

    def test_non_string_content_raises_error(self):
        """Test that non-string content raises ValueError."""
        with pytest.raises(ValueError, match="content must be a string"):
            SessionMessage(role="user", content=12345)


class TestSessionData:
    """Test SessionData dataclass."""

    def test_total_messages_calculated(self):
        """Test that total_messages is calculated correctly."""
        messages = [
            SessionMessage(role="user", content="msg1"),
            SessionMessage(role="assistant", content="msg2"),
            SessionMessage(role="user", content="msg3"),
        ]
        session = SessionData(
            session_id="test-123",
            messages=messages,
            file_path=Path("/tmp/test.jsonl")
        )
        assert session.total_messages == 3


class TestSessionParser:
    """Test SessionParser functionality."""

    def test_parse_valid_jsonl(self, parser, temp_session_file):
        """Test parsing a valid JSONL file."""
        content = '\n'.join([
            json.dumps({"role": "user", "content": "Hello"}),
            json.dumps({"role": "assistant", "content": "Hi there!"}),
            json.dumps({"role": "user", "content": "How are you?"}),
        ])
        file_path = temp_session_file(content)

        session = parser.parse_file(file_path)

        assert session.session_id == "test-session"
        assert session.total_messages == 3
        assert session.messages[0].role == "user"
        assert session.messages[0].content == "Hello"
        assert session.messages[1].role == "assistant"
        assert session.messages[1].content == "Hi there!"
        assert session.parse_errors == 0

    def test_parse_with_timestamps(self, parser, temp_session_file):
        """Test parsing messages with timestamps."""
        ts = "2024-01-20T10:30:00"
        content = '\n'.join([
            json.dumps({"role": "user", "content": "Test", "timestamp": ts}),
        ])
        file_path = temp_session_file(content)

        session = parser.parse_file(file_path)

        assert session.messages[0].timestamp is not None
        assert session.messages[0].timestamp.year == 2024

    def test_parse_with_unix_timestamp(self, parser, temp_session_file):
        """Test parsing messages with Unix timestamps."""
        unix_ts = 1705750200  # Jan 20, 2024
        content = json.dumps({"role": "user", "content": "Test", "timestamp": unix_ts})
        file_path = temp_session_file(content)

        session = parser.parse_file(file_path)

        assert session.messages[0].timestamp is not None
        assert session.messages[0].timestamp.year == 2024

    def test_parse_content_blocks(self, parser, temp_session_file):
        """Test parsing messages with content blocks."""
        content = json.dumps({
            "role": "assistant",
            "content": [
                {"type": "text", "text": "First block"},
                {"type": "text", "text": "Second block"}
            ]
        })
        file_path = temp_session_file(content)

        session = parser.parse_file(file_path)

        assert session.total_messages == 1
        assert "First block" in session.messages[0].content
        assert "Second block" in session.messages[0].content

    def test_parse_malformed_json_non_strict(self, parser, temp_session_file):
        """Test parsing with malformed JSON in non-strict mode."""
        content = '\n'.join([
            json.dumps({"role": "user", "content": "Valid message"}),
            '{invalid json here',
            json.dumps({"role": "assistant", "content": "Another valid message"}),
        ])
        file_path = temp_session_file(content)

        session = parser.parse_file(file_path)

        # Should skip the malformed line but continue
        assert session.total_messages == 2
        assert session.parse_errors == 1
        assert parser.stats['skipped_lines'] == 1

    def test_parse_malformed_json_strict(self, strict_parser, temp_session_file):
        """Test parsing with malformed JSON in strict mode."""
        content = '\n'.join([
            json.dumps({"role": "user", "content": "Valid message"}),
            '{invalid json here',
        ])
        file_path = temp_session_file(content)

        with pytest.raises(ValueError, match="Malformed JSON"):
            strict_parser.parse_file(file_path)

    def test_parse_empty_lines(self, parser, temp_session_file):
        """Test that empty lines are skipped."""
        content = '\n'.join([
            json.dumps({"role": "user", "content": "Message 1"}),
            '',
            '',
            json.dumps({"role": "assistant", "content": "Message 2"}),
            '',
        ])
        file_path = temp_session_file(content)

        session = parser.parse_file(file_path)

        assert session.total_messages == 2

    def test_parse_messages_without_role(self, parser, temp_session_file):
        """Test that messages without role are skipped."""
        content = '\n'.join([
            json.dumps({"role": "user", "content": "Valid"}),
            json.dumps({"content": "No role"}),  # Should be skipped
            json.dumps({"role": "assistant", "content": "Valid"}),
        ])
        file_path = temp_session_file(content)

        session = parser.parse_file(file_path)

        assert session.total_messages == 2

    def test_parse_messages_without_content(self, parser, temp_session_file):
        """Test that messages without content are skipped."""
        content = '\n'.join([
            json.dumps({"role": "user", "content": "Valid"}),
            json.dumps({"role": "user"}),  # No content
            json.dumps({"role": "assistant", "content": "Valid"}),
        ])
        file_path = temp_session_file(content)

        session = parser.parse_file(file_path)

        assert session.total_messages == 2

    def test_parse_alternative_content_fields(self, parser, temp_session_file):
        """Test parsing with alternative content field names."""
        content = '\n'.join([
            json.dumps({"role": "user", "text": "Using text field"}),
            json.dumps({"role": "assistant", "message": "Using message field"}),
        ])
        file_path = temp_session_file(content)

        session = parser.parse_file(file_path)

        assert session.total_messages == 2
        assert session.messages[0].content == "Using text field"
        assert session.messages[1].content == "Using message field"

    def test_parse_metadata_extraction(self, parser, temp_session_file):
        """Test that metadata is extracted correctly."""
        content = json.dumps({
            "role": "assistant",
            "content": "Response",
            "model": "claude-sonnet-4",
            "id": "msg_123",
            "usage": {"tokens": 150}
        })
        file_path = temp_session_file(content)

        session = parser.parse_file(file_path)

        msg = session.messages[0]
        assert msg.metadata is not None
        assert msg.metadata["model"] == "claude-sonnet-4"
        assert msg.metadata["id"] == "msg_123"
        assert msg.metadata["usage"]["tokens"] == 150

    def test_parse_file_not_found(self, parser):
        """Test that FileNotFoundError is raised for missing files."""
        with pytest.raises(FileNotFoundError):
            parser.parse_file(Path("/nonexistent/file.jsonl"))

    def test_session_id_from_filename(self, parser, temp_session_file):
        """Test that session ID is extracted from filename."""
        content = json.dumps({"role": "user", "content": "Test"})
        file_path = temp_session_file(content, "session-abc123.jsonl")

        session = parser.parse_file(file_path)

        assert session.session_id == "session-abc123"

    def test_file_metadata_extraction(self, parser, temp_session_file):
        """Test that file metadata is extracted."""
        content = json.dumps({"role": "user", "content": "Test"})
        file_path = temp_session_file(content)

        session = parser.parse_file(file_path)

        assert session.file_path == file_path
        assert session.last_modified is not None
        assert session.created_at is not None

    def test_parser_statistics(self, parser, temp_session_file):
        """Test that parser tracks statistics correctly."""
        parser.reset_stats()

        content1 = '\n'.join([
            json.dumps({"role": "user", "content": "Message 1"}),
            json.dumps({"role": "assistant", "content": "Message 2"}),
        ])
        file1 = temp_session_file(content1, "session1.jsonl")

        content2 = '\n'.join([
            json.dumps({"role": "user", "content": "Message 3"}),
            '{bad json',
        ])
        file2 = temp_session_file(content2, "session2.jsonl")

        parser.parse_file(file1)
        parser.parse_file(file2)

        stats = parser.get_stats()
        assert stats['files_parsed'] == 2
        assert stats['total_messages'] == 3
        assert stats['parse_errors'] == 1
        assert stats['skipped_lines'] == 1

    def test_utf8_encoding(self, parser, temp_session_file):
        """Test parsing files with UTF-8 characters."""
        content = json.dumps({
            "role": "user",
            "content": "Hello 世界! 🌍 Émojis and spëcial chars"
        })
        file_path = temp_session_file(content)

        session = parser.parse_file(file_path)

        assert session.total_messages == 1
        assert "世界" in session.messages[0].content
        assert "🌍" in session.messages[0].content
        assert "Émojis" in session.messages[0].content

    def test_incomplete_session_handling(self, parser, temp_session_file):
        """Test handling of incomplete/crashed sessions."""
        # Simulate a session that was writing but crashed mid-line
        content = '\n'.join([
            json.dumps({"role": "user", "content": "Message 1"}),
            json.dumps({"role": "assistant", "content": "Message 2"}),
            '{"role": "user", "content": "Incomplete',  # Incomplete JSON
        ])
        file_path = temp_session_file(content)

        session = parser.parse_file(file_path)

        # Should parse the valid messages and skip the incomplete one
        assert session.total_messages == 2
        assert session.parse_errors == 1

    def test_reset_statistics(self, parser, temp_session_file):
        """Test resetting parser statistics."""
        content = json.dumps({"role": "user", "content": "Test"})
        file_path = temp_session_file(content)

        parser.parse_file(file_path)
        assert parser.stats['files_parsed'] == 1

        parser.reset_stats()
        assert parser.stats['files_parsed'] == 0
        assert parser.stats['total_messages'] == 0

    def test_type_field_as_role(self, parser, temp_session_file):
        """Test using 'type' field as role."""
        content = json.dumps({
            "type": "user",
            "content": "Message using type field"
        })
        file_path = temp_session_file(content)

        session = parser.parse_file(file_path)

        assert session.total_messages == 1
        assert session.messages[0].role == "user"
