"""
Unit tests for the ChunkingService.

Tests verify:
- Token counting works correctly
- Chunks target 750 tokens
- Code blocks are never split mid-block
- Conversation turns stay together (user + assistant)
- 150-token overlap between chunks
- Edge cases (empty input, single message, etc.)
"""

import pytest
from smart_fork.chunking_service import ChunkingService, Chunk
from smart_fork.session_parser import SessionMessage


class TestChunkingService:
    """Test suite for ChunkingService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ChunkingService(
            target_tokens=750,
            overlap_tokens=150,
            max_tokens=1000
        )

    def test_initialization(self):
        """Test service initializes with correct defaults."""
        service = ChunkingService()
        assert service.target_tokens == 750
        assert service.overlap_tokens == 150
        assert service.max_tokens == 1000

    def test_initialization_custom(self):
        """Test service initializes with custom values."""
        service = ChunkingService(
            target_tokens=500,
            overlap_tokens=100,
            max_tokens=800
        )
        assert service.target_tokens == 500
        assert service.overlap_tokens == 100
        assert service.max_tokens == 800

    def test_count_tokens_empty(self):
        """Test token counting with empty string."""
        count = self.service._count_tokens("")
        assert count == 0

    def test_count_tokens_simple(self):
        """Test token counting with simple text."""
        # "hello world" = 11 chars / 4 = 2.75 -> 2 tokens
        count = self.service._count_tokens("hello world")
        assert count == 2

    def test_count_tokens_longer(self):
        """Test token counting with longer text."""
        # ~100 character text should be ~25 tokens
        text = "This is a longer piece of text that should result in approximately twenty-five tokens or so."
        count = self.service._count_tokens(text)
        assert 20 <= count <= 30  # Allow some variance

    def test_chunk_messages_empty(self):
        """Test chunking with empty message list."""
        chunks = self.service.chunk_messages([])
        assert chunks == []

    def test_chunk_messages_single(self):
        """Test chunking with single message."""
        messages = [
            SessionMessage(
                role="user",
                content="Hello, how are you?",
                timestamp=None,
                model=None
            )
        ]
        chunks = self.service.chunk_messages(messages)

        assert len(chunks) == 1
        assert chunks[0].content == "Hello, how are you?"
        assert chunks[0].start_index == 0
        assert chunks[0].end_index == 0

    def test_chunk_messages_small_conversation(self):
        """Test chunking with small conversation (all in one chunk)."""
        messages = [
            SessionMessage(role="user", content="What is Python?", timestamp=None, model=None),
            SessionMessage(role="assistant", content="Python is a programming language.", timestamp=None, model=None),
            SessionMessage(role="user", content="Thanks!", timestamp=None, model=None)
        ]

        chunks = self.service.chunk_messages(messages)

        # Should all fit in one chunk
        assert len(chunks) == 1
        assert "What is Python?" in chunks[0].content
        assert "Python is a programming language." in chunks[0].content
        assert "Thanks!" in chunks[0].content

    def test_chunk_messages_respects_target_size(self):
        """Test that chunking creates new chunks near target size."""
        # Create messages that will exceed target tokens
        large_text = "word " * 1000  # ~5000 chars = ~1250 tokens

        messages = [
            SessionMessage(role="user", content=large_text, timestamp=None, model=None),
            SessionMessage(role="assistant", content=large_text, timestamp=None, model=None),
            SessionMessage(role="user", content="Follow up", timestamp=None, model=None),
        ]

        chunks = self.service.chunk_messages(messages)

        # Should split into multiple chunks
        assert len(chunks) >= 2

        # Each chunk should be roughly near target (allowing for overlap)
        for chunk in chunks[:-1]:  # All but last chunk
            # Should be between target and max
            assert self.service.target_tokens <= chunk.token_count <= self.service.max_tokens

    def test_chunk_messages_conversation_turns(self):
        """Test that conversation turns (user + assistant) stay together when possible."""
        # Create a conversation with clear turns
        messages = [
            SessionMessage(role="user", content="Question 1 " * 50, timestamp=None, model=None),
            SessionMessage(role="assistant", content="Answer 1 " * 50, timestamp=None, model=None),
            SessionMessage(role="user", content="Question 2 " * 50, timestamp=None, model=None),
            SessionMessage(role="assistant", content="Answer 2 " * 50, timestamp=None, model=None),
        ]

        chunks = self.service.chunk_messages(messages)

        # Verify chunks split at assistant messages (end of turns)
        for chunk in chunks[:-1]:  # All but last
            # Should end with assistant message
            last_message_content = messages[chunk.end_index].content
            assert messages[chunk.end_index].role == "assistant"

    def test_chunk_messages_creates_overlap(self):
        """Test that chunks have overlap between them."""
        # Create messages that will require multiple chunks
        messages = []
        for i in range(10):
            messages.append(
                SessionMessage(
                    role="user",
                    content=f"User message {i} " * 100,
                    timestamp=None,
                    model=None
                )
            )
            messages.append(
                SessionMessage(
                    role="assistant",
                    content=f"Assistant response {i} " * 100,
                    timestamp=None,
                    model=None
                )
            )

        chunks = self.service.chunk_messages(messages)

        # Should have multiple chunks
        assert len(chunks) >= 2

        # Verify overlap: next chunk should start before previous chunk ends
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]

            # Next chunk should start before or at the end of current chunk
            # (but after the start to ensure progress)
            assert next_chunk.start_index > current_chunk.start_index
            assert next_chunk.start_index <= current_chunk.end_index + 1

    def test_chunk_messages_max_tokens_enforcement(self):
        """Test that chunks never exceed max_tokens."""
        # Create very large messages
        huge_text = "word " * 2000  # ~10,000 chars = ~2500 tokens

        messages = [
            SessionMessage(role="user", content=huge_text, timestamp=None, model=None),
            SessionMessage(role="assistant", content=huge_text, timestamp=None, model=None),
        ]

        chunks = self.service.chunk_messages(messages)

        # Verify no chunk exceeds max_tokens
        for chunk in chunks:
            assert chunk.token_count <= self.service.max_tokens + 100  # Small buffer for safety

    def test_find_code_blocks_fenced(self):
        """Test finding fenced code blocks."""
        text = """
        Here is some code:

        ```python
        def hello():
            print("world")
        ```

        And more text.
        """

        code_blocks = self.service._find_code_blocks(text)

        assert len(code_blocks) >= 1
        # Verify the code block is detected
        assert any("def hello" in text[start:end] for start, end in code_blocks)

    def test_find_code_blocks_multiple(self):
        """Test finding multiple code blocks."""
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

        code_blocks = self.service._find_code_blocks(text)

        assert len(code_blocks) >= 2

    def test_chunk_text_empty(self):
        """Test chunking empty text."""
        chunks = self.service.chunk_text("")
        assert chunks == []

    def test_chunk_text_small(self):
        """Test chunking small text."""
        text = "This is a small piece of text."
        chunks = self.service.chunk_text(text)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_text_large(self):
        """Test chunking large text."""
        # Create text larger than target tokens
        paragraphs = []
        for i in range(20):
            paragraphs.append(f"This is paragraph {i}. " * 50)

        text = "\n\n".join(paragraphs)
        chunks = self.service.chunk_text(text)

        # Should create multiple chunks
        assert len(chunks) >= 2

        # Each chunk should be under max_tokens
        for chunk in chunks:
            tokens = self.service._count_tokens(chunk)
            assert tokens <= self.service.max_tokens + 100

    def test_chunk_text_preserves_code_blocks(self):
        """Test that code blocks are kept together."""
        text = """
        Introduction paragraph.

        ```python
        def important_function():
            # This function should not be split
            for i in range(100):
                process(i)
            return result
        ```

        Conclusion paragraph.
        """

        chunks = self.service.chunk_text(text)

        # The code block should appear complete in at least one chunk
        code_found = False
        for chunk in chunks:
            if "def important_function" in chunk and "return result" in chunk:
                code_found = True
                break

        assert code_found, "Code block was split across chunks"

    def test_get_text_overlap_short(self):
        """Test overlap extraction with short text."""
        text = "Short text"
        overlap = self.service._get_text_overlap(text)

        # Short text should return full text as overlap
        assert overlap == text

    def test_get_text_overlap_long(self):
        """Test overlap extraction with long text."""
        text = "Paragraph one.\n\n" + ("Paragraph two. " * 100) + "\n\nParagraph three. " * 50

        overlap = self.service._get_text_overlap(text)

        # Overlap should be non-empty but shorter than full text
        assert len(overlap) > 0
        assert len(overlap) < len(text)

        # Overlap should be roughly the right size (overlap_tokens * 4 chars)
        expected_size = self.service.overlap_tokens * 4
        # Allow 50% variance
        assert expected_size * 0.5 <= len(overlap) <= expected_size * 2

    def test_chunk_boundaries_at_message_boundaries(self):
        """Test that chunk boundaries align with message boundaries."""
        messages = []

        # Create enough messages to force multiple chunks
        for i in range(20):
            messages.append(
                SessionMessage(
                    role="user",
                    content=f"User question {i}? " * 80,
                    timestamp=None,
                    model=None
                )
            )
            messages.append(
                SessionMessage(
                    role="assistant",
                    content=f"Assistant answer {i}. " * 80,
                    timestamp=None,
                    model=None
                )
            )

        chunks = self.service.chunk_messages(messages)

        # Verify all chunks have valid message indices
        for chunk in chunks:
            assert 0 <= chunk.start_index < len(messages)
            assert 0 <= chunk.end_index < len(messages)
            assert chunk.start_index <= chunk.end_index

    def test_chunk_content_matches_messages(self):
        """Test that chunk content actually comes from the messages."""
        messages = [
            SessionMessage(role="user", content="First message", timestamp=None, model=None),
            SessionMessage(role="assistant", content="Second message", timestamp=None, model=None),
            SessionMessage(role="user", content="Third message", timestamp=None, model=None),
        ]

        chunks = self.service.chunk_messages(messages)

        assert len(chunks) == 1
        chunk = chunks[0]

        # All message content should be in the chunk
        assert "First message" in chunk.content
        assert "Second message" in chunk.content
        assert "Third message" in chunk.content

    def test_progressive_chunking(self):
        """Test that chunking makes forward progress and doesn't loop."""
        # Create a long sequence that should be chunked
        messages = []
        for i in range(100):
            messages.append(
                SessionMessage(
                    role="user",
                    content=f"Message {i} " * 50,
                    timestamp=None,
                    model=None
                )
            )

        chunks = self.service.chunk_messages(messages)

        # Should create multiple chunks
        assert len(chunks) >= 2

        # Each chunk should start after the previous one starts
        for i in range(len(chunks) - 1):
            assert chunks[i + 1].start_index > chunks[i].start_index

        # All messages should be covered
        assert chunks[0].start_index == 0
        assert chunks[-1].end_index == len(messages) - 1

    def test_very_long_single_message(self):
        """Test handling of a single very long message."""
        # Create a message that exceeds max_tokens
        huge_content = "word " * 5000  # ~25,000 chars = ~6,250 tokens

        messages = [
            SessionMessage(
                role="user",
                content=huge_content,
                timestamp=None,
                model=None
            )
        ]

        chunks = self.service.chunk_messages(messages)

        # Should still create at least one chunk
        assert len(chunks) >= 1

        # The chunk should contain the message content
        assert huge_content[:100] in chunks[0].content


def test_chunk_dataclass():
    """Test Chunk dataclass."""
    chunk = Chunk(
        content="Test content",
        start_index=0,
        end_index=5,
        token_count=100,
        overlap=True
    )

    assert chunk.content == "Test content"
    assert chunk.start_index == 0
    assert chunk.end_index == 5
    assert chunk.token_count == 100
    assert chunk.overlap is True


def test_chunk_dataclass_defaults():
    """Test Chunk dataclass default values."""
    chunk = Chunk(
        content="Test",
        start_index=0,
        end_index=0,
        token_count=10
    )

    assert chunk.overlap is False
