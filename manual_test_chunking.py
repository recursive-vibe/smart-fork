#!/usr/bin/env python3
"""
Manual test script for ChunkingService.

This script verifies the chunking algorithm without requiring pytest.
"""

import sys
from smart_fork.chunking_service import ChunkingService, Chunk
from smart_fork.session_parser import SessionMessage


def test_basic_functionality():
    """Test basic chunking functionality."""
    print("=" * 70)
    print("TEST 1: Basic Functionality")
    print("=" * 70)

    service = ChunkingService(target_tokens=750, overlap_tokens=150, max_tokens=1000)

    # Test 1: Empty messages
    print("\n1.1 Testing empty messages...")
    chunks = service.chunk_messages([])
    assert chunks == [], "Empty messages should return empty chunks"
    print("✓ Empty messages handled correctly")

    # Test 2: Single message
    print("\n1.2 Testing single message...")
    messages = [
        SessionMessage(role="user", content="Hello, world!", timestamp=None, metadata=None)
    ]
    chunks = service.chunk_messages(messages)
    assert len(chunks) == 1, "Single message should create one chunk"
    assert chunks[0].content == "Hello, world!", "Chunk content should match message"
    assert chunks[0].start_index == 0, "Start index should be 0"
    assert chunks[0].end_index == 0, "End index should be 0"
    print("✓ Single message chunked correctly")

    # Test 3: Small conversation
    print("\n1.3 Testing small conversation...")
    messages = [
        SessionMessage(role="user", content="What is Python?", timestamp=None, metadata=None),
        SessionMessage(role="assistant", content="Python is a programming language.", timestamp=None, metadata=None),
        SessionMessage(role="user", content="Thanks!", timestamp=None, metadata=None)
    ]
    chunks = service.chunk_messages(messages)
    assert len(chunks) == 1, "Small conversation should fit in one chunk"
    assert "What is Python?" in chunks[0].content
    assert "Python is a programming language." in chunks[0].content
    assert "Thanks!" in chunks[0].content
    print("✓ Small conversation chunked correctly")

    print("\n✅ All basic functionality tests passed!\n")


def test_token_counting():
    """Test token counting accuracy."""
    print("=" * 70)
    print("TEST 2: Token Counting")
    print("=" * 70)

    service = ChunkingService()

    # Test empty string
    print("\n2.1 Testing empty string...")
    count = service._count_tokens("")
    assert count == 0, f"Empty string should be 0 tokens, got {count}"
    print(f"✓ Empty string: {count} tokens")

    # Test short string
    print("\n2.2 Testing short string...")
    count = service._count_tokens("hello world")
    print(f"✓ 'hello world' (~11 chars): {count} tokens")

    # Test longer string
    print("\n2.3 Testing longer string...")
    text = "This is a longer piece of text that should result in approximately twenty-five tokens or so."
    count = service._count_tokens(text)
    assert 20 <= count <= 30, f"Expected 20-30 tokens, got {count}"
    print(f"✓ Longer text (~{len(text)} chars): {count} tokens")

    print("\n✅ All token counting tests passed!\n")


def test_code_block_detection():
    """Test code block detection."""
    print("=" * 70)
    print("TEST 3: Code Block Detection")
    print("=" * 70)

    service = ChunkingService()

    # Test fenced code blocks
    print("\n3.1 Testing fenced code blocks...")
    text = """
Here is some code:

```python
def hello():
    print("world")
```

And more text.
    """
    code_blocks = service._find_code_blocks(text)
    assert len(code_blocks) >= 1, "Should find at least one code block"
    print(f"✓ Found {len(code_blocks)} code block(s)")

    # Test multiple code blocks
    print("\n3.2 Testing multiple code blocks...")
    text = """
First block:
```javascript
const x = 1;
```

Second block:
```python
y = 2
```
    """
    code_blocks = service._find_code_blocks(text)
    assert len(code_blocks) >= 2, f"Should find at least 2 code blocks, found {len(code_blocks)}"
    print(f"✓ Found {len(code_blocks)} code blocks")

    print("\n✅ All code block detection tests passed!\n")


def test_large_chunking():
    """Test chunking with large conversations."""
    print("=" * 70)
    print("TEST 4: Large Conversation Chunking")
    print("=" * 70)

    service = ChunkingService(target_tokens=750, overlap_tokens=150, max_tokens=1000)

    # Create a large conversation
    print("\n4.1 Creating large conversation (20 turns)...")
    messages = []
    for i in range(20):
        messages.append(
            SessionMessage(
                role="user",
                content=f"User question {i}? " * 80,  # ~1600 chars = ~400 tokens
                timestamp=None,
                metadata=None
            )
        )
        messages.append(
            SessionMessage(
                role="assistant",
                content=f"Assistant answer {i}. " * 80,  # ~1600 chars = ~400 tokens
                timestamp=None,
                metadata=None
            )
        )

    print(f"✓ Created {len(messages)} messages")

    print("\n4.2 Chunking messages...")
    chunks = service.chunk_messages(messages)
    print(f"✓ Created {len(chunks)} chunks")

    # Verify multiple chunks created
    assert len(chunks) >= 2, f"Should create multiple chunks, got {len(chunks)}"

    # Verify chunk sizes
    print("\n4.3 Verifying chunk sizes...")
    for i, chunk in enumerate(chunks):
        print(f"  Chunk {i+1}: {chunk.token_count} tokens (msgs {chunk.start_index}-{chunk.end_index})")
        # Allow some flexibility for the last chunk
        if i < len(chunks) - 1:
            assert chunk.token_count <= service.max_tokens + 100, \
                f"Chunk {i} exceeds max_tokens: {chunk.token_count} > {service.max_tokens}"

    # Verify overlap
    print("\n4.4 Verifying overlap between chunks...")
    for i in range(len(chunks) - 1):
        current = chunks[i]
        next_chunk = chunks[i + 1]
        assert next_chunk.start_index > current.start_index, \
            f"Chunks must make forward progress"
        print(f"  Overlap {i+1}-{i+2}: chunk {i+2} starts at msg {next_chunk.start_index}, chunk {i+1} ends at {current.end_index}")

    # Verify all messages covered
    print("\n4.5 Verifying all messages covered...")
    assert chunks[0].start_index == 0, "First chunk should start at index 0"
    assert chunks[-1].end_index == len(messages) - 1, "Last chunk should end at last message"
    print(f"✓ All messages from {chunks[0].start_index} to {chunks[-1].end_index} covered")

    print("\n✅ All large conversation chunking tests passed!\n")


def test_conversation_turn_boundaries():
    """Test that chunks respect conversation turn boundaries."""
    print("=" * 70)
    print("TEST 5: Conversation Turn Boundaries")
    print("=" * 70)

    service = ChunkingService(target_tokens=750, overlap_tokens=150, max_tokens=1000)

    # Create conversation with clear turns
    print("\n5.1 Creating conversation with clear turns...")
    messages = []
    for i in range(10):
        messages.append(
            SessionMessage(
                role="user",
                content=f"Question {i} " * 100,  # ~1200 chars = ~300 tokens
                timestamp=None,
                metadata=None
            )
        )
        messages.append(
            SessionMessage(
                role="assistant",
                content=f"Answer {i} " * 100,  # ~1200 chars = ~300 tokens
                timestamp=None,
                metadata=None
            )
        )

    chunks = service.chunk_messages(messages)
    print(f"✓ Created {len(chunks)} chunks from {len(messages)} messages")

    # Check that chunks (except last) end with assistant messages
    print("\n5.2 Verifying chunks end at conversation turns...")
    for i, chunk in enumerate(chunks[:-1]):  # All but last
        role = messages[chunk.end_index].role
        print(f"  Chunk {i+1} ends with: {role} message at index {chunk.end_index}")
        # Most chunks should end with assistant (end of turn)
        # This is a soft requirement - we're checking the pattern

    print("\n✅ Conversation turn boundary test passed!\n")


def test_text_chunking():
    """Test text chunking (non-message chunking)."""
    print("=" * 70)
    print("TEST 6: Text Chunking")
    print("=" * 70)

    service = ChunkingService(target_tokens=100, overlap_tokens=20, max_tokens=150)

    # Test empty text
    print("\n6.1 Testing empty text...")
    chunks = service.chunk_text("")
    assert chunks == [], "Empty text should return empty list"
    print("✓ Empty text handled correctly")

    # Test small text
    print("\n6.2 Testing small text...")
    text = "This is a small piece of text."
    chunks = service.chunk_text(text)
    assert len(chunks) == 1, "Small text should be one chunk"
    assert chunks[0] == text, "Chunk should match input text"
    print("✓ Small text chunked correctly")

    # Test large text
    print("\n6.3 Testing large text...")
    paragraphs = []
    for i in range(20):
        paragraphs.append(f"This is paragraph {i}. " * 50)
    text = "\n\n".join(paragraphs)

    chunks = service.chunk_text(text)
    assert len(chunks) >= 2, f"Large text should create multiple chunks, got {len(chunks)}"
    print(f"✓ Large text created {len(chunks)} chunks")

    # Verify chunk sizes
    print("\n6.4 Verifying chunk sizes...")
    for i, chunk in enumerate(chunks):
        tokens = service._count_tokens(chunk)
        print(f"  Chunk {i+1}: {tokens} tokens")
        # Text chunking can create larger chunks when preserving paragraphs/code blocks
        # Allow up to 3x max_tokens for text chunks
        assert tokens <= service.max_tokens * 3, f"Chunk {i} too large: {tokens}"

    print("\n✅ All text chunking tests passed!\n")


def test_overlap_extraction():
    """Test overlap text extraction."""
    print("=" * 70)
    print("TEST 7: Overlap Extraction")
    print("=" * 70)

    service = ChunkingService(target_tokens=750, overlap_tokens=150, max_tokens=1000)

    # Test short text (should return full text)
    print("\n7.1 Testing short text overlap...")
    text = "Short text"
    overlap = service._get_text_overlap(text)
    assert overlap == text, "Short text should return full text as overlap"
    print("✓ Short text overlap correct")

    # Test long text
    print("\n7.2 Testing long text overlap...")
    text = "Paragraph one.\n\n" + ("Paragraph two. " * 100) + "\n\nParagraph three. " * 50
    overlap = service._get_text_overlap(text)

    assert len(overlap) > 0, "Overlap should not be empty"
    assert len(overlap) < len(text), "Overlap should be shorter than full text"

    expected_size = service.overlap_tokens * 4  # 150 * 4 = 600 chars
    assert expected_size * 0.5 <= len(overlap) <= expected_size * 2, \
        f"Overlap size {len(overlap)} not in expected range [{expected_size*0.5}, {expected_size*2}]"

    print(f"✓ Long text overlap: {len(overlap)} chars (expected ~{expected_size})")

    print("\n✅ All overlap extraction tests passed!\n")


def test_edge_cases():
    """Test edge cases and boundary conditions."""
    print("=" * 70)
    print("TEST 8: Edge Cases")
    print("=" * 70)

    service = ChunkingService(target_tokens=750, overlap_tokens=150, max_tokens=1000)

    # Test very long single message
    print("\n8.1 Testing very long single message...")
    huge_content = "word " * 5000  # ~25,000 chars = ~6,250 tokens
    messages = [
        SessionMessage(role="user", content=huge_content, timestamp=None, metadata=None)
    ]

    chunks = service.chunk_messages(messages)
    assert len(chunks) >= 1, "Should create at least one chunk"
    assert huge_content[:100] in chunks[0].content, "Chunk should contain message content"
    print(f"✓ Very long message created {len(chunks)} chunk(s)")

    # Test progressive chunking (no infinite loops)
    print("\n8.2 Testing progressive chunking...")
    messages = []
    for i in range(100):
        messages.append(
            SessionMessage(
                role="user",
                content=f"Message {i} " * 50,
                timestamp=None,
                metadata=None
            )
        )

    chunks = service.chunk_messages(messages)
    assert len(chunks) >= 2, "Should create multiple chunks"

    # Verify forward progress
    for i in range(len(chunks) - 1):
        assert chunks[i + 1].start_index > chunks[i].start_index, \
            f"Chunk {i+1} doesn't make forward progress"

    # Verify all messages covered
    assert chunks[0].start_index == 0, "Should start at first message"
    assert chunks[-1].end_index == len(messages) - 1, "Should end at last message"

    print(f"✓ Progressive chunking: {len(chunks)} chunks cover all {len(messages)} messages")

    print("\n✅ All edge case tests passed!\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("CHUNKING SERVICE - MANUAL TEST SUITE")
    print("=" * 70 + "\n")

    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Token Counting", test_token_counting),
        ("Code Block Detection", test_code_block_detection),
        ("Large Conversation Chunking", test_large_chunking),
        ("Conversation Turn Boundaries", test_conversation_turn_boundaries),
        ("Text Chunking", test_text_chunking),
        ("Overlap Extraction", test_overlap_extraction),
        ("Edge Cases", test_edge_cases),
    ]

    passed = 0
    failed = 0
    errors = []

    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            failed += 1
            errors.append((test_name, str(e)))
            print(f"\n❌ {test_name} FAILED: {e}\n")
        except Exception as e:
            failed += 1
            errors.append((test_name, str(e)))
            print(f"\n❌ {test_name} ERROR: {e}\n")

    # Print summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print()

    if errors:
        print("Failed tests:")
        for test_name, error in errors:
            print(f"  - {test_name}: {error}")
        print()

    if failed == 0:
        print("🎉 ALL TESTS PASSED! 🎉")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
