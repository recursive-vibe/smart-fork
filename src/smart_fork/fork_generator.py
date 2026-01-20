"""
Fork command generator for dual-mode session forking.

This module generates fork commands in two modes:
1. New terminal mode: `claude --resume [id] --fork-session`
2. In-session mode: `/fork [id] [path]`
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import os

from .session_registry import SessionMetadata

logger = logging.getLogger(__name__)


@dataclass
class ForkCommand:
    """Represents a fork command with both modes."""
    session_id: str
    terminal_command: str
    in_session_command: str
    session_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ForkGenerator:
    """
    Generates fork commands for resuming sessions in dual modes.

    Supports:
    - New terminal fork: claude --resume [id] --fork-session
    - In-session fork: /fork [id] [path]
    """

    def __init__(self, claude_sessions_dir: str = "~/.claude"):
        """
        Initialize the ForkGenerator.

        Args:
            claude_sessions_dir: Directory where Claude session files are stored
        """
        self.claude_sessions_dir = os.path.expanduser(claude_sessions_dir)
        logger.info(f"Initialized ForkGenerator with sessions_dir: {self.claude_sessions_dir}")

    def find_session_path(self, session_id: str, project: Optional[str] = None) -> Optional[str]:
        """
        Find the file path for a session.

        Args:
            session_id: Session ID to find
            project: Optional project name to narrow search

        Returns:
            Full path to session file, or None if not found
        """
        # Try common patterns
        patterns = []

        if project:
            # Try project-specific path
            patterns.append(os.path.join(self.claude_sessions_dir, "projects", project, f"{session_id}.jsonl"))

        # Try direct path
        patterns.append(os.path.join(self.claude_sessions_dir, f"{session_id}.jsonl"))

        # Try sessions subdirectory
        patterns.append(os.path.join(self.claude_sessions_dir, "sessions", f"{session_id}.jsonl"))

        # Check each pattern
        for path in patterns:
            if os.path.exists(path):
                logger.info(f"Found session file at: {path}")
                return path

        # If not found, construct likely path based on project
        if project:
            likely_path = os.path.join(self.claude_sessions_dir, "projects", project, f"{session_id}.jsonl")
        else:
            likely_path = os.path.join(self.claude_sessions_dir, f"{session_id}.jsonl")

        logger.warning(f"Session file not found, using likely path: {likely_path}")
        return likely_path

    def generate_terminal_command(self, session_id: str) -> str:
        """
        Generate new terminal fork command.

        Args:
            session_id: Session ID to fork

        Returns:
            Terminal command string
        """
        return f"claude --resume {session_id} --fork-session"

    def generate_in_session_command(self, session_id: str, session_path: str) -> str:
        """
        Generate in-session fork command.

        Args:
            session_id: Session ID to fork
            session_path: Full path to session file

        Returns:
            In-session command string
        """
        return f"/fork {session_id} {session_path}"

    def format_metadata(self, metadata: Optional[SessionMetadata]) -> str:
        """
        Format session metadata for display.

        Args:
            metadata: Session metadata to format

        Returns:
            Formatted metadata string
        """
        if not metadata:
            return "No metadata available"

        lines = []
        lines.append(f"Project: {metadata.project or 'Unknown'}")

        # Format timestamps
        try:
            created_dt = datetime.fromisoformat(metadata.created_at.replace('Z', '+00:00'))
            lines.append(f"Created: {created_dt.strftime('%Y-%m-%d %H:%M')}")
        except (ValueError, AttributeError):
            lines.append(f"Created: {metadata.created_at}")

        lines.append(f"Messages: {metadata.message_count}")
        lines.append(f"Chunks: {metadata.chunk_count}")

        if metadata.tags:
            lines.append(f"Tags: {', '.join(metadata.tags)}")

        return "\n".join(lines)

    def generate_fork_command(
        self,
        session_id: str,
        metadata: Optional[SessionMetadata] = None
    ) -> ForkCommand:
        """
        Generate fork commands for a session.

        Args:
            session_id: Session ID to fork
            metadata: Optional session metadata

        Returns:
            ForkCommand object with both command modes
        """
        logger.info(f"Generating fork commands for session: {session_id}")

        # Find session file path
        project = metadata.project if metadata else None
        session_path = self.find_session_path(session_id, project)

        # Generate both commands
        terminal_cmd = self.generate_terminal_command(session_id)
        in_session_cmd = self.generate_in_session_command(session_id, session_path)

        # Convert metadata to dict if provided
        metadata_dict = None
        if metadata:
            metadata_dict = {
                'project': metadata.project,
                'created_at': metadata.created_at,
                'message_count': metadata.message_count,
                'chunk_count': metadata.chunk_count,
                'tags': metadata.tags or []
            }

        fork_cmd = ForkCommand(
            session_id=session_id,
            terminal_command=terminal_cmd,
            in_session_command=in_session_cmd,
            session_path=session_path,
            metadata=metadata_dict
        )

        logger.info(f"Generated fork commands successfully")
        return fork_cmd

    def format_fork_output(
        self,
        fork_command: ForkCommand,
        execution_time: Optional[float] = None
    ) -> str:
        """
        Format fork command output for display.

        Args:
            fork_command: Fork command to format
            execution_time: Optional execution time in seconds

        Returns:
            Formatted output string
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"Fork Command Generated: {fork_command.session_id}")
        lines.append("=" * 80)
        lines.append("")

        # Display metadata if available
        if fork_command.metadata:
            lines.append("Session Details:")
            lines.append("-" * 80)
            metadata_obj = SessionMetadata(
                session_id=fork_command.session_id,
                project=fork_command.metadata.get('project'),
                created_at=fork_command.metadata.get('created_at', ''),
                last_synced=fork_command.metadata.get('created_at', ''),
                message_count=fork_command.metadata.get('message_count', 0),
                chunk_count=fork_command.metadata.get('chunk_count', 0),
                tags=fork_command.metadata.get('tags', [])
            )
            lines.append(self.format_metadata(metadata_obj))
            lines.append("")

        # Display fork commands
        lines.append("Fork Commands:")
        lines.append("-" * 80)
        lines.append("")
        lines.append("Option 1: New Terminal Fork")
        lines.append(f"  {fork_command.terminal_command}")
        lines.append("")
        lines.append("Option 2: In-Session Fork")
        lines.append(f"  {fork_command.in_session_command}")
        lines.append("")
        lines.append("=" * 80)

        # Add execution time if provided
        if execution_time is not None:
            if execution_time < 60:
                time_str = f"{execution_time:.0f}s"
            else:
                minutes = int(execution_time // 60)
                seconds = int(execution_time % 60)
                time_str = f"{minutes}m {seconds}s"

            lines.append(f"✨ Generated in {time_str}")

        return "\n".join(lines)

    def generate_and_format(
        self,
        session_id: str,
        metadata: Optional[SessionMetadata] = None,
        execution_time: Optional[float] = None
    ) -> str:
        """
        Generate fork command and format output in one step.

        Args:
            session_id: Session ID to fork
            metadata: Optional session metadata
            execution_time: Optional execution time in seconds

        Returns:
            Formatted fork command output
        """
        fork_cmd = self.generate_fork_command(session_id, metadata)
        return self.format_fork_output(fork_cmd, execution_time)
