"""
Session Diff Service for comparing two sessions.

This module provides functionality to compare two Claude Code sessions,
identifying common content, unique messages, and differences in topics/technologies.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from collections import Counter
import re

from .vector_db_service import VectorDBService
from .session_registry import SessionRegistry
from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class MessageMatch:
    """Represents a matching pair of messages between two sessions."""
    session_1_index: int
    session_2_index: int
    similarity: float
    content_1: str
    content_2: str


@dataclass
class SessionDiff:
    """
    Represents the difference between two sessions.

    Attributes:
        session_id_1: First session ID
        session_id_2: Second session ID
        similarity_score: Overall similarity score (0-1)
        common_messages: List of matching message pairs
        unique_to_1: Message indices unique to session 1
        unique_to_2: Message indices unique to session 2
        topics_1: Unique topics/technologies in session 1
        topics_2: Unique topics/technologies in session 2
        common_topics: Topics appearing in both sessions
    """
    session_id_1: str
    session_id_2: str
    similarity_score: float
    common_messages: List[MessageMatch]
    unique_to_1: List[int]
    unique_to_2: List[int]
    topics_1: List[str]
    topics_2: List[str]
    common_topics: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'session_id_1': self.session_id_1,
            'session_id_2': self.session_id_2,
            'similarity_score': self.similarity_score,
            'common_messages': [
                {
                    'session_1_index': m.session_1_index,
                    'session_2_index': m.session_2_index,
                    'similarity': m.similarity,
                    'content_1': m.content_1[:100] + '...' if len(m.content_1) > 100 else m.content_1,
                    'content_2': m.content_2[:100] + '...' if len(m.content_2) > 100 else m.content_2
                }
                for m in self.common_messages
            ],
            'unique_to_1': self.unique_to_1,
            'unique_to_2': self.unique_to_2,
            'topics_1': self.topics_1,
            'topics_2': self.topics_2,
            'common_topics': self.common_topics
        }


class SessionDiffService:
    """
    Service for comparing two sessions and identifying differences.

    Features:
    - Compare semantic similarity between messages using embeddings
    - Find matching and unique messages in each session
    - Extract unique topics/technologies from each session
    - Compute overall session similarity score
    """

    def __init__(
        self,
        vector_db_service: VectorDBService,
        session_registry: SessionRegistry,
        embedding_service: EmbeddingService,
        similarity_threshold: float = 0.75,
        min_message_length: int = 20
    ):
        """
        Initialize the SessionDiffService.

        Args:
            vector_db_service: VectorDBService for accessing chunk embeddings
            session_registry: SessionRegistry for accessing session metadata
            embedding_service: EmbeddingService for computing embeddings
            similarity_threshold: Minimum similarity (0-1) to consider messages matching (default: 0.75)
            min_message_length: Minimum message length to consider for comparison (default: 20)
        """
        self.vector_db_service = vector_db_service
        self.session_registry = session_registry
        self.embedding_service = embedding_service
        self.similarity_threshold = similarity_threshold
        self.min_message_length = min_message_length

        logger.info(
            f"Initialized SessionDiffService "
            f"(threshold={similarity_threshold}, min_length={min_message_length})"
        )

    def compare_sessions(
        self,
        session_id_1: str,
        session_id_2: str
    ) -> Optional[SessionDiff]:
        """
        Compare two sessions and return structured diff.

        Args:
            session_id_1: First session ID
            session_id_2: Second session ID

        Returns:
            SessionDiff object with comparison results, or None if sessions cannot be compared
        """
        # Validate sessions exist
        session_1 = self.session_registry.get_session(session_id_1)
        session_2 = self.session_registry.get_session(session_id_2)

        if session_1 is None:
            logger.error(f"Session {session_id_1} not found in registry")
            return None

        if session_2 is None:
            logger.error(f"Session {session_id_2} not found in registry")
            return None

        # Get chunks for both sessions
        chunks_1 = self.vector_db_service.get_session_chunks(session_id_1)
        chunks_2 = self.vector_db_service.get_session_chunks(session_id_2)

        if not chunks_1:
            logger.warning(f"Session {session_id_1} has no chunks")
            return None

        if not chunks_2:
            logger.warning(f"Session {session_id_2} has no chunks")
            return None

        # Get embeddings for chunks
        embeddings_1 = self._get_chunk_embeddings(chunks_1)
        embeddings_2 = self._get_chunk_embeddings(chunks_2)

        if not embeddings_1 or not embeddings_2:
            logger.warning("Failed to retrieve embeddings for one or both sessions")
            return None

        # Find matching messages using cosine similarity
        matches = self._find_matching_messages(
            chunks_1, embeddings_1, chunks_2, embeddings_2
        )

        # Identify unique messages
        matched_indices_1 = {m.session_1_index for m in matches}
        matched_indices_2 = {m.session_2_index for m in matches}

        unique_to_1 = [i for i in range(len(chunks_1)) if i not in matched_indices_1]
        unique_to_2 = [i for i in range(len(chunks_2)) if i not in matched_indices_2]

        # Extract topics from both sessions
        topics_1 = self._extract_topics([c.content for c in chunks_1])
        topics_2 = self._extract_topics([c.content for c in chunks_2])

        # Find common and unique topics
        topics_set_1 = set(topics_1)
        topics_set_2 = set(topics_2)

        common_topics = sorted(topics_set_1 & topics_set_2)
        unique_topics_1 = sorted(topics_set_1 - topics_set_2)
        unique_topics_2 = sorted(topics_set_2 - topics_set_1)

        # Calculate overall similarity score
        # Weighted average: 70% content similarity, 30% topic overlap
        content_similarity = len(matches) / max(len(chunks_1), len(chunks_2)) if chunks_1 or chunks_2 else 0

        all_topics = topics_set_1 | topics_set_2
        topic_similarity = len(common_topics) / len(all_topics) if all_topics else 0

        overall_similarity = 0.7 * content_similarity + 0.3 * topic_similarity

        logger.info(
            f"Compared {session_id_1} vs {session_id_2}: "
            f"similarity={overall_similarity:.3f}, "
            f"matches={len(matches)}, "
            f"unique_1={len(unique_to_1)}, "
            f"unique_2={len(unique_to_2)}"
        )

        return SessionDiff(
            session_id_1=session_id_1,
            session_id_2=session_id_2,
            similarity_score=overall_similarity,
            common_messages=matches,
            unique_to_1=unique_to_1,
            unique_to_2=unique_to_2,
            topics_1=unique_topics_1,
            topics_2=unique_topics_2,
            common_topics=common_topics
        )

    def _get_chunk_embeddings(self, chunks: List[Any]) -> List[np.ndarray]:
        """
        Get embeddings for a list of chunks.

        Args:
            chunks: List of chunk objects

        Returns:
            List of embedding vectors
        """
        chunk_ids = [chunk.chunk_id for chunk in chunks]

        try:
            results = self.vector_db_service.collection.get(
                ids=chunk_ids,
                include=["embeddings"]
            )

            if not results["embeddings"]:
                return []

            # Convert to numpy arrays
            embeddings = [np.array(emb) for emb in results["embeddings"]]
            return embeddings

        except Exception as e:
            logger.error(f"Error retrieving embeddings: {e}")
            return []

    def _find_matching_messages(
        self,
        chunks_1: List[Any],
        embeddings_1: List[np.ndarray],
        chunks_2: List[Any],
        embeddings_2: List[np.ndarray]
    ) -> List[MessageMatch]:
        """
        Find matching messages between two sessions using cosine similarity.

        Uses a greedy approach: for each chunk in session 1, find the best match
        in session 2 above the similarity threshold. Then remove duplicates.

        Args:
            chunks_1: Chunks from session 1
            embeddings_1: Embeddings from session 1
            chunks_2: Chunks from session 2
            embeddings_2: Embeddings from session 2

        Returns:
            List of MessageMatch objects
        """
        matches = []
        used_indices_2: Set[int] = set()

        # For each chunk in session 1, find best match in session 2
        for i, (chunk_1, emb_1) in enumerate(zip(chunks_1, embeddings_1)):
            # Filter by minimum length
            if len(chunk_1.content.strip()) < self.min_message_length:
                continue

            best_match_idx = None
            best_similarity = 0.0

            for j, (chunk_2, emb_2) in enumerate(zip(chunks_2, embeddings_2)):
                # Skip if already matched
                if j in used_indices_2:
                    continue

                # Filter by minimum length
                if len(chunk_2.content.strip()) < self.min_message_length:
                    continue

                # Compute cosine similarity
                # Normalize embeddings
                norm_1 = np.linalg.norm(emb_1)
                norm_2 = np.linalg.norm(emb_2)

                if norm_1 > 0 and norm_2 > 0:
                    similarity = np.dot(emb_1 / norm_1, emb_2 / norm_2)
                    similarity = max(0.0, min(1.0, float(similarity)))

                    if similarity > best_similarity and similarity >= self.similarity_threshold:
                        best_similarity = similarity
                        best_match_idx = j

            # If found a match, record it
            if best_match_idx is not None:
                matches.append(MessageMatch(
                    session_1_index=i,
                    session_2_index=best_match_idx,
                    similarity=best_similarity,
                    content_1=chunk_1.content,
                    content_2=chunks_2[best_match_idx].content
                ))
                used_indices_2.add(best_match_idx)

        # Sort by similarity (highest first)
        matches.sort(key=lambda m: m.similarity, reverse=True)

        return matches

    def _extract_topics(self, texts: List[str], top_k: int = 10) -> List[str]:
        """
        Extract key topics/technologies from text content.

        Uses term frequency to identify important technical terms.

        Args:
            texts: List of text strings
            top_k: Number of top topics to extract (default: 10)

        Returns:
            List of topic terms
        """
        # Common stop words to filter out
        stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'this', 'can', 'could', 'would',
            'should', 'i', 'you', 'we', 'they', 'my', 'your', 'their', 'our',
            'me', 'him', 'her', 'them', 'us', 'am', 'do', 'does', 'did',
            'been', 'being', 'have', 'had', 'having', 'or', 'but', 'if',
            'because', 'when', 'where', 'why', 'how', 'which', 'who', 'whom',
            'code', 'file', 'function', 'method', 'class', 'need', 'want',
            'use', 'using', 'get', 'set', 'make', 'create', 'add', 'update'
        }

        # Combine all text
        combined_text = ' '.join(texts).lower()

        # Extract words (alphanumeric, including hyphenated tech terms)
        # Match common technology patterns: React, TypeScript, kebab-case, snake_case, etc.
        words = re.findall(r'\b[a-z][a-z0-9_-]*[a-z0-9]\b|\b[a-z]\b', combined_text)

        # Filter stop words and short words
        filtered_words = [
            w for w in words
            if w not in stop_words and len(w) >= 3
        ]

        # Count frequency
        word_freq = Counter(filtered_words)

        # Get top K most common
        top_terms = [word for word, count in word_freq.most_common(top_k)]

        return top_terms

    def get_message_content(
        self,
        session_id: str,
        message_indices: List[int],
        max_length: int = 200
    ) -> List[str]:
        """
        Get content for specific message indices from a session.

        Args:
            session_id: Session ID
            message_indices: List of chunk indices
            max_length: Maximum length per message (default: 200)

        Returns:
            List of message content strings (truncated if needed)
        """
        chunks = self.vector_db_service.get_session_chunks(session_id)

        if not chunks:
            return []

        messages = []
        for idx in message_indices:
            if 0 <= idx < len(chunks):
                content = chunks[idx].content
                if len(content) > max_length:
                    content = content[:max_length] + '...'
                messages.append(content)

        return messages
