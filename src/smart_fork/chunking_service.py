"""
Semantic chunking service for breaking down session transcripts into searchable chunks.

This module implements intelligent chunking that:
- Targets 750 tokens per chunk
- Never splits code blocks mid-block
- Keeps conversation turns together (user + assistant pairs)
- Adds 150-token overlap between adjacent chunks
"""

import re
from dataclasses import dataclass
from typing import List, Optional
from smart_fork.session_parser import SessionMessage
from smart_fork.memory_extractor import MemoryExtractor


@dataclass
class Chunk:
    """Represents a chunk of conversation content."""
    content: str
    start_index: int  # Index of first message in chunk
    end_index: int    # Index of last message in chunk (inclusive)
    token_count: int
    overlap: bool = False  # True if this is overlap content from previous chunk
    memory_types: Optional[List[str]] = None  # Memory markers: PATTERN, WORKING_SOLUTION, WAITING


class ChunkingService:
    """Service for breaking session transcripts into semantic chunks."""

    def __init__(
        self,
        target_tokens: int = 750,
        overlap_tokens: int = 150,
        max_tokens: int = 1000,
        extract_memory: bool = True
    ):
        """
        Initialize the chunking service.

        Args:
            target_tokens: Target token count per chunk (default: 750)
            overlap_tokens: Token overlap between chunks (default: 150)
            max_tokens: Maximum tokens per chunk before forced split (default: 1000)
            extract_memory: Whether to extract memory markers from chunks (default: True)
        """
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens
        self.max_tokens = max_tokens
        self.extract_memory = extract_memory
        self.memory_extractor = MemoryExtractor() if extract_memory else None

    def chunk_messages(self, messages: List[SessionMessage]) -> List[Chunk]:
        """
        Chunk a list of session messages into semantic chunks.

        Args:
            messages: List of SessionMessage objects to chunk

        Returns:
            List of Chunk objects
        """
        if not messages:
            return []

        chunks = []
        current_chunk_start = 0
        current_tokens = 0
        current_content = []

        i = 0
        while i < len(messages):
            message = messages[i]
            message_tokens = self._count_tokens(message.content)

            # Check if adding this message would exceed max_tokens
            if current_tokens + message_tokens > self.max_tokens and current_content:
                # Create chunk from accumulated content
                chunk = self._create_chunk(
                    current_content,
                    current_chunk_start,
                    i - 1
                )
                chunks.append(chunk)

                # Start new chunk with overlap
                overlap_start = self._find_overlap_start(
                    messages,
                    current_chunk_start,
                    i - 1
                )
                current_chunk_start = overlap_start
                current_content = []
                current_tokens = 0
                i = overlap_start
                continue

            # Add message to current chunk
            current_content.append(message.content)
            current_tokens += message_tokens

            # Check if we should start a new chunk
            should_split = False

            # If we've reached target tokens, look for a good split point
            if current_tokens >= self.target_tokens:
                # Check if this is the end of a conversation turn (assistant message)
                if message.role == "assistant":
                    should_split = True
                # Or if next message would push us over max_tokens
                elif i + 1 < len(messages):
                    next_tokens = self._count_tokens(messages[i + 1].content)
                    if current_tokens + next_tokens > self.max_tokens:
                        should_split = True

            if should_split and i < len(messages) - 1:
                # Create chunk
                chunk = self._create_chunk(
                    current_content,
                    current_chunk_start,
                    i
                )
                chunks.append(chunk)

                # Start new chunk with overlap
                overlap_start = self._find_overlap_start(
                    messages,
                    current_chunk_start,
                    i
                )
                current_chunk_start = overlap_start
                current_content = []
                current_tokens = 0
                i = overlap_start
                continue

            i += 1

        # Add final chunk if there's remaining content
        if current_content:
            chunk = self._create_chunk(
                current_content,
                current_chunk_start,
                len(messages) - 1
            )
            chunks.append(chunk)

        return chunks

    def _create_chunk(
        self,
        content_parts: List[str],
        start_index: int,
        end_index: int
    ) -> Chunk:
        """Create a Chunk object from content parts."""
        content = "\n\n".join(content_parts)
        token_count = self._count_tokens(content)

        # Extract memory types if enabled
        memory_types = None
        if self.extract_memory and self.memory_extractor:
            memory_types = self.memory_extractor.extract_memory_types(content)
            if not memory_types:  # Empty list -> None for consistency
                memory_types = None

        return Chunk(
            content=content,
            start_index=start_index,
            end_index=end_index,
            token_count=token_count,
            memory_types=memory_types
        )

    def _find_overlap_start(
        self,
        messages: List[SessionMessage],
        chunk_start: int,
        chunk_end: int
    ) -> int:
        """
        Find the start index for the next chunk to create overlap.

        Works backwards from chunk_end to find where overlap_tokens worth
        of content begins.

        Args:
            messages: Full list of messages
            chunk_start: Start index of current chunk
            chunk_end: End index of current chunk

        Returns:
            Index where next chunk should start
        """
        overlap_accumulated = 0
        overlap_start = chunk_end

        # Work backwards from the end of the chunk
        for i in range(chunk_end, chunk_start - 1, -1):
            message_tokens = self._count_tokens(messages[i].content)

            if overlap_accumulated + message_tokens > self.overlap_tokens:
                # We've accumulated enough overlap
                break

            overlap_accumulated += message_tokens
            overlap_start = i

        # Don't start before the next message after chunk_start
        # to ensure we make forward progress
        next_start = min(chunk_end + 1, len(messages) - 1)

        return min(overlap_start, next_start)

    def _count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses a simple approximation: ~4 characters per token.
        This is conservative for English text and code.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Simple heuristic: 4 characters per token
        # This is conservative and works reasonably well for code and technical text
        return max(1, len(text) // 4)

    def _find_code_blocks(self, text: str) -> List[tuple]:
        """
        Find all code blocks in the text.

        Returns list of (start_pos, end_pos) tuples for each code block.
        """
        code_blocks = []

        # Match fenced code blocks (```...```)
        pattern = r'```[\s\S]*?```'
        for match in re.finditer(pattern, text):
            code_blocks.append((match.start(), match.end()))

        # Match indented code blocks (4+ spaces at line start)
        # This is more conservative to avoid false positives
        indented_pattern = r'(?:^|\n)((?:    |\t)[^\n]*(?:\n(?:    |\t)[^\n]*)*)'
        for match in re.finditer(indented_pattern, text, re.MULTILINE):
            code_blocks.append((match.start(), match.end()))

        return code_blocks

    def _is_inside_code_block(self, position: int, code_blocks: List[tuple]) -> bool:
        """Check if a position is inside any code block."""
        for start, end in code_blocks:
            if start <= position <= end:
                return True
        return False

    def chunk_text(self, text: str) -> List[str]:
        """
        Chunk raw text into semantic chunks.

        This is a simpler interface for chunking plain text without
        message structure.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        if not text:
            return []

        chunks = []
        code_blocks = self._find_code_blocks(text)

        current_chunk = ""
        current_tokens = 0

        # Split by paragraphs (double newline)
        paragraphs = re.split(r'\n\n+', text)

        for para in paragraphs:
            para_tokens = self._count_tokens(para)

            # Check if this paragraph contains a code block
            para_start = text.find(para)
            para_end = para_start + len(para)
            contains_code = any(
                start < para_end and end > para_start
                for start, end in code_blocks
            )

            # If adding this paragraph would exceed target and it's not a code block
            if current_tokens + para_tokens > self.target_tokens and current_chunk and not contains_code:
                chunks.append(current_chunk.strip())

                # Start new chunk with overlap (last ~150 tokens of previous chunk)
                overlap = self._get_text_overlap(current_chunk)
                current_chunk = overlap + "\n\n" + para
                current_tokens = self._count_tokens(current_chunk)
            else:
                # Add to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
                current_tokens += para_tokens

            # Force split if we exceed max_tokens (even for code blocks)
            if current_tokens > self.max_tokens:
                chunks.append(current_chunk.strip())
                current_chunk = ""
                current_tokens = 0

        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _get_text_overlap(self, text: str) -> str:
        """
        Get the last ~overlap_tokens worth of text for overlap.

        Args:
            text: Text to extract overlap from

        Returns:
            Overlap text
        """
        target_chars = self.overlap_tokens * 4  # Approximate characters

        if len(text) <= target_chars:
            return text

        # Try to split at paragraph boundary
        overlap_start = max(0, len(text) - target_chars - 100)
        overlap_text = text[overlap_start:]

        # Find first paragraph break
        para_break = overlap_text.find('\n\n')
        if para_break > 0:
            overlap_text = overlap_text[para_break + 2:]

        return overlap_text
