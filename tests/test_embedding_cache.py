"""
Tests for the embedding cache module.
"""

import json
import tempfile
from pathlib import Path

import pytest

from smart_fork.embedding_cache import EmbeddingCache, EmbeddingCacheStats


class TestEmbeddingCache:
    """Tests for the EmbeddingCache class."""

    def test_initialization(self):
        """Test cache initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(cache_dir=tmpdir)

            assert cache.cache_dir == Path(tmpdir)
            assert cache.cache_file == Path(tmpdir) / "cache.json"
            assert cache.size() == 0
            assert cache.stats.hits == 0
            assert cache.stats.misses == 0

    def test_put_and_get(self):
        """Test storing and retrieving embeddings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(cache_dir=tmpdir)

            text = "Hello, world!"
            embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

            # Put embedding
            cache.put(text, embedding)
            assert cache.size() == 1

            # Get embedding
            retrieved = cache.get(text)
            assert retrieved == embedding
            assert cache.stats.hits == 1
            assert cache.stats.misses == 0

    def test_cache_miss(self):
        """Test cache miss behavior."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(cache_dir=tmpdir)

            # Try to get non-existent embedding
            result = cache.get("non-existent text")
            assert result is None
            assert cache.stats.hits == 0
            assert cache.stats.misses == 1

    def test_content_addressable(self):
        """Test that same content produces same cache key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(cache_dir=tmpdir)

            text = "Test content"
            embedding1 = [0.1, 0.2, 0.3]
            embedding2 = [0.4, 0.5, 0.6]

            # Put first embedding
            cache.put(text, embedding1)

            # Put second embedding for same text (should not overwrite since hash is same)
            cache.put(text, embedding2)

            # Should only have one entry
            assert cache.size() == 1

            # First embedding should be preserved (not overwritten)
            retrieved = cache.get(text)
            assert retrieved == embedding1

    def test_different_content(self):
        """Test that different content produces different cache keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(cache_dir=tmpdir)

            text1 = "First text"
            text2 = "Second text"
            embedding1 = [0.1, 0.2, 0.3]
            embedding2 = [0.4, 0.5, 0.6]

            cache.put(text1, embedding1)
            cache.put(text2, embedding2)

            assert cache.size() == 2
            assert cache.get(text1) == embedding1
            assert cache.get(text2) == embedding2

    def test_batch_get(self):
        """Test batch retrieval of embeddings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(cache_dir=tmpdir)

            texts = ["text1", "text2", "text3", "text4"]
            embeddings = [
                [0.1, 0.2],
                [0.3, 0.4],
                [0.5, 0.6],
                [0.7, 0.8]
            ]

            # Cache first two embeddings
            cache.put(texts[0], embeddings[0])
            cache.put(texts[1], embeddings[1])

            # Get batch (2 hits, 2 misses)
            results, miss_indices = cache.get_batch(texts)

            assert len(results) == 4
            assert results[0] == embeddings[0]  # Hit
            assert results[1] == embeddings[1]  # Hit
            assert results[2] is None  # Miss
            assert results[3] is None  # Miss
            assert miss_indices == [2, 3]
            assert cache.stats.hits == 2
            assert cache.stats.misses == 2

    def test_batch_put(self):
        """Test batch storage of embeddings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(cache_dir=tmpdir)

            texts = ["text1", "text2", "text3"]
            embeddings = [
                [0.1, 0.2],
                [0.3, 0.4],
                [0.5, 0.6]
            ]

            cache.put_batch(texts, embeddings)

            assert cache.size() == 3
            assert cache.get(texts[0]) == embeddings[0]
            assert cache.get(texts[1]) == embeddings[1]
            assert cache.get(texts[2]) == embeddings[2]

    def test_batch_put_length_mismatch(self):
        """Test that batch put raises error on length mismatch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(cache_dir=tmpdir)

            texts = ["text1", "text2"]
            embeddings = [[0.1, 0.2]]  # Only one embedding

            with pytest.raises(ValueError, match="must match"):
                cache.put_batch(texts, embeddings)

    def test_persistence(self):
        """Test that cache persists to disk and loads correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create cache and add data
            cache1 = EmbeddingCache(cache_dir=tmpdir)
            text = "Persistent text"
            embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
            cache1.put(text, embedding)
            cache1.flush()

            # Create new cache instance (should load from disk)
            cache2 = EmbeddingCache(cache_dir=tmpdir)
            assert cache2.size() == 1
            assert cache2.get(text) == embedding

    def test_flush(self):
        """Test manual flushing to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(cache_dir=tmpdir)

            text = "Test text"
            embedding = [0.1, 0.2, 0.3]
            cache.put(text, embedding)

            # Flush to disk
            cache.flush()

            # Verify file exists and contains data
            assert cache.cache_file.exists()
            with open(cache.cache_file, 'r') as f:
                data = json.load(f)
            assert len(data) == 1

    def test_clear(self):
        """Test clearing the cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(cache_dir=tmpdir)

            # Add some data
            cache.put("text1", [0.1, 0.2])
            cache.put("text2", [0.3, 0.4])
            assert cache.size() == 2

            # Clear cache
            cache.clear()
            assert cache.size() == 0
            assert cache.stats.total_entries == 0

            # Verify cache file is empty
            with open(cache.cache_file, 'r') as f:
                data = json.load(f)
            assert len(data) == 0

    def test_stats(self):
        """Test cache statistics tracking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(cache_dir=tmpdir)

            # Add data
            cache.put("text1", [0.1, 0.2])
            cache.put("text2", [0.3, 0.4])

            # Generate hits and misses
            cache.get("text1")  # Hit
            cache.get("text2")  # Hit
            cache.get("text3")  # Miss
            cache.get("text4")  # Miss
            cache.get("text1")  # Hit

            stats = cache.get_stats()
            assert stats.hits == 3
            assert stats.misses == 2
            assert stats.total_requests == 5
            assert stats.hit_rate == 60.0
            assert stats.total_entries == 2

    def test_stats_to_dict(self):
        """Test conversion of stats to dictionary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(cache_dir=tmpdir)

            cache.put("text1", [0.1, 0.2])
            cache.get("text1")  # Hit
            cache.get("text2")  # Miss

            stats_dict = cache.get_stats().to_dict()
            assert stats_dict['hits'] == 1
            assert stats_dict['misses'] == 1
            assert stats_dict['total_entries'] == 1
            assert stats_dict['total_requests'] == 2
            assert stats_dict['hit_rate'] == "50.00%"

    def test_empty_cache_stats(self):
        """Test stats for empty cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(cache_dir=tmpdir)

            stats = cache.get_stats()
            assert stats.hits == 0
            assert stats.misses == 0
            assert stats.total_requests == 0
            assert stats.hit_rate == 0.0
            assert stats.total_entries == 0

    def test_large_batch(self):
        """Test cache with large batch of embeddings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(cache_dir=tmpdir)

            # Create 1000 embeddings
            texts = [f"text_{i}" for i in range(1000)]
            embeddings = [[float(i) * 0.1] * 384 for i in range(1000)]

            # Store all
            cache.put_batch(texts, embeddings)
            assert cache.size() == 1000

            # Retrieve all
            results, miss_indices = cache.get_batch(texts)
            assert len(miss_indices) == 0
            assert all(r is not None for r in results)
            assert cache.stats.hits == 1000

    def test_hash_collision_resistance(self):
        """Test that similar but different content produces different hashes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = EmbeddingCache(cache_dir=tmpdir)

            text1 = "The quick brown fox"
            text2 = "The quick brown fox "  # Extra space
            text3 = "the quick brown fox"  # Different case

            embedding1 = [0.1, 0.2]
            embedding2 = [0.3, 0.4]
            embedding3 = [0.5, 0.6]

            cache.put(text1, embedding1)
            cache.put(text2, embedding2)
            cache.put(text3, embedding3)

            # All should be stored separately
            assert cache.size() == 3
            assert cache.get(text1) == embedding1
            assert cache.get(text2) == embedding2
            assert cache.get(text3) == embedding3


class TestEmbeddingCacheStats:
    """Tests for the EmbeddingCacheStats dataclass."""

    def test_total_requests(self):
        """Test total_requests property."""
        stats = EmbeddingCacheStats(hits=10, misses=5)
        assert stats.total_requests == 15

    def test_hit_rate(self):
        """Test hit_rate property."""
        stats = EmbeddingCacheStats(hits=75, misses=25)
        assert stats.hit_rate == 75.0

    def test_hit_rate_zero_requests(self):
        """Test hit_rate with zero requests."""
        stats = EmbeddingCacheStats()
        assert stats.hit_rate == 0.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        stats = EmbeddingCacheStats(hits=8, misses=2, total_entries=100)
        d = stats.to_dict()
        assert d['hits'] == 8
        assert d['misses'] == 2
        assert d['total_entries'] == 100
        assert d['total_requests'] == 10
        assert d['hit_rate'] == "80.00%"
