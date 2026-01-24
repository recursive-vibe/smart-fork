"""
Initial database setup flow for Smart Fork.

This module handles the first-run experience, scanning existing Claude Code sessions
and building the initial vector database and session registry.

Supports two modes:
- Standard mode: Process all sessions in a single process (may use lots of memory)
- Batch mode (--batch-mode): Process sessions in batches, spawning fresh Python
  processes between batches to fully release memory. Recommended for large
  session counts (>100 sessions).
"""

import gc
import os
import sys
import subprocess
import time
import json
import logging
import signal
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from .session_parser import SessionParser
from .chunking_service import ChunkingService
from .embedding_service import EmbeddingService
from .vector_db_service import VectorDBService
from .session_registry import SessionRegistry, SessionMetadata
from .config_manager import ConfigManager

logger = logging.getLogger(__name__)


def _format_time(seconds: float) -> str:
    """
    Format seconds into a human-readable time string.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted time string (e.g., "2m 30s", "1h 15m")
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"


def _format_bytes(num_bytes: int) -> str:
    """
    Format bytes into a human-readable size string.

    Args:
        num_bytes: Size in bytes

    Returns:
        Formatted size string (e.g., "1.5 MB", "512 KB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def default_progress_callback(progress: 'SetupProgress') -> None:
    """
    Default console progress callback.

    Displays progress information to stdout, including:
    - Current file being processed
    - Progress counter (X of Y files)
    - Percentage complete
    - Elapsed time
    - Estimated time remaining
    - Cache statistics (on completion)

    Args:
        progress: Progress information
    """
    if progress.is_complete:
        # Final completion message
        print(f"\n✓ Setup complete!")
        print(f"  Processed: {progress.processed_files} files")
        print(f"  Total chunks: {progress.total_chunks}")
        print(f"  Time elapsed: {_format_time(progress.elapsed_time)}")

        # Display cache statistics if available
        if progress.cache_stats:
            print(f"\n  Embedding cache statistics:")
            print(f"    Total entries: {progress.cache_stats.get('total_entries', 0)}")
            print(f"    Cache hits: {progress.cache_stats.get('hits', 0)}")
            print(f"    Cache misses: {progress.cache_stats.get('misses', 0)}")
            print(f"    Hit rate: {progress.cache_stats.get('hit_rate', '0.00%')}")
    elif progress.error:
        # Error message
        print(f"\n✗ Error: {progress.error}")
    else:
        # Progress update
        percent = (progress.processed_files / progress.total_files * 100) if progress.total_files > 0 else 0
        print(f"Indexing session {progress.processed_files + 1} of {progress.total_files} ({percent:.1f}%)", end='')

        if progress.current_file:
            print(f" - {progress.current_file}", end='')

        if progress.elapsed_time > 0:
            print(f" | Elapsed: {_format_time(progress.elapsed_time)}", end='')

        if progress.estimated_remaining > 0:
            print(f" | ETA: {_format_time(progress.estimated_remaining)}", end='')

        print()  # New line


@dataclass
class SetupProgress:
    """Progress information for setup process."""
    total_files: int
    processed_files: int
    current_file: str
    total_chunks: int
    elapsed_time: float
    estimated_remaining: float
    is_complete: bool = False
    error: Optional[str] = None
    cache_stats: Optional[Dict[str, Any]] = None


@dataclass
class SetupState:
    """Persistent state for resuming interrupted setup."""
    total_files: int
    processed_files: List[str]
    timed_out_files: List[str]
    started_at: float
    last_updated: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'SetupState':
        """Create from dictionary."""
        # Handle old state files without timed_out_files
        if 'timed_out_files' not in data:
            data['timed_out_files'] = []
        return SetupState(**data)


class InitialSetup:
    """
    Manages the initial database setup flow.

    Responsibilities:
    - Detect first-run (no ~/.smart-fork/ directory)
    - Scan ~/.claude/ for all existing session files
    - Display progress with estimated time remaining
    - Support graceful interruption and resume
    - Create session registry on completion
    """

    def __init__(
        self,
        storage_dir: str = "~/.smart-fork",
        claude_dir: str = "~/.claude",
        progress_callback: Optional[Callable[[SetupProgress], None]] = None,
        show_progress: bool = True,
        timeout_per_session: float = 30.0,
        workers: int = 1
    ):
        """
        Initialize the setup manager.

        Args:
            storage_dir: Directory for Smart Fork data
            claude_dir: Directory containing Claude Code sessions
            progress_callback: Optional callback for progress updates
            show_progress: Whether to show default console progress (default: True)
            timeout_per_session: Timeout in seconds for processing each session (default: 30.0)
            workers: Number of worker threads for parallel processing (default: 1)
        """
        self.storage_dir = Path(storage_dir).expanduser()
        self.claude_dir = Path(claude_dir).expanduser()
        self.timeout_per_session = timeout_per_session
        self.workers = max(1, workers)  # Ensure at least 1 worker

        # Use default progress callback if none provided and show_progress is True
        if progress_callback is None and show_progress:
            self.progress_callback = default_progress_callback
        else:
            self.progress_callback = progress_callback

        self.state_file = self.storage_dir / "setup_state.json"
        self.session_parser = SessionParser()
        self.chunking_service = ChunkingService()

        # Services will be initialized during setup
        self.embedding_service: Optional[EmbeddingService] = None
        self.vector_db_service: Optional[VectorDBService] = None
        self.session_registry: Optional[SessionRegistry] = None

        self._interrupted = False
        self._progress_lock = threading.Lock()  # Lock for thread-safe progress updates
        self._state_lock = threading.Lock()  # Lock for thread-safe state updates

    def is_first_run(self) -> bool:
        """
        Check if this is the first run (no storage directory exists).

        Returns:
            True if this is the first run
        """
        return not self.storage_dir.exists()

    def has_incomplete_setup(self) -> bool:
        """
        Check if there's an incomplete setup that can be resumed.

        Returns:
            True if there's a setup state file
        """
        return self.state_file.exists()

    def _find_session_files(self) -> List[Path]:
        """
        Find all session JSONL files in the Claude directory.

        Returns:
            List of session file paths
        """
        if not self.claude_dir.exists():
            logger.warning(f"Claude directory not found: {self.claude_dir}")
            return []

        session_files = []

        # Search for .jsonl files recursively
        for jsonl_file in self.claude_dir.rglob("*.jsonl"):
            # Skip files that are too small (likely empty or invalid)
            if jsonl_file.stat().st_size > 100:
                session_files.append(jsonl_file)

        logger.info(f"Found {len(session_files)} session files")
        return sorted(session_files)

    def _load_state(self) -> Optional[SetupState]:
        """
        Load setup state from disk.

        Returns:
            SetupState if found, None otherwise
        """
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
            return SetupState.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load setup state: {e}")
            return None

    def _save_state(self, state: SetupState) -> None:
        """
        Save setup state to disk.

        Args:
            state: State to save
        """
        try:
            # Ensure directory exists
            self.storage_dir.mkdir(parents=True, exist_ok=True)

            # Write to temporary file first
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(state.to_dict(), f, indent=2)

            # Atomic rename
            temp_file.rename(self.state_file)
        except Exception as e:
            logger.error(f"Failed to save setup state: {e}")

    def _delete_state(self) -> None:
        """Delete the setup state file."""
        try:
            if self.state_file.exists():
                self.state_file.unlink()
        except Exception as e:
            logger.error(f"Failed to delete setup state: {e}")

    def _initialize_services(self) -> None:
        """Initialize all required services."""
        logger.info("Initializing services...")

        # Create storage directory
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.load()

        # Initialize services (with caching enabled by default)
        # Use cache directory within storage_dir for isolation
        cache_dir = str(self.storage_dir / "embedding_cache")
        self.embedding_service = EmbeddingService(
            model_name=config.embedding.model_name,
            min_batch_size=config.embedding.min_batch_size,
            max_batch_size=config.embedding.max_batch_size,
            throttle_seconds=config.embedding.throttle_seconds,
            use_mps=config.embedding.use_mps,
            use_cache=True,
            cache_dir=cache_dir
        )
        self.vector_db_service = VectorDBService(
            persist_directory=str(self.storage_dir / "vector_db")
        )
        self.session_registry = SessionRegistry(
            registry_path=str(self.storage_dir / "session-registry.json")
        )

    def _process_session_file_with_timeout(
        self,
        file_path: Path,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a single session file with timeout.

        Args:
            file_path: Path to session file
            session_id: Optional session ID (derived from filename if not provided)

        Returns:
            Dictionary with processing results
        """
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._process_session_file, file_path, session_id)
                return future.result(timeout=self.timeout_per_session)
        except FuturesTimeoutError:
            session_id = session_id or file_path.stem
            file_size = file_path.stat().st_size
            logger.warning(
                f"Session {session_id} timed out after {self.timeout_per_session}s "
                f"(file size: {_format_bytes(file_size)})"
            )
            return {
                'session_id': session_id,
                'success': False,
                'error': f'Timeout after {self.timeout_per_session}s',
                'chunks': 0,
                'timed_out': True
            }
        except Exception as e:
            session_id = session_id or file_path.stem
            logger.error(f"Unexpected error processing session {session_id}: {e}")
            return {
                'session_id': session_id,
                'success': False,
                'error': str(e),
                'chunks': 0,
                'timed_out': False
            }

    def _process_session_file(
        self,
        file_path: Path,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a single session file.

        Args:
            file_path: Path to session file
            session_id: Optional session ID (derived from filename if not provided)

        Returns:
            Dictionary with processing results
        """
        if session_id is None:
            session_id = file_path.stem

        try:
            # Parse session
            session_data = self.session_parser.parse_file(str(file_path))

            if not session_data.messages:
                logger.warning(f"No messages in session {session_id}")
                return {
                    'session_id': session_id,
                    'success': False,
                    'error': 'No messages found',
                    'chunks': 0
                }

            # Chunk messages
            chunks = self.chunking_service.chunk_messages(session_data.messages)

            if not chunks:
                logger.warning(f"No chunks generated for session {session_id}")
                return {
                    'session_id': session_id,
                    'success': False,
                    'error': 'No chunks generated',
                    'chunks': 0
                }

            # Extract text from chunks
            chunk_texts = [chunk.content for chunk in chunks]

            # Generate embeddings
            embeddings = self.embedding_service.embed_texts(chunk_texts)

            # Prepare chunks for vector DB
            chunk_ids = []
            chunk_metadata = []
            for i, chunk in enumerate(chunks):
                chunk_ids.append(f"{session_id}_{i}")
                metadata = {
                    'session_id': session_id,
                    'chunk_index': i,
                    'start_index': chunk.start_index,
                    'end_index': chunk.end_index
                }
                # Add memory_types if present
                if chunk.memory_types:
                    metadata['memory_types'] = chunk.memory_types
                chunk_metadata.append(metadata)

            # Add to vector database
            self.vector_db_service.add_chunks(
                chunks=chunk_texts,
                embeddings=embeddings,
                metadata=chunk_metadata,
                chunk_ids=chunk_ids
            )

            # Add to session registry
            project = self._extract_project(file_path)
            # Convert datetime to ISO string for JSON serialization
            created_at = None
            if session_data.messages and session_data.messages[0].timestamp:
                ts = session_data.messages[0].timestamp
                # Handle both datetime objects and ISO strings
                if isinstance(ts, str):
                    created_at = ts
                else:
                    created_at = ts.isoformat()

            session_metadata = SessionMetadata(
                session_id=session_id,
                project=project,
                created_at=created_at,
                chunk_count=len(chunks),
                message_count=len(session_data.messages),
                tags=[]
            )
            self.session_registry.add_session(session_id, session_metadata)

            return {
                'session_id': session_id,
                'success': True,
                'chunks': len(chunks),
                'messages': len(session_data.messages)
            }

        except Exception as e:
            logger.error(f"Error processing session {session_id}: {e}")
            return {
                'session_id': session_id,
                'success': False,
                'error': str(e),
                'chunks': 0
            }

    def _extract_project(self, file_path: Path) -> str:
        """
        Extract project name from file path.

        Args:
            file_path: Path to session file

        Returns:
            Project name
        """
        # Try to get project from parent directory name
        # Typical structure: ~/.claude/projects/{project_name}/sessions/{session_id}.jsonl
        parts = file_path.parts
        if 'projects' in parts:
            idx = parts.index('projects')
            if idx + 1 < len(parts):
                return parts[idx + 1]

        # Default to "unknown"
        return "unknown"

    def _estimate_remaining_time(
        self,
        processed: int,
        total: int,
        elapsed: float
    ) -> float:
        """
        Estimate remaining time based on current progress.

        Args:
            processed: Number of files processed
            total: Total number of files
            elapsed: Elapsed time in seconds

        Returns:
            Estimated remaining time in seconds
        """
        if processed == 0:
            return 0.0

        avg_time_per_file = elapsed / processed
        remaining_files = total - processed
        return avg_time_per_file * remaining_files

    def _notify_progress(
        self,
        total: int,
        processed: int,
        current_file: str,
        total_chunks: int,
        start_time: float,
        is_complete: bool = False,
        error: Optional[str] = None,
        cache_stats: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Notify progress callback.

        Args:
            total: Total number of files
            processed: Number of files processed
            current_file: Current file being processed
            total_chunks: Total chunks processed
            start_time: Start time of setup
            is_complete: Whether setup is complete
            error: Optional error message
            cache_stats: Optional cache statistics (on completion)
        """
        if self.progress_callback is None:
            return

        elapsed = time.time() - start_time
        estimated_remaining = self._estimate_remaining_time(processed, total, elapsed)

        progress = SetupProgress(
            total_files=total,
            processed_files=processed,
            current_file=current_file,
            total_chunks=total_chunks,
            elapsed_time=elapsed,
            estimated_remaining=estimated_remaining,
            is_complete=is_complete,
            error=error,
            cache_stats=cache_stats
        )

        self.progress_callback(progress)

    def interrupt(self) -> None:
        """Signal that setup should be interrupted gracefully."""
        self._interrupted = True
        logger.info("Setup interrupted by user")

    def _process_files_sequential(
        self,
        files_to_process: List[Path],
        all_files: List[Path],
        state: SetupState,
        start_time: float
    ) -> Dict[str, Any]:
        """
        Process files sequentially (single-threaded).

        Args:
            files_to_process: List of files to process
            all_files: All session files (for progress tracking)
            state: Setup state object
            start_time: Start time of setup

        Returns:
            Dictionary with processing results
        """
        total_chunks = 0
        errors = []
        timeouts = []

        for file_path in files_to_process:
            # Check for interruption
            if self._interrupted:
                logger.info("Setup interrupted, saving state...")
                self._save_state(state)
                return {
                    'total_chunks': total_chunks,
                    'errors': errors,
                    'timeouts': timeouts,
                    'interrupted': True
                }

            # Notify progress
            self._notify_progress(
                total=len(all_files),
                processed=len(state.processed_files),
                current_file=file_path.name,
                total_chunks=total_chunks,
                start_time=start_time
            )

            # Process file with timeout
            result = self._process_session_file_with_timeout(file_path)

            # Update state and statistics
            file_str = str(file_path)
            if result['success']:
                total_chunks += result['chunks']
                state.processed_files.append(file_str)
            elif result.get('timed_out', False):
                state.timed_out_files.append(file_str)
                state.processed_files.append(file_str)
                timeouts.append({
                    'file': file_path.name,
                    'error': result.get('error', 'Unknown timeout'),
                    'file_size': _format_bytes(file_path.stat().st_size)
                })
            else:
                errors.append({
                    'file': file_path.name,
                    'error': result.get('error', 'Unknown error')
                })

            # Update state
            state.last_updated = time.time()
            self._save_state(state)

            # Memory management: run garbage collection after each session
            gc.collect()

            # More aggressive cleanup every 10 sessions
            sessions_done = len(state.processed_files)
            if sessions_done % 10 == 0:
                gc.collect(generation=2)
                logger.debug(f"Full GC after {sessions_done} sessions")

            # Unload and reload embedding model every 50 sessions to free GPU/MPS memory
            if sessions_done % 50 == 0 and sessions_done > 0:
                logger.info(f"Unloading embedding model after {sessions_done} sessions to free memory")
                if self.embedding_service:
                    self.embedding_service.flush_cache()
                    self.embedding_service.unload_model()
                gc.collect()

        return {
            'total_chunks': total_chunks,
            'errors': errors,
            'timeouts': timeouts,
            'interrupted': False
        }

    def _process_files_parallel(
        self,
        files_to_process: List[Path],
        all_files: List[Path],
        state: SetupState,
        start_time: float
    ) -> Dict[str, Any]:
        """
        Process files in parallel using thread pool.

        Args:
            files_to_process: List of files to process
            all_files: All session files (for progress tracking)
            state: Setup state object
            start_time: Start time of setup

        Returns:
            Dictionary with processing results
        """
        total_chunks = 0
        errors = []
        timeouts = []

        # Process files using thread pool
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self._process_session_file_with_timeout, file_path): file_path
                for file_path in files_to_process
            }

            # Process results as they complete
            from concurrent.futures import as_completed
            for future in as_completed(future_to_file):
                # Check for interruption
                if self._interrupted:
                    logger.info("Setup interrupted, cancelling remaining tasks...")
                    # Cancel pending futures
                    for f in future_to_file:
                        f.cancel()
                    # Save state
                    with self._state_lock:
                        self._save_state(state)
                    return {
                        'total_chunks': total_chunks,
                        'errors': errors,
                        'timeouts': timeouts,
                        'interrupted': True
                    }

                file_path = future_to_file[future]
                result = future.result()

                # Update state and statistics with thread safety
                with self._state_lock:
                    file_str = str(file_path)
                    if result['success']:
                        total_chunks += result['chunks']
                        state.processed_files.append(file_str)
                    elif result.get('timed_out', False):
                        state.timed_out_files.append(file_str)
                        state.processed_files.append(file_str)
                        timeouts.append({
                            'file': file_path.name,
                            'error': result.get('error', 'Unknown timeout'),
                            'file_size': _format_bytes(file_path.stat().st_size)
                        })
                    else:
                        errors.append({
                            'file': file_path.name,
                            'error': result.get('error', 'Unknown error')
                        })

                    # Update state periodically
                    state.last_updated = time.time()
                    self._save_state(state)

                # Notify progress (with lock for thread safety)
                with self._progress_lock:
                    self._notify_progress(
                        total=len(all_files),
                        processed=len(state.processed_files),
                        current_file=file_path.name,
                        total_chunks=total_chunks,
                        start_time=start_time
                    )

                # Memory management: run garbage collection after each session
                gc.collect()

                # More aggressive cleanup every 10 sessions
                sessions_done = len(state.processed_files)
                if sessions_done % 10 == 0:
                    gc.collect(generation=2)
                    logger.debug(f"Full GC after {sessions_done} sessions")

                # Unload and reload embedding model every 50 sessions to free GPU/MPS memory
                if sessions_done % 50 == 0 and sessions_done > 0:
                    logger.info(f"Unloading embedding model after {sessions_done} sessions to free memory")
                    if self.embedding_service:
                        self.embedding_service.flush_cache()
                        self.embedding_service.unload_model()
                    gc.collect()

        return {
            'total_chunks': total_chunks,
            'errors': errors,
            'timeouts': timeouts,
            'interrupted': False
        }

    def run_setup(self, resume: bool = False, retry_timeouts: bool = False) -> Dict[str, Any]:
        """
        Run the initial setup process.

        Args:
            resume: Whether to resume from previous state
            retry_timeouts: Whether to retry timed-out sessions from previous run

        Returns:
            Dictionary with setup results
        """
        # Find all session files
        all_files = self._find_session_files()

        if not all_files:
            logger.warning("No session files found")
            return {
                'success': True,
                'files_processed': 0,
                'total_chunks': 0,
                'errors': [],
                'timeouts': [],
                'message': 'No session files found'
            }

        # Load or create state
        state = None
        if resume:
            state = self._load_state()

        if state is None:
            # New setup
            state = SetupState(
                total_files=len(all_files),
                processed_files=[],
                timed_out_files=[],
                started_at=time.time(),
                last_updated=time.time()
            )

        # If retry_timeouts flag is set, process timed-out files
        if retry_timeouts and state.timed_out_files:
            logger.info(f"Retrying {len(state.timed_out_files)} timed-out sessions...")
            # Move timed-out files back to pending (remove from both lists)
            files_to_retry = state.timed_out_files.copy()
            state.timed_out_files = []
            # Remove from processed files so they'll be reprocessed
            for file_str in files_to_retry:
                if file_str in state.processed_files:
                    state.processed_files.remove(file_str)

        # Initialize services
        self._initialize_services()

        # Get files to process (skip already processed)
        files_to_process = [
            file_path for file_path in all_files
            if str(file_path) not in state.processed_files
        ]

        logger.info(f"Processing {len(files_to_process)} sessions with {self.workers} worker(s)...")

        # Process files with thread pool
        start_time = state.started_at
        total_chunks = 0
        errors = []
        timeouts = []

        # Use single-threaded processing if workers=1 (backward compatible)
        if self.workers == 1:
            result = self._process_files_sequential(
                files_to_process, all_files, state, start_time
            )
        else:
            result = self._process_files_parallel(
                files_to_process, all_files, state, start_time
            )

        # Unpack results
        total_chunks = result['total_chunks']
        errors = result['errors']
        timeouts = result['timeouts']
        interrupted = result.get('interrupted', False)

        if interrupted:
            return {
                'success': False,
                'files_processed': len(state.processed_files),
                'total_chunks': total_chunks,
                'errors': errors,
                'timeouts': timeouts,
                'interrupted': True,
                'message': 'Setup interrupted, can be resumed later'
            }

        # Setup complete - flush embedding cache to disk
        if self.embedding_service:
            self.embedding_service.flush_cache()
            logger.info("Flushed embedding cache to disk")

        self._delete_state()

        # Get cache statistics
        cache_stats = {}
        if self.embedding_service:
            cache_stats = self.embedding_service.get_cache_stats()

        # Final progress notification
        self._notify_progress(
            total=len(all_files),
            processed=len(state.processed_files),
            current_file="",
            total_chunks=total_chunks,
            start_time=start_time,
            is_complete=True,
            cache_stats=cache_stats
        )

        result = {
            'success': True,
            'files_processed': len(state.processed_files) - len(timeouts),
            'total_chunks': total_chunks,
            'errors': errors,
            'timeouts': timeouts,
            'elapsed_time': time.time() - start_time,
            'cache_stats': cache_stats,
            'workers_used': self.workers
        }

        # Add helpful message about timeouts if any occurred
        if timeouts:
            result['message'] = (
                f"{len(timeouts)} session(s) timed out. "
                f"Run with retry_timeouts=True to retry them with a longer timeout."
            )

        return result


def run_single_batch(
    batch_size: int = 5,
    storage_dir: str = "~/.smart-fork",
    claude_dir: str = "~/.claude",
    timeout_per_session: float = 30.0,
    use_cpu: bool = True
) -> int:
    """
    Process a single batch of sessions.

    This function is designed to be called in a subprocess. It processes
    up to `batch_size` sessions and then exits, allowing memory to be
    fully released.

    Args:
        batch_size: Maximum number of sessions to process in this batch
        storage_dir: Directory for Smart Fork data (default: ~/.smart-fork)
        claude_dir: Directory containing Claude Code sessions
        timeout_per_session: Timeout in seconds for processing each session
        use_cpu: Force CPU mode (disable MPS/CUDA) to reduce memory usage

    Returns:
        Exit code: 0 = all done, 1 = more to process, 2 = error
    """
    try:
        # Force CPU mode if requested (before importing torch-dependent modules)
        if use_cpu:
            os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
            os.environ['CUDA_VISIBLE_DEVICES'] = ''

        from .embedding_service import EmbeddingService

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        batch_logger = logging.getLogger(__name__)

        # Patch EmbeddingService to use CPU and smaller batch size
        if use_cpu:
            original_init = EmbeddingService.__init__
            def patched_init(self, *args, **kwargs):
                kwargs['use_mps'] = False
                kwargs['max_batch_size'] = 8
                original_init(self, *args, **kwargs)
            EmbeddingService.__init__ = patched_init

        setup = InitialSetup(
            storage_dir=storage_dir,
            claude_dir=claude_dir,
            timeout_per_session=timeout_per_session,
            show_progress=False  # We'll handle progress ourselves
        )

        # Find all session files
        all_files = setup._find_session_files()
        state = setup._load_state()

        if state is None:
            processed = set()
        else:
            processed = set(state.processed_files)

        remaining = len(all_files) - len(processed)
        batch_logger.info(f"Total: {len(all_files)}, Processed: {len(processed)}, Remaining: {remaining}")

        if remaining == 0:
            batch_logger.info("All sessions processed!")
            return 0

        # Initialize services
        setup._initialize_services()

        count = 0
        start_time = time.time()

        for file_path in all_files:
            if str(file_path) in processed:
                continue

            if count >= batch_size:
                batch_logger.info(f"Batch limit reached ({batch_size} sessions)")
                break

            # Progress
            total_done = len(processed) + count
            pct = (total_done / len(all_files)) * 100
            print(f"Processing {total_done + 1} of {len(all_files)} ({pct:.1f}%) - {file_path.name}")

            # Process the file
            result = setup._process_session_file_with_timeout(file_path)

            # Update state
            if state is None:
                state = SetupState(
                    total_files=len(all_files),
                    processed_files=[],
                    timed_out_files=[],
                    started_at=time.time(),
                    last_updated=time.time()
                )

            state.processed_files.append(str(file_path))
            if result.get('timed_out'):
                state.timed_out_files.append(str(file_path))
            state.last_updated = time.time()
            setup._save_state(state)

            count += 1
            gc.collect()

        # Cleanup
        if setup.embedding_service:
            setup.embedding_service.flush_cache()
            setup.embedding_service.unload_model()

        gc.collect()

        elapsed = time.time() - start_time
        batch_logger.info(f"Batch processed {count} sessions in {elapsed:.1f}s")

        # Check if there are more
        remaining_after = len(all_files) - len(state.processed_files)
        if remaining_after == 0:
            batch_logger.info("All sessions processed!")
            return 0
        else:
            batch_logger.info(f"Sessions remaining: {remaining_after}")
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2


def run_batch_mode(
    batch_size: int = 5,
    storage_dir: str = "~/.smart-fork",
    claude_dir: str = "~/.claude",
    timeout_per_session: float = 30.0,
    use_cpu: bool = True
) -> Dict[str, Any]:
    """
    Run initial setup in batch mode, spawning fresh processes for each batch.

    This is the recommended approach for large session counts (>100 sessions)
    as it ensures memory is fully released between batches.

    Args:
        batch_size: Number of sessions to process per batch (default: 5)
        storage_dir: Directory for Smart Fork data (default: ~/.smart-fork)
        claude_dir: Directory containing Claude Code sessions
        timeout_per_session: Timeout in seconds for processing each session
        use_cpu: Force CPU mode to reduce memory usage (default: True)

    Returns:
        Dictionary with setup results
    """
    batch_logger = logging.getLogger(__name__)
    batch_logger.info(f"Starting batch mode setup (batch_size={batch_size}, use_cpu={use_cpu})")

    # Resolve paths
    storage_path = Path(storage_dir).expanduser()
    claude_path = Path(claude_dir).expanduser()

    # Build the subprocess command
    # Use the same Python interpreter and module
    python_exe = sys.executable

    batch_num = 0
    start_time = time.time()

    while True:
        batch_num += 1
        print(f"\n{'='*60}")
        print(f"Starting batch {batch_num}")
        print(f"{'='*60}\n")

        # Build command to run single batch
        cmd = [
            python_exe, '-m', 'smart_fork.initial_setup',
            '--single-batch',
            '--batch-size', str(batch_size),
            '--storage-dir', str(storage_path),
            '--claude-dir', str(claude_path),
            '--timeout', str(timeout_per_session)
        ]
        if use_cpu:
            cmd.append('--use-cpu')

        # Run subprocess
        try:
            result = subprocess.run(cmd, check=False)
            exit_code = result.returncode
        except Exception as e:
            batch_logger.error(f"Subprocess failed: {e}")
            return {
                'success': False,
                'batches_run': batch_num,
                'elapsed_time': time.time() - start_time,
                'error': str(e)
            }

        if exit_code == 0:
            # All done
            print(f"\n{'='*60}")
            print(f"All sessions processed! Done.")
            print(f"Total batches: {batch_num}")
            print(f"Total time: {_format_time(time.time() - start_time)}")
            print(f"{'='*60}")
            return {
                'success': True,
                'batches_run': batch_num,
                'elapsed_time': time.time() - start_time
            }
        elif exit_code == 1:
            # More to process, continue
            batch_logger.info(f"Batch {batch_num} complete, more sessions remaining...")
            time.sleep(1)  # Brief pause between batches
            continue
        else:
            # Error
            batch_logger.error(f"Batch {batch_num} failed with exit code {exit_code}")
            return {
                'success': False,
                'batches_run': batch_num,
                'elapsed_time': time.time() - start_time,
                'error': f'Batch failed with exit code {exit_code}'
            }


def main():
    """CLI entry point for initial setup."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Smart Fork initial setup - index Claude Code sessions into vector database"
    )

    # Mode selection
    parser.add_argument(
        "--batch-mode", action="store_true",
        help="Use subprocess-based batch processing (recommended for >100 sessions)"
    )
    parser.add_argument(
        "--single-batch", action="store_true",
        help="Process one batch and exit (internal use, returns exit code 0/1/2)"
    )

    # Common options
    parser.add_argument("--resume", action="store_true", help="Resume from previous state")
    parser.add_argument("--retry-timeouts", action="store_true", help="Retry timed-out sessions")
    parser.add_argument("--timeout", type=float, default=30.0, help="Timeout per session in seconds")
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel workers (standard mode only)")

    # Batch mode options
    parser.add_argument("--batch-size", type=int, default=5, help="Sessions per batch (batch mode)")
    parser.add_argument("--use-cpu", action="store_true", help="Force CPU mode (disable MPS/CUDA)")

    # Path options
    parser.add_argument(
        "--storage-dir", type=str, default="~/.smart-fork",
        help="Directory for Smart Fork data (default: ~/.smart-fork)"
    )
    parser.add_argument(
        "--claude-dir", type=str, default="~/.claude",
        help="Directory containing Claude Code sessions (default: ~/.claude)"
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    if args.single_batch:
        # Internal: process single batch and exit with code
        exit_code = run_single_batch(
            batch_size=args.batch_size,
            storage_dir=args.storage_dir,
            claude_dir=args.claude_dir,
            timeout_per_session=args.timeout,
            use_cpu=args.use_cpu
        )
        sys.exit(exit_code)

    elif args.batch_mode:
        # Batch mode: spawn subprocesses
        result = run_batch_mode(
            batch_size=args.batch_size,
            storage_dir=args.storage_dir,
            claude_dir=args.claude_dir,
            timeout_per_session=args.timeout,
            use_cpu=args.use_cpu
        )

        if not result.get('success'):
            print(f"\nSetup failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)

    else:
        # Standard mode: single process
        setup = InitialSetup(
            storage_dir=args.storage_dir,
            claude_dir=args.claude_dir,
            timeout_per_session=args.timeout,
            workers=args.workers
        )
        result = setup.run_setup(resume=args.resume, retry_timeouts=args.retry_timeouts)

        if result.get('interrupted'):
            print("\nSetup interrupted. Run with --resume to continue.")
        elif not result.get('success', True):
            print(f"\nSetup failed: {result.get('message', 'Unknown error')}")
        else:
            print(f"\nSetup complete!")


if __name__ == "__main__":
    main()
