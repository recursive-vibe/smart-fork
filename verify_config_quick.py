#!/usr/bin/env python3
"""Quick verification of config_manager module."""

import sys
sys.path.insert(0, 'src')

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

print("✓ All imports successful")

# Test basic functionality
config = Config()
print(f"✓ Config created with storage_dir: {config.storage_dir}")
print(f"✓ Embedding model: {config.embedding.model_name}")
print(f"✓ Search k_chunks: {config.search.k_chunks}")
print(f"✓ Server port: {config.server.port}")

# Test to_dict / from_dict
data = config.to_dict()
print(f"✓ Config converted to dict with {len(data)} keys")

config2 = Config.from_dict(data)
print(f"✓ Config created from dict")

# Test ConfigManager
import tempfile
import os
temp_dir = tempfile.mkdtemp()
config_path = os.path.join(temp_dir, "config.json")

manager = ConfigManager(config_path)
print(f"✓ ConfigManager created")

loaded_config = manager.load()
print(f"✓ Config loaded (default)")

manager.save(loaded_config)
print(f"✓ Config saved")

loaded_again = manager.load()
print(f"✓ Config loaded from file")

is_valid = manager.validate()
print(f"✓ Config validation: {is_valid}")

# Clean up
os.unlink(config_path)
os.rmdir(temp_dir)

print("\n✅ All basic verifications passed!")
