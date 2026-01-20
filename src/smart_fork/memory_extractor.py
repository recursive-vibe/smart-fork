"""
Memory marker extraction service for detecting Claude memory types in session content.

This module implements detection of Claude's memory markers:
- PATTERN: Design patterns, architectural solutions
- WORKING_SOLUTION: Proven implementations, successful code
- WAITING: Async operations, pending items, things to resume

Memory markers are extracted from session content and stored in chunk metadata
to enable memory-based score boosting during search.
"""

import re
from typing import List, Set, Optional
from dataclasses import dataclass


@dataclass
class MemoryMarker:
    """Represents a detected memory marker in content."""
    memory_type: str  # PATTERN, WORKING_SOLUTION, or WAITING
    context: str      # Surrounding text context
    position: int     # Character position in content


class MemoryExtractor:
    """
    Service for extracting Claude memory markers from session content.

    Detects three types of memory markers:
    - PATTERN: Design patterns, architectural patterns, solution patterns
    - WORKING_SOLUTION: Proven implementations, successful solutions, working code
    - WAITING: Async operations, pending tasks, things to resume later
    """

    # Memory marker patterns
    PATTERN_KEYWORDS = [
        r'\bpattern\b',
        r'\bdesign pattern\b',
        r'\barchitectural pattern\b',
        r'\bsolution pattern\b',
        r'\bapproach\b',
        r'\bstrategy\b',
        r'\barchitecture\b',
    ]

    WORKING_SOLUTION_KEYWORDS = [
        r'\bworking solution\b',
        r'\bproven implementation\b',
        r'\bsuccessful\b',
        r'\btested\b',
        r'\bverified\b',
        r'\bworks correctly\b',
        r'\bimplementation complete\b',
        r'\ball tests pass\b',
    ]

    WAITING_KEYWORDS = [
        r'\bwaiting\b',
        r'\bpending\b',
        r'\bto be completed\b',
        r'\bresume later\b',
        r'\bin progress\b',
        r'\bto do\b',
        r'\btodo\b',
        r'\bblocked\b',
    ]

    def __init__(self, context_window: int = 100):
        """
        Initialize the MemoryExtractor.

        Args:
            context_window: Number of characters to extract around marker for context
        """
        self.context_window = context_window

        # Compile regex patterns for efficiency
        self.pattern_regex = re.compile(
            '|'.join(self.PATTERN_KEYWORDS),
            re.IGNORECASE
        )
        self.working_solution_regex = re.compile(
            '|'.join(self.WORKING_SOLUTION_KEYWORDS),
            re.IGNORECASE
        )
        self.waiting_regex = re.compile(
            '|'.join(self.WAITING_KEYWORDS),
            re.IGNORECASE
        )

    def extract_memory_types(self, content: str) -> List[str]:
        """
        Extract all memory types present in the content.

        Args:
            content: The text content to analyze

        Returns:
            List of unique memory types found (e.g., ['PATTERN', 'WORKING_SOLUTION'])
        """
        memory_types = set()

        if self.pattern_regex.search(content):
            memory_types.add('PATTERN')

        if self.working_solution_regex.search(content):
            memory_types.add('WORKING_SOLUTION')

        if self.waiting_regex.search(content):
            memory_types.add('WAITING')

        return sorted(list(memory_types))  # Sort for consistent ordering

    def extract_markers(self, content: str) -> List[MemoryMarker]:
        """
        Extract all memory markers with their context and positions.

        Args:
            content: The text content to analyze

        Returns:
            List of MemoryMarker objects with type, context, and position
        """
        markers = []

        # Find PATTERN markers
        for match in self.pattern_regex.finditer(content):
            context = self._extract_context(content, match.start())
            markers.append(MemoryMarker(
                memory_type='PATTERN',
                context=context,
                position=match.start()
            ))

        # Find WORKING_SOLUTION markers
        for match in self.working_solution_regex.finditer(content):
            context = self._extract_context(content, match.start())
            markers.append(MemoryMarker(
                memory_type='WORKING_SOLUTION',
                context=context,
                position=match.start()
            ))

        # Find WAITING markers
        for match in self.waiting_regex.finditer(content):
            context = self._extract_context(content, match.start())
            markers.append(MemoryMarker(
                memory_type='WAITING',
                context=context,
                position=match.start()
            ))

        # Sort by position
        markers.sort(key=lambda m: m.position)

        return markers

    def _extract_context(self, content: str, position: int) -> str:
        """
        Extract context window around a marker position.

        Args:
            content: The full text content
            position: Character position of the marker

        Returns:
            Context string around the marker
        """
        start = max(0, position - self.context_window)
        end = min(len(content), position + self.context_window)

        context = content[start:end].strip()

        # Add ellipsis if truncated
        if start > 0:
            context = '...' + context
        if end < len(content):
            context = context + '...'

        return context

    def has_memory_type(self, content: str, memory_type: str) -> bool:
        """
        Check if content contains a specific memory type.

        Args:
            content: The text content to analyze
            memory_type: The memory type to check for (PATTERN, WORKING_SOLUTION, WAITING)

        Returns:
            True if the memory type is present, False otherwise
        """
        memory_type = memory_type.upper()

        if memory_type == 'PATTERN':
            return self.pattern_regex.search(content) is not None
        elif memory_type == 'WORKING_SOLUTION':
            return self.working_solution_regex.search(content) is not None
        elif memory_type == 'WAITING':
            return self.waiting_regex.search(content) is not None
        else:
            return False

    def get_memory_boost(self, memory_types: List[str]) -> float:
        """
        Calculate total memory boost for a list of memory types.

        Memory type boosts (from PRD):
        - PATTERN: +5%
        - WORKING_SOLUTION: +8%
        - WAITING: +2%

        Args:
            memory_types: List of memory types present

        Returns:
            Total boost as a decimal (e.g., 0.13 for 13% boost)
        """
        boost = 0.0

        for memory_type in memory_types:
            if memory_type == 'PATTERN':
                boost += 0.05
            elif memory_type == 'WORKING_SOLUTION':
                boost += 0.08
            elif memory_type == 'WAITING':
                boost += 0.02

        return boost

    def extract_from_messages(self, messages: List[dict]) -> List[str]:
        """
        Extract memory types from a list of session messages.

        Args:
            messages: List of message dictionaries with 'content' field

        Returns:
            List of unique memory types found across all messages
        """
        memory_types = set()

        for message in messages:
            content = message.get('content', '')
            if isinstance(content, str):
                types = self.extract_memory_types(content)
                memory_types.update(types)

        return sorted(list(memory_types))
