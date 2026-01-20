#!/usr/bin/env python3
"""
Manual test runner for SessionParser.

Since pytest cannot be installed due to network restrictions,
this script manually runs tests to verify the parser implementation.
"""

import json
import sys
import tempfile
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from smart_fork.session_parser import SessionParser, SessionMessage, SessionData


def test_session_message():
    """Test SessionMessage creation."""
    print("Testing SessionMessage...")

    # Valid message
    msg = SessionMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"
    print("✓ Valid message creation")

    # Message with metadata
    msg2 = SessionMessage(
        role="assistant",
        content="Hi",
        metadata={"model": "claude-3"}
    )
    assert msg2.metadata["model"] == "claude-3"
    print("✓ Message with metadata")

    # Empty role should fail
    try:
        SessionMessage(role="", content="test")
        assert False, "Should have raised ValueError"
    except ValueError:
        print("✓ Empty role validation")

    # Non-string content should fail
    try:
        SessionMessage(role="user", content=123)
        assert False, "Should have raised ValueError"
    except ValueError:
        print("✓ Non-string content validation")


def test_valid_jsonl_parsing():
    """Test parsing valid JSONL."""
    print("\nTesting valid JSONL parsing...")

    parser = SessionParser()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({"role": "user", "content": "Hello"}) + '\n')
        f.write(json.dumps({"role": "assistant", "content": "Hi there!"}) + '\n')
        f.write(json.dumps({"role": "user", "content": "How are you?"}) + '\n')
        temp_path = f.name

    try:
        session = parser.parse_file(temp_path)
        assert session.total_messages == 3
        assert session.messages[0].role == "user"
        assert session.messages[0].content == "Hello"
        assert session.messages[1].content == "Hi there!"
        assert session.parse_errors == 0
        print(f"✓ Parsed {session.total_messages} messages correctly")
    finally:
        Path(temp_path).unlink()


def test_malformed_json_handling():
    """Test handling of malformed JSON."""
    print("\nTesting malformed JSON handling...")

    parser = SessionParser(strict=False)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({"role": "user", "content": "Valid 1"}) + '\n')
        f.write('{invalid json here\n')
        f.write(json.dumps({"role": "assistant", "content": "Valid 2"}) + '\n')
        temp_path = f.name

    try:
        session = parser.parse_file(temp_path)
        assert session.total_messages == 2, f"Expected 2 messages, got {session.total_messages}"
        assert session.parse_errors == 1
        print(f"✓ Skipped malformed line, parsed {session.total_messages} valid messages")
    finally:
        Path(temp_path).unlink()


def test_timestamps():
    """Test timestamp parsing."""
    print("\nTesting timestamp parsing...")

    parser = SessionParser()

    # ISO format timestamp
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({
            "role": "user",
            "content": "Test",
            "timestamp": "2024-01-20T10:30:00"
        }) + '\n')
        temp_path = f.name

    try:
        session = parser.parse_file(temp_path)
        assert session.messages[0].timestamp is not None
        assert session.messages[0].timestamp.year == 2024
        print("✓ ISO format timestamp parsed")
    finally:
        Path(temp_path).unlink()

    # Unix timestamp
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({
            "role": "user",
            "content": "Test",
            "timestamp": 1705750200
        }) + '\n')
        temp_path = f.name

    try:
        session = parser.parse_file(temp_path)
        assert session.messages[0].timestamp is not None
        print("✓ Unix timestamp parsed")
    finally:
        Path(temp_path).unlink()


def test_content_blocks():
    """Test parsing content blocks."""
    print("\nTesting content blocks...")

    parser = SessionParser()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({
            "role": "assistant",
            "content": [
                {"type": "text", "text": "First block"},
                {"type": "text", "text": "Second block"}
            ]
        }) + '\n')
        temp_path = f.name

    try:
        session = parser.parse_file(temp_path)
        assert "First block" in session.messages[0].content
        assert "Second block" in session.messages[0].content
        print("✓ Content blocks concatenated correctly")
    finally:
        Path(temp_path).unlink()


def test_empty_lines():
    """Test that empty lines are skipped."""
    print("\nTesting empty line handling...")

    parser = SessionParser()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({"role": "user", "content": "Message 1"}) + '\n')
        f.write('\n')
        f.write('\n')
        f.write(json.dumps({"role": "assistant", "content": "Message 2"}) + '\n')
        temp_path = f.name

    try:
        session = parser.parse_file(temp_path)
        assert session.total_messages == 2
        print("✓ Empty lines skipped correctly")
    finally:
        Path(temp_path).unlink()


def test_utf8_encoding():
    """Test UTF-8 character support."""
    print("\nTesting UTF-8 encoding...")

    parser = SessionParser()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        f.write(json.dumps({
            "role": "user",
            "content": "Hello 世界! 🌍 Émojis and spëcial chars"
        }) + '\n')
        temp_path = f.name

    try:
        session = parser.parse_file(temp_path)
        assert "世界" in session.messages[0].content
        assert "🌍" in session.messages[0].content
        assert "Émojis" in session.messages[0].content
        print("✓ UTF-8 characters handled correctly")
    finally:
        Path(temp_path).unlink()


def test_metadata_extraction():
    """Test metadata extraction."""
    print("\nTesting metadata extraction...")

    parser = SessionParser()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({
            "role": "assistant",
            "content": "Response",
            "model": "claude-sonnet-4",
            "id": "msg_123",
            "usage": {"tokens": 150}
        }) + '\n')
        temp_path = f.name

    try:
        session = parser.parse_file(temp_path)
        msg = session.messages[0]
        assert msg.metadata is not None
        assert msg.metadata["model"] == "claude-sonnet-4"
        assert msg.metadata["id"] == "msg_123"
        print("✓ Metadata extracted correctly")
    finally:
        Path(temp_path).unlink()


def test_parser_statistics():
    """Test parser statistics tracking."""
    print("\nTesting parser statistics...")

    parser = SessionParser()
    parser.reset_stats()

    # Create two files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({"role": "user", "content": "Message 1"}) + '\n')
        f.write(json.dumps({"role": "assistant", "content": "Message 2"}) + '\n')
        temp1 = f.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({"role": "user", "content": "Message 3"}) + '\n')
        f.write('{bad json\n')
        temp2 = f.name

    try:
        parser.parse_file(temp1)
        parser.parse_file(temp2)

        stats = parser.get_stats()
        assert stats['files_parsed'] == 2
        assert stats['total_messages'] == 3
        assert stats['parse_errors'] == 1
        print(f"✓ Statistics tracked: {stats}")
    finally:
        Path(temp1).unlink()
        Path(temp2).unlink()


def test_alternative_content_fields():
    """Test alternative content field names."""
    print("\nTesting alternative content fields...")

    parser = SessionParser()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({"role": "user", "text": "Using text field"}) + '\n')
        f.write(json.dumps({"role": "assistant", "message": "Using message field"}) + '\n')
        temp_path = f.name

    try:
        session = parser.parse_file(temp_path)
        assert session.total_messages == 2
        assert session.messages[0].content == "Using text field"
        assert session.messages[1].content == "Using message field"
        print("✓ Alternative content fields handled")
    finally:
        Path(temp_path).unlink()


def test_incomplete_session():
    """Test handling of incomplete/crashed sessions."""
    print("\nTesting incomplete session handling...")

    parser = SessionParser(strict=False)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        f.write(json.dumps({"role": "user", "content": "Message 1"}) + '\n')
        f.write(json.dumps({"role": "assistant", "content": "Message 2"}) + '\n')
        f.write('{"role": "user", "content": "Incomplete\n')  # Incomplete JSON
        temp_path = f.name

    try:
        session = parser.parse_file(temp_path)
        assert session.total_messages == 2
        assert session.parse_errors == 1
        print("✓ Incomplete session handled gracefully")
    finally:
        Path(temp_path).unlink()


def main():
    """Run all tests."""
    print("=" * 60)
    print("SessionParser Manual Test Suite")
    print("=" * 60)

    tests_passed = 0
    tests_failed = 0

    tests = [
        test_session_message,
        test_valid_jsonl_parsing,
        test_malformed_json_handling,
        test_timestamps,
        test_content_blocks,
        test_empty_lines,
        test_utf8_encoding,
        test_metadata_extraction,
        test_parser_statistics,
        test_alternative_content_fields,
        test_incomplete_session,
    ]

    for test in tests:
        try:
            test()
            tests_passed += 1
        except Exception as e:
            print(f"✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            tests_failed += 1

    print("\n" + "=" * 60)
    print(f"Tests passed: {tests_passed}/{len(tests)}")
    print(f"Tests failed: {tests_failed}/{len(tests)}")
    print("=" * 60)

    return 0 if tests_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
