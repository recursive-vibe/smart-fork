"""Tests for ConfigManager."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from smart_fork.config_manager import (
    Config,
    ConfigManager,
    EmbeddingConfig,
    SearchConfig,
    ChunkingConfig,
    IndexingConfig,
    ServerConfig,
    MemoryConfig,
    load_config,
    save_config
)


class TestEmbeddingConfig(unittest.TestCase):
    """Test EmbeddingConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = EmbeddingConfig()
        self.assertEqual(config.model_name, "nomic-ai/nomic-embed-text-v1.5")
        self.assertEqual(config.dimension, 768)
        self.assertEqual(config.batch_size, 32)
        self.assertEqual(config.max_batch_size, 128)
        self.assertEqual(config.min_batch_size, 8)

    def test_custom_values(self):
        """Test custom configuration values."""
        config = EmbeddingConfig(
            model_name="custom-model",
            dimension=512,
            batch_size=16
        )
        self.assertEqual(config.model_name, "custom-model")
        self.assertEqual(config.dimension, 512)
        self.assertEqual(config.batch_size, 16)


class TestSearchConfig(unittest.TestCase):
    """Test SearchConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SearchConfig()
        self.assertEqual(config.k_chunks, 200)
        self.assertEqual(config.top_n_sessions, 5)
        self.assertEqual(config.preview_length, 200)
        self.assertEqual(config.similarity_threshold, 0.3)
        self.assertEqual(config.recency_weight, 0.25)

    def test_custom_values(self):
        """Test custom configuration values."""
        config = SearchConfig(
            k_chunks=100,
            top_n_sessions=3,
            similarity_threshold=0.5
        )
        self.assertEqual(config.k_chunks, 100)
        self.assertEqual(config.top_n_sessions, 3)
        self.assertEqual(config.similarity_threshold, 0.5)


class TestChunkingConfig(unittest.TestCase):
    """Test ChunkingConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ChunkingConfig()
        self.assertEqual(config.target_tokens, 750)
        self.assertEqual(config.overlap_tokens, 150)
        self.assertEqual(config.max_tokens, 1000)


class TestIndexingConfig(unittest.TestCase):
    """Test IndexingConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = IndexingConfig()
        self.assertEqual(config.debounce_delay, 5.0)
        self.assertEqual(config.checkpoint_interval, 15)
        self.assertTrue(config.enabled)


class TestServerConfig(unittest.TestCase):
    """Test ServerConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ServerConfig()
        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 8741)


class TestMemoryConfig(unittest.TestCase):
    """Test MemoryConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = MemoryConfig()
        self.assertEqual(config.max_memory_mb, 2000)
        self.assertTrue(config.gc_between_batches)


class TestConfig(unittest.TestCase):
    """Test Config dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = Config()
        self.assertIsInstance(config.embedding, EmbeddingConfig)
        self.assertIsInstance(config.search, SearchConfig)
        self.assertIsInstance(config.chunking, ChunkingConfig)
        self.assertIsInstance(config.indexing, IndexingConfig)
        self.assertIsInstance(config.server, ServerConfig)
        self.assertIsInstance(config.memory, MemoryConfig)
        self.assertEqual(config.storage_dir, "~/.smart-fork")

    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = Config()
        data = config.to_dict()

        self.assertIn("embedding", data)
        self.assertIn("search", data)
        self.assertIn("chunking", data)
        self.assertIn("indexing", data)
        self.assertIn("server", data)
        self.assertIn("memory", data)
        self.assertIn("storage_dir", data)

        self.assertEqual(data["embedding"]["model_name"], "nomic-ai/nomic-embed-text-v1.5")
        self.assertEqual(data["search"]["k_chunks"], 200)
        self.assertEqual(data["chunking"]["target_tokens"], 750)

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "embedding": {
                "model_name": "custom-model",
                "dimension": 512
            },
            "search": {
                "k_chunks": 100
            },
            "storage_dir": "/custom/path"
        }

        config = Config.from_dict(data)
        self.assertEqual(config.embedding.model_name, "custom-model")
        self.assertEqual(config.embedding.dimension, 512)
        self.assertEqual(config.search.k_chunks, 100)
        self.assertEqual(config.storage_dir, "/custom/path")

        # Check defaults for unspecified values
        self.assertEqual(config.embedding.batch_size, 32)
        self.assertEqual(config.search.top_n_sessions, 5)

    def test_roundtrip(self):
        """Test to_dict -> from_dict roundtrip."""
        config1 = Config()
        config1.embedding.model_name = "test-model"
        config1.search.k_chunks = 150

        data = config1.to_dict()
        config2 = Config.from_dict(data)

        self.assertEqual(config2.embedding.model_name, "test-model")
        self.assertEqual(config2.search.k_chunks, 150)


class TestConfigManager(unittest.TestCase):
    """Test ConfigManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"

    def tearDown(self):
        """Clean up test fixtures."""
        if self.config_path.exists():
            self.config_path.unlink()
        os.rmdir(self.temp_dir)

    def test_init_default_path(self):
        """Test initialization with default path."""
        manager = ConfigManager()
        expected_path = Path.home() / ".smart-fork" / "config.json"
        self.assertEqual(manager.config_path, expected_path)

    def test_init_custom_path(self):
        """Test initialization with custom path."""
        manager = ConfigManager(str(self.config_path))
        self.assertEqual(manager.config_path, self.config_path)

    def test_load_nonexistent_file(self):
        """Test loading when config file doesn't exist."""
        manager = ConfigManager(str(self.config_path))
        config = manager.load()

        self.assertIsInstance(config, Config)
        self.assertEqual(config.embedding.model_name, "nomic-ai/nomic-embed-text-v1.5")

    def test_save_and_load(self):
        """Test saving and loading configuration."""
        manager = ConfigManager(str(self.config_path))

        # Create and save config
        config = Config()
        config.embedding.model_name = "test-model"
        config.search.k_chunks = 150
        manager.save(config)

        self.assertTrue(self.config_path.exists())

        # Load config
        manager2 = ConfigManager(str(self.config_path))
        loaded_config = manager2.load()

        self.assertEqual(loaded_config.embedding.model_name, "test-model")
        self.assertEqual(loaded_config.search.k_chunks, 150)

    def test_save_without_config(self):
        """Test saving without setting config."""
        manager = ConfigManager(str(self.config_path))

        with self.assertRaises(ValueError):
            manager.save()

    def test_load_invalid_json(self):
        """Test loading invalid JSON."""
        # Write invalid JSON
        with open(self.config_path, 'w') as f:
            f.write("{ invalid json }")

        manager = ConfigManager(str(self.config_path))
        config = manager.load()

        # Should return default config
        self.assertIsInstance(config, Config)
        self.assertEqual(config.embedding.model_name, "nomic-ai/nomic-embed-text-v1.5")

    def test_get_loads_if_not_loaded(self):
        """Test get() loads config if not already loaded."""
        manager = ConfigManager(str(self.config_path))
        config = manager.get()

        self.assertIsInstance(config, Config)

    def test_get_returns_cached_config(self):
        """Test get() returns cached config."""
        manager = ConfigManager(str(self.config_path))
        config1 = manager.get()
        config2 = manager.get()

        self.assertIs(config1, config2)

    def test_update(self):
        """Test updating configuration values."""
        manager = ConfigManager(str(self.config_path))
        manager.load()

        manager.update(storage_dir="/new/path")
        manager.update(embedding={"model_name": "new-model", "batch_size": 64})

        config = manager.get()
        self.assertEqual(config.storage_dir, "/new/path")
        self.assertEqual(config.embedding.model_name, "new-model")
        self.assertEqual(config.embedding.batch_size, 64)

    def test_validate_valid_config(self):
        """Test validation with valid config."""
        manager = ConfigManager(str(self.config_path))
        manager.load()

        self.assertTrue(manager.validate())

    def test_validate_invalid_embedding_dimension(self):
        """Test validation with invalid embedding dimension."""
        manager = ConfigManager(str(self.config_path))
        config = manager.load()
        config.embedding.dimension = -1

        self.assertFalse(manager.validate())

    def test_validate_invalid_batch_size(self):
        """Test validation with invalid batch size."""
        manager = ConfigManager(str(self.config_path))
        config = manager.load()
        config.embedding.batch_size = 0

        self.assertFalse(manager.validate())

    def test_validate_invalid_batch_size_range(self):
        """Test validation with invalid batch size range."""
        manager = ConfigManager(str(self.config_path))
        config = manager.load()
        config.embedding.min_batch_size = 100
        config.embedding.max_batch_size = 50

        self.assertFalse(manager.validate())

    def test_validate_invalid_k_chunks(self):
        """Test validation with invalid k_chunks."""
        manager = ConfigManager(str(self.config_path))
        config = manager.load()
        config.search.k_chunks = 0

        self.assertFalse(manager.validate())

    def test_validate_invalid_similarity_threshold(self):
        """Test validation with invalid similarity threshold."""
        manager = ConfigManager(str(self.config_path))
        config = manager.load()
        config.search.similarity_threshold = 1.5

        self.assertFalse(manager.validate())

    def test_validate_invalid_recency_weight(self):
        """Test validation with invalid recency weight."""
        manager = ConfigManager(str(self.config_path))
        config = manager.load()
        config.search.recency_weight = -0.1

        self.assertFalse(manager.validate())

    def test_validate_invalid_token_sizes(self):
        """Test validation with invalid token sizes."""
        manager = ConfigManager(str(self.config_path))
        config = manager.load()
        config.chunking.target_tokens = 2000
        config.chunking.max_tokens = 1000

        self.assertFalse(manager.validate())

    def test_validate_invalid_port(self):
        """Test validation with invalid port."""
        manager = ConfigManager(str(self.config_path))
        config = manager.load()
        config.server.port = 80

        self.assertFalse(manager.validate())

    def test_validate_invalid_memory(self):
        """Test validation with invalid memory."""
        manager = ConfigManager(str(self.config_path))
        config = manager.load()
        config.memory.max_memory_mb = -100

        self.assertFalse(manager.validate())

    def test_reset(self):
        """Test resetting configuration."""
        manager = ConfigManager(str(self.config_path))
        config = manager.load()
        config.embedding.model_name = "custom-model"

        manager.reset()
        config = manager.get()

        self.assertEqual(config.embedding.model_name, "nomic-ai/nomic-embed-text-v1.5")


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"

    def tearDown(self):
        """Clean up test fixtures."""
        if self.config_path.exists():
            self.config_path.unlink()
        os.rmdir(self.temp_dir)

    def test_load_config(self):
        """Test load_config convenience function."""
        config = load_config(str(self.config_path))
        self.assertIsInstance(config, Config)

    def test_save_config(self):
        """Test save_config convenience function."""
        config = Config()
        config.embedding.model_name = "test-model"

        save_config(config, str(self.config_path))
        self.assertTrue(self.config_path.exists())

        # Verify saved content
        loaded_config = load_config(str(self.config_path))
        self.assertEqual(loaded_config.embedding.model_name, "test-model")


class TestThreadSafety(unittest.TestCase):
    """Test thread safety of ConfigManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"

    def tearDown(self):
        """Clean up test fixtures."""
        if self.config_path.exists():
            self.config_path.unlink()
        os.rmdir(self.temp_dir)

    def test_concurrent_reads(self):
        """Test concurrent reads are thread-safe."""
        import threading

        manager = ConfigManager(str(self.config_path))
        manager.load()

        results = []

        def read_config():
            config = manager.get()
            results.append(config.embedding.model_name)

        threads = [threading.Thread(target=read_config) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(results), 10)
        self.assertTrue(all(r == "nomic-ai/nomic-embed-text-v1.5" for r in results))


if __name__ == '__main__':
    unittest.main()
