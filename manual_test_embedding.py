#!/usr/bin/env python3
"""Manual test script for EmbeddingService.

This script tests the embedding service with the actual Nomic model.
Run manually to verify integration.
"""

import logging
import sys
import time

from smart_fork.embedding_service import EmbeddingService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_model_loading():
    """Test 1: Model loading"""
    print("\n" + "="*80)
    print("TEST 1: Model Loading")
    print("="*80)

    try:
        service = EmbeddingService()
        print(f"✓ Service initialized")
        print(f"  Model: {service.model_name}")
        print(f"  Embedding dimension: {service.embedding_dimension}")

        print("\nLoading model (this may take a minute on first run)...")
        start_time = time.time()
        service.load_model()
        load_time = time.time() - start_time

        print(f"✓ Model loaded successfully in {load_time:.2f} seconds")
        return service
    except Exception as e:
        print(f"✗ Error loading model: {e}")
        return None


def test_single_embedding(service):
    """Test 2: Single text embedding"""
    print("\n" + "="*80)
    print("TEST 2: Single Text Embedding")
    print("="*80)

    try:
        text = "This is a test sentence for embedding generation."
        print(f"Input text: '{text}'")

        start_time = time.time()
        embedding = service.embed_single(text)
        embed_time = time.time() - start_time

        print(f"✓ Embedding generated in {embed_time:.3f} seconds")
        print(f"  Dimension: {len(embedding)}")
        print(f"  First 5 values: {embedding[:5]}")
        print(f"  Value range: [{min(embedding):.4f}, {max(embedding):.4f}]")

        assert len(embedding) == 768, "Embedding dimension should be 768"
        print("✓ Dimension check passed")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_batch_embedding(service):
    """Test 3: Batch embedding"""
    print("\n" + "="*80)
    print("TEST 3: Batch Embedding")
    print("="*80)

    try:
        texts = [
            "First test sentence about programming.",
            "Second test sentence about cats.",
            "Third test sentence about weather.",
            "Fourth test sentence about cooking.",
            "Fifth test sentence about music.",
        ]
        print(f"Number of texts: {len(texts)}")

        start_time = time.time()
        embeddings = service.embed_texts(texts)
        embed_time = time.time() - start_time

        print(f"✓ Batch embeddings generated in {embed_time:.3f} seconds")
        print(f"  Number of embeddings: {len(embeddings)}")
        print(f"  Each dimension: {len(embeddings[0])}")
        print(f"  Time per text: {embed_time/len(texts):.3f} seconds")

        assert len(embeddings) == len(texts), "Should have one embedding per text"
        assert all(len(emb) == 768 for emb in embeddings), "All embeddings should be 768-dim"
        print("✓ Batch embedding checks passed")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_semantic_similarity(service):
    """Test 4: Semantic similarity"""
    print("\n" + "="*80)
    print("TEST 4: Semantic Similarity")
    print("="*80)

    try:
        texts = [
            "The cat sat on the mat.",
            "A feline rested on the rug.",  # Similar meaning
            "Python is a programming language.",  # Different meaning
        ]

        print("Text 1 (reference): " + texts[0])
        print("Text 2 (similar):   " + texts[1])
        print("Text 3 (different): " + texts[2])

        embeddings = service.embed_texts(texts)

        # Calculate cosine similarity (embeddings are already normalized)
        def cosine_similarity(a, b):
            return sum(x * y for x, y in zip(a, b))

        sim_1_2 = cosine_similarity(embeddings[0], embeddings[1])
        sim_1_3 = cosine_similarity(embeddings[0], embeddings[2])

        print(f"\nSimilarity scores:")
        print(f"  Text 1 ↔ Text 2 (similar):   {sim_1_2:.4f}")
        print(f"  Text 1 ↔ Text 3 (different): {sim_1_3:.4f}")

        if sim_1_2 > sim_1_3:
            print("✓ Semantic similarity works correctly")
            print(f"  Similar texts have higher similarity ({sim_1_2:.4f} > {sim_1_3:.4f})")
            return True
        else:
            print("✗ Unexpected: dissimilar texts have higher similarity")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_memory_management(service):
    """Test 5: Memory management and adaptive batching"""
    print("\n" + "="*80)
    print("TEST 5: Memory Management & Adaptive Batching")
    print("="*80)

    try:
        # Check available memory
        available_mb = service.get_available_memory_mb()
        print(f"Available memory: {available_mb:.1f} MB")

        # Test batch size calculation
        batch_size = service.calculate_batch_size()
        print(f"Calculated batch size: {batch_size}")
        print(f"  Min batch size: {service.min_batch_size}")
        print(f"  Max batch size: {service.max_batch_size}")
        print(f"  Memory threshold: {service.memory_threshold_mb} MB")

        assert service.min_batch_size <= batch_size <= service.max_batch_size
        print("✓ Batch size within bounds")

        # Test with larger batch
        print("\nTesting batch processing with 50 texts...")
        texts = [f"Test sentence number {i} about various topics." for i in range(50)]

        start_time = time.time()
        embeddings = service.embed_texts(texts, batch_size=batch_size)
        embed_time = time.time() - start_time

        print(f"✓ Processed {len(texts)} texts in {embed_time:.3f} seconds")
        print(f"  Throughput: {len(texts)/embed_time:.1f} texts/second")
        print(f"  Average time per text: {embed_time/len(texts):.3f} seconds")

        assert len(embeddings) == 50
        print("✓ All embeddings generated successfully")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_model_unloading(service):
    """Test 6: Model unloading"""
    print("\n" + "="*80)
    print("TEST 6: Model Unloading")
    print("="*80)

    try:
        print("Unloading model...")
        service.unload_model()
        print("✓ Model unloaded")

        assert service.model is None
        print("✓ Model reference cleared")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("EMBEDDING SERVICE MANUAL TEST SUITE")
    print("="*80)
    print("\nThis will download the Nomic model on first run (~1GB)")
    print("Subsequent runs will use the cached model.")
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n\nTest cancelled.")
        sys.exit(0)

    results = []
    service = None

    # Test 1: Load model
    service = test_model_loading()
    results.append(("Model Loading", service is not None))

    if service is None:
        print("\n✗ Cannot continue without model. Exiting.")
        sys.exit(1)

    # Test 2-6: Run remaining tests
    results.append(("Single Embedding", test_single_embedding(service)))
    results.append(("Batch Embedding", test_batch_embedding(service)))
    results.append(("Semantic Similarity", test_semantic_similarity(service)))
    results.append(("Memory Management", test_memory_management(service)))
    results.append(("Model Unloading", test_model_unloading(service)))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed successfully!")
        sys.exit(0)
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
