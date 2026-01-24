"""
Tests for embedding service cache integration.
"""

import tempfile
from unittest.mock import Mock, patch

import pytest

from smart_fork.embedding_service import EmbeddingService


class TestEmbeddingServiceCache:
    """Tests for embedding cache integration in EmbeddingService."""

    @pytest.fixture
    def mock_model(self):
        """Mock SentenceTransformer model."""
        model = Mock()
        # Mock encode to return deterministic embeddings
        def mock_encode(texts, **kwargs):
            import numpy as np
            # Return unique embeddings for each text
            return np.array([[float(hash(t) % 100) / 100] * 384 for t in texts])
        model.encode = mock_encode
        return model

    def test_cache_disabled(self, mock_model):
        """Test that cache can be disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = EmbeddingService(use_cache=False, cache_dir=tmpdir)
            assert service.use_cache is False
            assert service.cache is None

    def test_cache_enabled_by_default(self, mock_model):
        """Test that cache is enabled by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = EmbeddingService(use_cache=True, cache_dir=tmpdir)
            assert service.use_cache is True
            assert service.cache is not None

    @patch('smart_fork.embedding_service.SentenceTransformer')
    def test_cache_hit_on_repeated_text(self, mock_transformer, mock_model):
        """Test that repeated text hits the cache."""
        mock_transformer.return_value = mock_model

        with tempfile.TemporaryDirectory() as tmpdir:
            service = EmbeddingService(use_cache=True, cache_dir=tmpdir)
            service.load_model()

            text = "Hello, world!"

            # First call - should miss cache and compute
            embeddings1 = service.embed_texts([text])
            assert len(embeddings1) == 1
            assert service.cache.stats.misses == 1
            assert service.cache.stats.hits == 0

            # Second call - should hit cache
            embeddings2 = service.embed_texts([text])
            assert len(embeddings2) == 1
            assert embeddings1 == embeddings2
            assert service.cache.stats.misses == 1
            assert service.cache.stats.hits == 1

    @patch('smart_fork.embedding_service.SentenceTransformer')
    def test_cache_partial_hits(self, mock_transformer, mock_model):
        """Test cache with partial hits in a batch."""
        mock_transformer.return_value = mock_model

        with tempfile.TemporaryDirectory() as tmpdir:
            service = EmbeddingService(use_cache=True, cache_dir=tmpdir)
            service.load_model()

            texts1 = ["text1", "text2", "text3"]
            texts2 = ["text2", "text3", "text4"]  # 2 cached, 1 new

            # First batch - all cache misses
            embeddings1 = service.embed_texts(texts1)
            assert len(embeddings1) == 3
            assert service.cache.stats.misses == 3
            assert service.cache.stats.hits == 0

            # Second batch - 2 hits, 1 miss
            embeddings2 = service.embed_texts(texts2)
            assert len(embeddings2) == 3
            assert service.cache.stats.misses == 4  # 3 + 1
            assert service.cache.stats.hits == 2

    @patch('smart_fork.embedding_service.SentenceTransformer')
    def test_cache_flush(self, mock_transformer, mock_model):
        """Test that cache can be flushed to disk."""
        mock_transformer.return_value = mock_model

        with tempfile.TemporaryDirectory() as tmpdir:
            service = EmbeddingService(use_cache=True, cache_dir=tmpdir)
            service.load_model()

            text = "Test text"
            service.embed_texts([text])

            # Flush cache
            service.flush_cache()

            # Create new service instance (should load from disk)
            service2 = EmbeddingService(use_cache=True, cache_dir=tmpdir)
            assert service2.cache.size() == 1

    @patch('smart_fork.embedding_service.SentenceTransformer')
    def test_get_cache_stats(self, mock_transformer, mock_model):
        """Test retrieving cache statistics."""
        mock_transformer.return_value = mock_model

        with tempfile.TemporaryDirectory() as tmpdir:
            service = EmbeddingService(use_cache=True, cache_dir=tmpdir)
            service.load_model()

            # Generate some activity
            service.embed_texts(["text1", "text2"])
            service.embed_texts(["text1"])  # Hit

            stats = service.get_cache_stats()
            assert stats['misses'] == 2
            assert stats['hits'] == 1
            assert stats['total_entries'] == 2
            assert stats['total_requests'] == 3

    def test_get_cache_stats_disabled(self):
        """Test that get_cache_stats returns empty dict when cache disabled."""
        service = EmbeddingService(use_cache=False)
        stats = service.get_cache_stats()
        assert stats == {}

    @patch('smart_fork.embedding_service.SentenceTransformer')
    def test_cache_with_single_text(self, mock_transformer, mock_model):
        """Test cache with single text (not a list)."""
        mock_transformer.return_value = mock_model

        with tempfile.TemporaryDirectory() as tmpdir:
            service = EmbeddingService(use_cache=True, cache_dir=tmpdir)
            service.load_model()

            text = "Single text"

            # First call
            embedding1 = service.embed_single(text)
            assert len(embedding1) == 384

            # Second call - should hit cache
            embedding2 = service.embed_single(text)
            assert embedding1 == embedding2
            assert service.cache.stats.hits == 1

    @patch('smart_fork.embedding_service.SentenceTransformer')
    def test_cache_preserves_order(self, mock_transformer, mock_model):
        """Test that cache preserves embedding order in batch."""
        mock_transformer.return_value = mock_model

        with tempfile.TemporaryDirectory() as tmpdir:
            service = EmbeddingService(use_cache=True, cache_dir=tmpdir)
            service.load_model()

            texts = ["text1", "text2", "text3"]

            # First call - compute all
            embeddings1 = service.embed_texts(texts)

            # Second call with different order - should return in requested order
            shuffled_texts = ["text3", "text1", "text2"]
            embeddings2 = service.embed_texts(shuffled_texts)

            assert embeddings2[0] == embeddings1[2]  # text3
            assert embeddings2[1] == embeddings1[0]  # text1
            assert embeddings2[2] == embeddings1[1]  # text2

    @patch('smart_fork.embedding_service.SentenceTransformer')
    def test_cache_with_empty_list(self, mock_transformer, mock_model):
        """Test cache behavior with empty input."""
        mock_transformer.return_value = mock_model

        with tempfile.TemporaryDirectory() as tmpdir:
            service = EmbeddingService(use_cache=True, cache_dir=tmpdir)
            service.load_model()

            embeddings = service.embed_texts([])
            assert embeddings == []
            assert service.cache.stats.total_requests == 0

    @patch('smart_fork.embedding_service.SentenceTransformer')
    def test_cache_100_percent_hit_rate(self, mock_transformer, mock_model):
        """Test 100% cache hit rate scenario."""
        # Create a proper Mock for encode
        encode_mock = Mock()
        import numpy as np
        encode_mock.side_effect = lambda texts, **kwargs: np.array([[float(hash(t) % 100) / 100] * 384 for t in texts])
        mock_model.encode = encode_mock
        mock_transformer.return_value = mock_model

        with tempfile.TemporaryDirectory() as tmpdir:
            service = EmbeddingService(use_cache=True, cache_dir=tmpdir)
            service.load_model()

            texts = ["text1", "text2", "text3"]

            # First call - populate cache
            service.embed_texts(texts)
            assert encode_mock.call_count == 1

            # Reset call count
            encode_mock.reset_mock()

            # Second call - should not call model at all
            service.embed_texts(texts)

            # Model should not have been called (100% cache hit)
            encode_mock.assert_not_called()

    @patch('smart_fork.embedding_service.SentenceTransformer')
    def test_cache_stats_after_multiple_batches(self, mock_transformer, mock_model):
        """Test cache statistics accumulate correctly across batches."""
        mock_transformer.return_value = mock_model

        with tempfile.TemporaryDirectory() as tmpdir:
            service = EmbeddingService(use_cache=True, cache_dir=tmpdir)
            service.load_model()

            # Batch 1
            service.embed_texts(["a", "b", "c"])
            assert service.cache.stats.misses == 3
            assert service.cache.stats.hits == 0

            # Batch 2 - partial overlap
            service.embed_texts(["b", "c", "d"])
            assert service.cache.stats.misses == 4  # +1 for "d"
            assert service.cache.stats.hits == 2  # b, c

            # Batch 3 - all hits
            service.embed_texts(["a", "b"])
            assert service.cache.stats.misses == 4
            assert service.cache.stats.hits == 4  # +2

            stats = service.get_cache_stats()
            assert stats['hit_rate'] == "50.00%"
