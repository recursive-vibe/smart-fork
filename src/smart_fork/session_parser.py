"""
Session file parser for Claude Code JSONL transcripts.

Parses .jsonl session files containing conversation history,
handling malformed lines and incomplete sessions gracefully.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class SessionMessage:
    """Represents a single message in a session."""

    role: str
    content: str
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate message after initialization."""
        if not self.role:
            raise ValueError("Message role cannot be empty")
        if not isinstance(self.content, str):
            raise ValueError("Message content must be a string")


@dataclass
class SessionData:
    """Represents a parsed session with all messages."""

    session_id: str
    messages: List[SessionMessage]
    file_path: Path
    created_at: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    total_messages: int = 0
    parse_errors: int = 0

    def __post_init__(self):
        """Calculate derived fields."""
        self.total_messages = len(self.messages)


class SessionParser:
    """
    Parser for Claude Code session files in JSONL format.

    Handles:
    - UTF-8 encoding
    - Malformed JSON lines (gracefully skipped with warnings)
    - Incomplete/crashed sessions
    - Missing or invalid timestamps
    """

    def __init__(self, strict: bool = False):
        """
        Initialize the session parser.

        Args:
            strict: If True, raise exceptions on parse errors.
                   If False, skip malformed lines and log warnings.
        """
        self.strict = strict
        self.stats = {
            'files_parsed': 0,
            'total_messages': 0,
            'parse_errors': 0,
            'skipped_lines': 0
        }

    def parse_file(self, file_path: Union[Path, str]) -> SessionData:
        """
        Parse a JSONL session file.

        Args:
            file_path: Path to the .jsonl session file

        Returns:
            SessionData object containing all parsed messages

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If strict mode and parse errors occur
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Session file not found: {file_path}")

        messages = []
        parse_errors = 0

        # Get file metadata
        stat = file_path.stat()
        last_modified = datetime.fromtimestamp(stat.st_mtime)

        # Extract session ID from filename (assume format: session-{id}.jsonl)
        session_id = file_path.stem

        logger.info(f"Parsing session file: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()

                    # Skip empty lines
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        message = self._parse_message(data)
                        if message:
                            messages.append(message)
                    except json.JSONDecodeError as e:
                        parse_errors += 1
                        self.stats['parse_errors'] += 1

                        error_msg = f"Malformed JSON at line {line_num}: {e}"
                        logger.warning(error_msg)

                        if self.strict:
                            raise ValueError(error_msg) from e

                        # Skip this line and continue
                        self.stats['skipped_lines'] += 1
                        continue
                    except Exception as e:
                        parse_errors += 1
                        self.stats['parse_errors'] += 1

                        error_msg = f"Error parsing line {line_num}: {e}"
                        logger.warning(error_msg)

                        if self.strict:
                            raise ValueError(error_msg) from e

                        self.stats['skipped_lines'] += 1
                        continue

        except UnicodeDecodeError as e:
            error_msg = f"UTF-8 decoding error in {file_path}: {e}"
            logger.error(error_msg)
            if self.strict:
                raise ValueError(error_msg) from e

        # Update stats
        self.stats['files_parsed'] += 1
        self.stats['total_messages'] += len(messages)

        # Infer creation time from first message or file creation time
        created_at = None
        if messages and messages[0].timestamp:
            created_at = messages[0].timestamp
        else:
            created_at = datetime.fromtimestamp(stat.st_ctime)

        session_data = SessionData(
            session_id=session_id,
            messages=messages,
            file_path=file_path,
            created_at=created_at,
            last_modified=last_modified,
            parse_errors=parse_errors
        )

        logger.info(
            f"Parsed {len(messages)} messages from {file_path} "
            f"({parse_errors} errors)"
        )

        return session_data

    def _parse_message(self, data: Dict[str, Any]) -> Optional[SessionMessage]:
        """
        Parse a single message from JSON data.

        Args:
            data: Dictionary containing message data

        Returns:
            SessionMessage or None if data is invalid
        """
        # Handle different possible message formats
        # Claude Code sessions may have various structures

        role = None
        content = None
        timestamp = None
        metadata = {}

        # Try to extract role
        if 'role' in data:
            role = data['role']
        elif 'type' in data:
            role = data['type']
        else:
            # Skip messages without a clear role
            logger.debug(f"Skipping message without role: {data.keys()}")
            return None

        # Try to extract content
        if 'content' in data:
            # Content might be a string or a list of content blocks
            content_data = data['content']
            if isinstance(content_data, str):
                content = content_data
            elif isinstance(content_data, list):
                # Concatenate all text content blocks
                text_parts = []
                for block in content_data:
                    if isinstance(block, dict) and 'text' in block:
                        text_parts.append(block['text'])
                    elif isinstance(block, str):
                        text_parts.append(block)
                content = '\n'.join(text_parts)
            else:
                content = str(content_data)
        elif 'text' in data:
            content = data['text']
        elif 'message' in data:
            # Handle nested message structure from Claude Code format
            msg = data['message']
            if isinstance(msg, dict):
                # Extract role from nested message if not already set
                if 'role' in msg:
                    role = msg['role']
                # Extract content from nested message
                if 'content' in msg:
                    content_data = msg['content']
                    if isinstance(content_data, str):
                        content = content_data
                    elif isinstance(content_data, list):
                        text_parts = []
                        for block in content_data:
                            if isinstance(block, dict) and 'text' in block:
                                text_parts.append(block['text'])
                            elif isinstance(block, str):
                                text_parts.append(block)
                        content = '\n'.join(text_parts) if text_parts else None
                    else:
                        content = str(content_data)
            else:
                content = str(msg)
        else:
            # Skip messages without content
            logger.debug(f"Skipping message without content: {data.keys()}")
            return None

        # Ensure content is a string
        if not isinstance(content, str):
            content = str(content)

        # Try to extract timestamp
        if 'timestamp' in data:
            try:
                ts_value = data['timestamp']
                if isinstance(ts_value, str):
                    # Try ISO format
                    timestamp = datetime.fromisoformat(ts_value.replace('Z', '+00:00'))
                elif isinstance(ts_value, (int, float)):
                    # Unix timestamp
                    timestamp = datetime.fromtimestamp(ts_value)
            except Exception as e:
                logger.debug(f"Could not parse timestamp: {e}")

        # Store any additional metadata
        for key in ['model', 'id', 'stop_reason', 'usage']:
            if key in data:
                metadata[key] = data[key]

        try:
            return SessionMessage(
                role=role,
                content=content,
                timestamp=timestamp,
                metadata=metadata if metadata else None
            )
        except ValueError as e:
            logger.warning(f"Invalid message data: {e}")
            return None

    def get_stats(self) -> Dict[str, int]:
        """Get parser statistics."""
        return self.stats.copy()

    def reset_stats(self):
        """Reset parser statistics."""
        self.stats = {
            'files_parsed': 0,
            'total_messages': 0,
            'parse_errors': 0,
            'skipped_lines': 0
        }
