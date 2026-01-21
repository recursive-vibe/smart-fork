"""
Session archiving service for managing old sessions.

This module provides functionality to archive old sessions to a separate
ChromaDB collection to keep the active database performant, with the ability
to restore archived sessions when needed.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import chromadb
from chromadb.config import Settings

from .session_registry import SessionRegistry, SessionMetadata
from .vector_db_service import VectorDBService, ChunkSearchResult

logger = logging.getLogger(__name__)


@dataclass
class ArchiveStats:
    """Statistics about archived sessions."""
    total_archived_sessions: int
    total_archived_chunks: int
    oldest_session_date: Optional[str]
    newest_session_date: Optional[str]


class SessionArchiveService:
    """
    Service for archiving old sessions to a separate collection.

    Provides methods to:
    - Archive sessions older than a threshold
    - Search archived sessions
    - Restore archived sessions to active collection
    - Get archive statistics
    """

    def __init__(
        self,
        vector_db_service: VectorDBService,
        session_registry: SessionRegistry,
        archive_threshold_days: int = 365
    ):
        """
        Initialize the SessionArchiveService.

        Args:
            vector_db_service: VectorDBService for active collection
            session_registry: SessionRegistry for tracking session metadata
            archive_threshold_days: Number of days after which sessions are archived (default 365)
        """
        self.vector_db_service = vector_db_service
        self.session_registry = session_registry
        self.archive_threshold_days = archive_threshold_days

        # Get ChromaDB client from vector_db_service
        self.client = vector_db_service.client

        # Get or create archive collection
        self.archive_collection = self.client.get_or_create_collection(
            name="session_chunks_archive",
            metadata={"description": "Archived Claude Code session chunks"}
        )

        logger.info(f"Initialized SessionArchiveService (threshold: {archive_threshold_days} days)")

    def _is_session_old(self, metadata: SessionMetadata) -> bool:
        """
        Check if a session is old enough to be archived.

        Args:
            metadata: SessionMetadata to check

        Returns:
            True if session should be archived, False otherwise
        """
        if not metadata.last_modified:
            # If no last_modified, check created_at
            if not metadata.created_at:
                return False
            date_str = metadata.created_at
        else:
            date_str = metadata.last_modified

        try:
            session_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            threshold_date = datetime.utcnow() - timedelta(days=self.archive_threshold_days)
            return session_date < threshold_date
        except (ValueError, AttributeError):
            logger.warning(f"Invalid date format for session {metadata.session_id}: {date_str}")
            return False

    def archive_old_sessions(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Archive sessions older than the threshold.

        Args:
            dry_run: If True, only report what would be archived without actually archiving

        Returns:
            Dictionary with archive results:
            - sessions_archived: List of session IDs that were archived
            - chunks_moved: Total number of chunks moved
            - dry_run: Whether this was a dry run
        """
        all_sessions = self.session_registry.get_all_sessions()
        sessions_to_archive = []

        # Find sessions that should be archived
        for session_id, metadata in all_sessions.items():
            if self._is_session_old(metadata):
                sessions_to_archive.append(session_id)

        if dry_run:
            logger.info(f"Dry run: Would archive {len(sessions_to_archive)} sessions")
            return {
                "sessions_archived": sessions_to_archive,
                "chunks_moved": 0,
                "dry_run": True
            }

        # Archive each session
        total_chunks = 0
        archived_sessions = []

        for session_id in sessions_to_archive:
            try:
                chunks_moved = self._archive_session(session_id)
                total_chunks += chunks_moved
                archived_sessions.append(session_id)
                logger.info(f"Archived session {session_id} ({chunks_moved} chunks)")
            except Exception as e:
                logger.error(f"Failed to archive session {session_id}: {e}")

        logger.info(f"Archived {len(archived_sessions)} sessions ({total_chunks} chunks)")

        return {
            "sessions_archived": archived_sessions,
            "chunks_moved": total_chunks,
            "dry_run": False
        }

    def _archive_session(self, session_id: str) -> int:
        """
        Archive a single session by moving its chunks to the archive collection.

        Args:
            session_id: Session ID to archive

        Returns:
            Number of chunks archived
        """
        # Get all chunks for this session from active collection
        chunks = self.vector_db_service.get_session_chunks(session_id)

        if not chunks:
            return 0

        # Extract data from chunks
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]

        # Get embeddings from the active collection
        active_results = self.vector_db_service.collection.get(
            ids=chunk_ids,
            include=["embeddings"]
        )

        embeddings = active_results.get("embeddings")
        if embeddings is None or len(embeddings) == 0:
            logger.warning(f"No embeddings found for session {session_id}")
            return 0

        # Add to archive collection
        self.archive_collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

        # Delete from active collection
        self.vector_db_service.delete_session_chunks(session_id)

        # Update session metadata to mark as archived
        self.session_registry.update_session(session_id, archived=True)

        return len(chunks)

    def restore_session(self, session_id: str) -> Dict[str, Any]:
        """
        Restore an archived session back to the active collection.

        Args:
            session_id: Session ID to restore

        Returns:
            Dictionary with restore results:
            - session_id: The session ID
            - chunks_restored: Number of chunks restored
            - success: Whether the restore was successful
        """
        try:
            # Get all chunks for this session from archive collection
            archive_results = self.archive_collection.get(
                where={"session_id": session_id},
                include=["documents", "metadatas", "embeddings"]
            )

            if not archive_results["ids"]:
                logger.warning(f"Session {session_id} not found in archive")
                return {
                    "session_id": session_id,
                    "chunks_restored": 0,
                    "success": False,
                    "error": "Session not found in archive"
                }

            # Extract data
            chunk_ids = archive_results["ids"]
            documents = archive_results["documents"]
            metadatas = archive_results["metadatas"]
            embeddings = archive_results["embeddings"]

            # Add to active collection
            self.vector_db_service.add_chunks(
                chunks=documents,
                embeddings=embeddings,
                metadata=metadatas,
                chunk_ids=chunk_ids
            )

            # Delete from archive collection
            self.archive_collection.delete(ids=chunk_ids)

            # Update session metadata to mark as not archived
            self.session_registry.update_session(session_id, archived=False)

            logger.info(f"Restored session {session_id} ({len(chunk_ids)} chunks)")

            return {
                "session_id": session_id,
                "chunks_restored": len(chunk_ids),
                "success": True
            }

        except Exception as e:
            logger.error(f"Failed to restore session {session_id}: {e}")
            return {
                "session_id": session_id,
                "chunks_restored": 0,
                "success": False,
                "error": str(e)
            }

    def search_archive(
        self,
        query_embedding: List[float],
        k: int = 200
    ) -> List[ChunkSearchResult]:
        """
        Search archived sessions using vector similarity.

        Args:
            query_embedding: Query embedding vector
            k: Number of results to return (default 200)

        Returns:
            List of ChunkSearchResult objects from archived sessions
        """
        if k <= 0:
            return []

        # Query the archive collection
        results = self.archive_collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"]
        )

        # Convert to ChunkSearchResult objects
        search_results = []

        if results["ids"] and len(results["ids"]) > 0:
            chunk_ids = results["ids"][0]
            documents = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]

            for i in range(len(chunk_ids)):
                # Convert distance to similarity
                similarity = 1.0 / (1.0 + distances[i])

                metadata = metadatas[i] if metadatas else {}

                search_results.append(ChunkSearchResult(
                    chunk_id=chunk_ids[i],
                    session_id=metadata.get("session_id", "unknown"),
                    content=documents[i],
                    metadata=metadata,
                    similarity=similarity,
                    chunk_index=int(metadata.get("chunk_index", 0))
                ))

        return search_results

    def get_archive_stats(self) -> ArchiveStats:
        """
        Get statistics about archived sessions.

        Returns:
            ArchiveStats object with archive statistics
        """
        # Count total chunks in archive
        total_chunks = self.archive_collection.count()

        # Get all archived sessions
        all_sessions = self.session_registry.get_all_sessions()
        archived_sessions = [
            metadata for metadata in all_sessions.values()
            if metadata.__dict__.get('archived', False)
        ]

        # Find oldest and newest dates
        oldest_date = None
        newest_date = None

        for metadata in archived_sessions:
            date_str = metadata.last_modified or metadata.created_at
            if not date_str:
                continue

            try:
                session_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))

                if oldest_date is None or session_date < oldest_date:
                    oldest_date = session_date

                if newest_date is None or session_date > newest_date:
                    newest_date = session_date
            except (ValueError, AttributeError):
                pass

        return ArchiveStats(
            total_archived_sessions=len(archived_sessions),
            total_archived_chunks=total_chunks,
            oldest_session_date=oldest_date.isoformat() if oldest_date else None,
            newest_session_date=newest_date.isoformat() if newest_date else None
        )

    def list_archived_sessions(self) -> List[SessionMetadata]:
        """
        List all archived sessions.

        Returns:
            List of SessionMetadata for archived sessions
        """
        all_sessions = self.session_registry.get_all_sessions()
        archived = [
            metadata for metadata in all_sessions.values()
            if metadata.__dict__.get('archived', False)
        ]
        return archived

    def is_session_archived(self, session_id: str) -> bool:
        """
        Check if a session is archived.

        Args:
            session_id: Session ID to check

        Returns:
            True if session is archived, False otherwise
        """
        metadata = self.session_registry.get_session(session_id)
        if not metadata:
            return False
        return metadata.__dict__.get('archived', False)
