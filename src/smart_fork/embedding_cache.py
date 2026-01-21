"""
Embedding cache for storing and retrieving pre-computed embeddings.

This module provides content-addressable storage for embeddings, allowing
reuse of embeddings when chunk content hasn't changed during re-indexing.
"""

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingCacheStats:
    """Statistics for embedding cache performance."""
    hits: int = 0
    misses: int = 0
    total_entries: int = 0

    @property
    def total_requests(self) -> int:
        """Total number of cache requests."""
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        """Cache hit rate as a percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100

    def to_dict(self) -> Dict[str, any]:
        """Convert stats to dictionary."""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'total_entries': self.total_entries,
            'total_requests': self.total_requests,
            'hit_rate': f"{self.hit_rate:.2f}%"
        }


class EmbeddingCache:
    """
    Content-addressable storage for embeddings.

    Uses SHA256 hash of chunk text as key to store and retrieve embeddings.
    This allows skipping expensive embedding computation when content hasn't changed.

    Storage format:
    - cache.json: Maps content hashes to embeddings
    - Each entry: {"hash": [embedding_vector]}
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the embedding cache.

        Args:
            cache_dir: Directory for cache storage.
                      Defaults to ~/.smart-fork/embedding_cache/
        """
        if cache_dir is None:
            home = os.path.expanduser("~")
            cache_dir = os.path.join(home, ".smart-fork", "embedding_cache")

        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / "cache.json"

        # Create directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache: hash -> embedding
        self._cache: Dict[str, List[float]] = {}

        # Statistics
        self.stats = EmbeddingCacheStats()

        # Load existing cache
        self._load_cache()

        logger.info(
            f"Initialized EmbeddingCache at {cache_dir} "
            f"({self.stats.total_entries} entries)"
        )

    def _compute_hash(self, text: str) -> str:
        """
        Compute SHA256 hash of text content.

        Args:
            text: Text to hash

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def _load_cache(self) -> None:
        """Load cache from disk into memory."""
        if not self.cache_file.exists():
            logger.info("No existing cache file found, starting fresh")
            return

        try:
            with open(self.cache_file, 'r') as f:
                self._cache = json.load(f)

            self.stats.total_entries = len(self._cache)
            logger.info(f"Loaded {len(self._cache)} cached embeddings")
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            self._cache = {}

    def _save_cache(self) -> None:
        """Save cache from memory to disk."""
        try:
            # Write to temporary file first
            temp_file = self.cache_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(self._cache, f)

            # Atomic rename
            temp_file.rename(self.cache_file)
            logger.debug(f"Saved {len(self._cache)} cached embeddings")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def get(self, text: str) -> Optional[List[float]]:
        """
        Get cached embedding for text.

        Args:
            text: Text to look up

        Returns:
            Cached embedding if found, None otherwise
        """
        content_hash = self._compute_hash(text)

        if content_hash in self._cache:
            self.stats.hits += 1
            logger.debug(f"Cache hit for hash {content_hash[:16]}...")
            return self._cache[content_hash]

        self.stats.misses += 1
        logger.debug(f"Cache miss for hash {content_hash[:16]}...")
        return None

    def get_batch(self, texts: List[str]) -> Tuple[List[Optional[List[float]]], List[int]]:
        """
        Get cached embeddings for a batch of texts.

        Args:
            texts: List of texts to look up

        Returns:
            Tuple of:
            - List of embeddings (None for cache misses)
            - List of indices where cache missed (need computation)
        """
        embeddings = []
        miss_indices = []

        for i, text in enumerate(texts):
            embedding = self.get(text)
            embeddings.append(embedding)
            if embedding is None:
                miss_indices.append(i)

        return embeddings, miss_indices

    def put(self, text: str, embedding: List[float]) -> None:
        """
        Store embedding in cache.

        Args:
            text: Text content
            embedding: Embedding vector to cache
        """
        content_hash = self._compute_hash(text)

        # Only update if not already in cache (avoid unnecessary writes)
        if content_hash not in self._cache:
            self._cache[content_hash] = embedding
            self.stats.total_entries = len(self._cache)
            logger.debug(f"Cached embedding for hash {content_hash[:16]}...")

    def put_batch(self, texts: List[str], embeddings: List[List[float]]) -> None:
        """
        Store multiple embeddings in cache.

        Args:
            texts: List of text contents
            embeddings: List of embedding vectors (must match texts length)
        """
        if len(texts) != len(embeddings):
            raise ValueError(
                f"Texts count ({len(texts)}) must match embeddings count ({len(embeddings)})"
            )

        for text, embedding in zip(texts, embeddings):
            self.put(text, embedding)

    def flush(self) -> None:
        """Flush in-memory cache to disk."""
        self._save_cache()
        logger.info(f"Flushed {len(self._cache)} cached embeddings to disk")

    def clear(self) -> None:
        """Clear all cached embeddings."""
        count = len(self._cache)
        self._cache.clear()
        self.stats.total_entries = 0
        self._save_cache()
        logger.info(f"Cleared {count} cached embeddings")

    def size(self) -> int:
        """Get current number of cached embeddings."""
        return len(self._cache)

    def get_stats(self) -> EmbeddingCacheStats:
        """Get cache statistics."""
        self.stats.total_entries = len(self._cache)
        return self.stats
