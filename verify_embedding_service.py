#!/usr/bin/env python3
"""Verification script for EmbeddingService (no pytest required)."""

import sys
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, 'src')

from smart_fork.embedding_service import EmbeddingService


def test_init():
    """Test initialization."""
    print("Test: Initialization")
    service = EmbeddingService()
    assert service.model_name == "nomic-ai/nomic-embed-text-v1.5"
    assert service.embedding_dimension == 768
    assert service.min_batch_size == 8
    assert service.max_batch_size == 128
    assert service.model is None
    print("  ✓ Default initialization works")

    service2 = EmbeddingService(
        model_name="custom/model",
        min_batch_size=4,
        max_batch_size=64
    )
    assert service2.model_name == "custom/model"
    assert service2.min_batch_size == 4
    print("  ✓ Custom initialization works")
    return True


def test_memory_calculation():
    """Test memory calculation."""
    print("\nTest: Memory calculation")

    with patch("psutil.virtual_memory") as mock_mem:
        # Test with high memory (2GB)
        mock_mem.return_value = MagicMock(available=2 * 1024 * 1024 * 1024)
        service = EmbeddingService()
        mem_mb = service.get_available_memory_mb()
        assert mem_mb == 2048.0
        print(f"  ✓ Available memory calculation: {mem_mb} MB")

        # Test batch size with high memory
        batch_size = service.calculate_batch_size()
        assert batch_size == service.max_batch_size
        print(f"  ✓ Batch size with high memory: {batch_size}")

        # Test with low memory (300MB)
        mock_mem.return_value = MagicMock(available=300 * 1024 * 1024)
        batch_size = service.calculate_batch_size()
        assert batch_size == service.min_batch_size
        print(f"  ✓ Batch size with low memory: {batch_size}")

    return True


def test_model_loading():
    """Test model loading."""
    print("\nTest: Model loading")

    with patch("smart_fork.embedding_service.SentenceTransformer") as mock_transformer:
        mock_model = MagicMock()
        mock_transformer.return_value = mock_model

        service = EmbeddingService()
        service.load_model()

        assert service.model == mock_model
        assert mock_transformer.called
        print("  ✓ Model loading works")

        # Test loading twice (should only load once)
        service.load_model()
        assert mock_transformer.call_count == 1
        print("  ✓ Model only loaded once")

    return True


def test_embedding_generation():
    """Test embedding generation."""
    print("\nTest: Embedding generation")

    with patch("smart_fork.embedding_service.SentenceTransformer") as mock_transformer:
        with patch("psutil.virtual_memory") as mock_mem:
            mock_mem.return_value = MagicMock(available=2 * 1024 * 1024 * 1024)
            mock_model = MagicMock()

            # Mock encode to return proper numpy-like arrays
            def mock_encode(texts, **kwargs):
                import numpy as np
                return np.array([[0.1] * 768 for _ in texts])

            mock_model.encode = mock_encode
            mock_transformer.return_value = mock_model

            service = EmbeddingService()

            # Test single text
            embeddings = service.embed_texts("test")
            assert len(embeddings) == 1
            assert len(embeddings[0]) == 768
            print("  ✓ Single text embedding works")

            # Test multiple texts
            embeddings = service.embed_texts(["text1", "text2", "text3"])
            assert len(embeddings) == 3
            assert all(len(emb) == 768 for emb in embeddings)
            print("  ✓ Multiple text embedding works")

            # Test empty list
            embeddings = service.embed_texts([])
            assert embeddings == []
            print("  ✓ Empty list handling works")

            # Test embed_single
            embedding = service.embed_single("test")
            assert len(embedding) == 768
            print("  ✓ embed_single() works")

    return True


def test_batching():
    """Test batching logic."""
    print("\nTest: Batching")

    with patch("smart_fork.embedding_service.SentenceTransformer") as mock_transformer:
        with patch("psutil.virtual_memory") as mock_mem:
            with patch("gc.collect") as mock_gc:
                mock_mem.return_value = MagicMock(available=2 * 1024 * 1024 * 1024)
                mock_model = MagicMock()

                call_count = 0
                def mock_encode(texts, **kwargs):
                    import numpy as np
                    nonlocal call_count
                    call_count += 1
                    return np.array([[0.1] * 768 for _ in texts])

                mock_model.encode = mock_encode
                mock_transformer.return_value = mock_model

                service = EmbeddingService()

                # Test with 20 texts, batch size 8
                # Should create 3 batches: 8, 8, 4
                texts = [f"text {i}" for i in range(20)]
                embeddings = service.embed_texts(texts, batch_size=8)

                assert len(embeddings) == 20
                assert call_count == 3
                print(f"  ✓ Batching works (3 batches for 20 texts)")

                # Garbage collection should be called between batches
                assert mock_gc.call_count >= 2
                print(f"  ✓ Garbage collection called {mock_gc.call_count} times")

    return True


def test_model_unloading():
    """Test model unloading."""
    print("\nTest: Model unloading")

    with patch("smart_fork.embedding_service.SentenceTransformer") as mock_transformer:
        with patch("gc.collect") as mock_gc:
            mock_model = MagicMock()
            mock_transformer.return_value = mock_model

            service = EmbeddingService()
            service.load_model()
            assert service.model is not None

            service.unload_model()
            assert service.model is None
            assert mock_gc.called
            print("  ✓ Model unloading works")

    return True


def test_dimension():
    """Test dimension getter."""
    print("\nTest: Dimension getter")
    service = EmbeddingService()
    assert service.get_embedding_dimension() == 768
    print("  ✓ Dimension getter works")
    return True


def main():
    """Run all tests."""
    print("="*80)
    print("EMBEDDING SERVICE VERIFICATION")
    print("="*80)

    tests = [
        ("Initialization", test_init),
        ("Memory Calculation", test_memory_calculation),
        ("Model Loading", test_model_loading),
        ("Embedding Generation", test_embedding_generation),
        ("Batching", test_batching),
        ("Model Unloading", test_model_unloading),
        ("Dimension Getter", test_dimension),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, True))
        except Exception as e:
            print(f"  ✗ {name} failed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All verification tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
