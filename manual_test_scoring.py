#!/usr/bin/env python3
"""
Manual test script for ScoringService.

Runs comprehensive tests without pytest dependency.
"""

import sys
import os
from datetime import datetime, timedelta
import math

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from smart_fork.scoring_service import ScoringService, SessionScore


def test_group(name):
    """Decorator for test groups."""
    print(f"\n{'='*60}")
    print(f"TEST GROUP: {name}")
    print('='*60)


def assert_equal(actual, expected, msg=""):
    """Assert two values are equal."""
    if actual != expected:
        raise AssertionError(f"{msg}\nExpected: {expected}\nActual: {actual}")
    print(f"  ✓ {msg or 'Values equal'}")


def assert_close(actual, expected, tolerance=0.001, msg=""):
    """Assert two floats are close."""
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{msg}\nExpected: {expected}\nActual: {actual}\nDiff: {abs(actual - expected)}")
    print(f"  ✓ {msg or 'Values close'}")


def assert_true(condition, msg=""):
    """Assert condition is true."""
    if not condition:
        raise AssertionError(msg)
    print(f"  ✓ {msg or 'Condition true'}")


def main():
    """Run all tests."""
    total_tests = 0
    passed_tests = 0
    failed_tests = 0

    print("SCORING SERVICE MANUAL TEST SUITE")
    print("="*60)

    # Test 1: Initialization
    test_group("Initialization")
    try:
        service = ScoringService()
        assert_equal(service.chain_quality_placeholder, 0.5, "Default chain quality is 0.5")

        service_custom = ScoringService(chain_quality_placeholder=0.7)
        assert_equal(service_custom.chain_quality_placeholder, 0.7, "Custom chain quality is 0.7")

        passed_tests += 2
        total_tests += 2
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        failed_tests += 2
        total_tests += 2

    # Test 2: Best Similarity Calculation
    test_group("Best Similarity Calculation")
    try:
        service = ScoringService()

        # Single chunk
        score = service.calculate_session_score(
            session_id="test-1",
            chunk_similarities=[0.85],
            total_chunks_in_session=10
        )
        assert_equal(score.best_similarity, 0.85, "Best similarity with single chunk")

        # Multiple chunks
        score = service.calculate_session_score(
            session_id="test-2",
            chunk_similarities=[0.6, 0.9, 0.7, 0.85],
            total_chunks_in_session=20
        )
        assert_equal(score.best_similarity, 0.9, "Best similarity picks maximum")

        # Empty chunks
        score = service.calculate_session_score(
            session_id="test-3",
            chunk_similarities=[],
            total_chunks_in_session=10
        )
        assert_equal(score.best_similarity, 0.0, "Best similarity with no chunks is 0")

        passed_tests += 3
        total_tests += 3
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        failed_tests += 3
        total_tests += 3

    # Test 3: Average Similarity Calculation
    test_group("Average Similarity Calculation")
    try:
        service = ScoringService()

        # Single chunk
        score = service.calculate_session_score(
            session_id="test-1",
            chunk_similarities=[0.75],
            total_chunks_in_session=10
        )
        assert_equal(score.avg_similarity, 0.75, "Average similarity with single chunk")

        # Multiple chunks
        score = service.calculate_session_score(
            session_id="test-2",
            chunk_similarities=[0.6, 0.8, 0.7, 0.9],
            total_chunks_in_session=20
        )
        expected = (0.6 + 0.8 + 0.7 + 0.9) / 4
        assert_close(score.avg_similarity, expected, msg="Average similarity calculation")

        passed_tests += 2
        total_tests += 2
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        failed_tests += 2
        total_tests += 2

    # Test 4: Chunk Ratio Calculation
    test_group("Chunk Ratio Calculation")
    try:
        service = ScoringService()

        # All chunks matched
        score = service.calculate_session_score(
            session_id="test-1",
            chunk_similarities=[0.8, 0.7, 0.9, 0.85, 0.75],
            total_chunks_in_session=5
        )
        assert_equal(score.chunk_ratio, 1.0, "Chunk ratio when all matched")

        # Partial match
        score = service.calculate_session_score(
            session_id="test-2",
            chunk_similarities=[0.8, 0.7, 0.9],
            total_chunks_in_session=10
        )
        assert_close(score.chunk_ratio, 0.3, msg="Chunk ratio with partial match")

        # Zero total chunks
        score = service.calculate_session_score(
            session_id="test-3",
            chunk_similarities=[0.8],
            total_chunks_in_session=0
        )
        assert_equal(score.chunk_ratio, 0.0, "Chunk ratio with zero total chunks")

        passed_tests += 3
        total_tests += 3
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        failed_tests += 3
        total_tests += 3

    # Test 5: Recency Score Calculation
    test_group("Recency Score Calculation")
    try:
        service = ScoringService()
        current_time = datetime.now()

        # Recent session (1 hour old)
        last_modified = current_time - timedelta(hours=1)
        score = service.calculate_session_score(
            session_id="test-1",
            chunk_similarities=[0.8],
            total_chunks_in_session=10,
            session_last_modified=last_modified.isoformat(),
            current_time=current_time
        )
        assert_true(score.recency_score > 0.99, "Recent session has high recency score")

        # 30 days old (decay constant)
        last_modified = current_time - timedelta(days=30)
        score = service.calculate_session_score(
            session_id="test-2",
            chunk_similarities=[0.8],
            total_chunks_in_session=10,
            session_last_modified=last_modified.isoformat(),
            current_time=current_time
        )
        expected = math.exp(-1)
        assert_close(score.recency_score, expected, tolerance=0.01, msg="30-day-old session recency")

        # Very old session (365 days)
        last_modified = current_time - timedelta(days=365)
        score = service.calculate_session_score(
            session_id="test-3",
            chunk_similarities=[0.8],
            total_chunks_in_session=10,
            session_last_modified=last_modified.isoformat(),
            current_time=current_time
        )
        assert_true(score.recency_score < 0.01, "Very old session has low recency score")

        # No timestamp
        score = service.calculate_session_score(
            session_id="test-4",
            chunk_similarities=[0.8],
            total_chunks_in_session=10,
            session_last_modified=None
        )
        assert_equal(score.recency_score, 0.0, "No timestamp results in zero recency")

        # Invalid timestamp
        score = service.calculate_session_score(
            session_id="test-5",
            chunk_similarities=[0.8],
            total_chunks_in_session=10,
            session_last_modified="invalid"
        )
        assert_equal(score.recency_score, 0.0, "Invalid timestamp results in zero recency")

        # Future timestamp
        future_time = current_time + timedelta(days=1)
        score = service.calculate_session_score(
            session_id="test-6",
            chunk_similarities=[0.8],
            total_chunks_in_session=10,
            session_last_modified=future_time.isoformat(),
            current_time=current_time
        )
        assert_equal(score.recency_score, 1.0, "Future timestamp treated as age=0")

        passed_tests += 6
        total_tests += 6
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        failed_tests += 6
        total_tests += 6

    # Test 6: Memory Boost Calculation
    test_group("Memory Boost Calculation")
    try:
        service = ScoringService()

        # PATTERN boost
        score = service.calculate_session_score(
            session_id="test-1",
            chunk_similarities=[0.8],
            total_chunks_in_session=10,
            memory_types=['PATTERN']
        )
        assert_equal(score.memory_boost, 0.05, "PATTERN memory boost is +5%")

        # WORKING_SOLUTION boost
        score = service.calculate_session_score(
            session_id="test-2",
            chunk_similarities=[0.8],
            total_chunks_in_session=10,
            memory_types=['WORKING_SOLUTION']
        )
        assert_equal(score.memory_boost, 0.08, "WORKING_SOLUTION memory boost is +8%")

        # WAITING boost
        score = service.calculate_session_score(
            session_id="test-3",
            chunk_similarities=[0.8],
            total_chunks_in_session=10,
            memory_types=['WAITING']
        )
        assert_equal(score.memory_boost, 0.02, "WAITING memory boost is +2%")

        # Multiple types (additive)
        score = service.calculate_session_score(
            session_id="test-4",
            chunk_similarities=[0.8],
            total_chunks_in_session=10,
            memory_types=['PATTERN', 'WORKING_SOLUTION', 'WAITING']
        )
        expected = 0.05 + 0.08 + 0.02
        assert_close(score.memory_boost, expected, msg="Multiple memory types are additive")

        # Duplicate types (only count once)
        score = service.calculate_session_score(
            session_id="test-5",
            chunk_similarities=[0.8],
            total_chunks_in_session=10,
            memory_types=['PATTERN', 'PATTERN', 'PATTERN']
        )
        assert_equal(score.memory_boost, 0.05, "Duplicate memory types only count once")

        # No types
        score = service.calculate_session_score(
            session_id="test-6",
            chunk_similarities=[0.8],
            total_chunks_in_session=10,
            memory_types=None
        )
        assert_equal(score.memory_boost, 0.0, "No memory types results in zero boost")

        # Unknown types
        score = service.calculate_session_score(
            session_id="test-7",
            chunk_similarities=[0.8],
            total_chunks_in_session=10,
            memory_types=['UNKNOWN', 'INVALID']
        )
        assert_equal(score.memory_boost, 0.0, "Unknown memory types are ignored")

        passed_tests += 7
        total_tests += 7
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        failed_tests += 7
        total_tests += 7

    # Test 7: Final Score Composition
    test_group("Final Score Composition")
    try:
        service = ScoringService()
        current_time = datetime.now()

        # Test formula weights
        last_modified = current_time - timedelta(hours=1)
        score = service.calculate_session_score(
            session_id="test-1",
            chunk_similarities=[0.9, 0.8, 0.7],  # best=0.9, avg=0.8
            total_chunks_in_session=10,  # ratio=0.3
            session_last_modified=last_modified.isoformat(),
            current_time=current_time,
            memory_types=None
        )

        expected_base = (
            (0.9 * 0.40) +
            (0.8 * 0.20) +
            (0.3 * 0.05) +
            (score.recency_score * 0.25) +
            (0.5 * 0.10)
        )
        assert_close(score.final_score, expected_base, tolerance=0.01, msg="Final score uses correct weights")

        # Test with memory boost
        score = service.calculate_session_score(
            session_id="test-2",
            chunk_similarities=[0.9, 0.8],
            total_chunks_in_session=10,
            session_last_modified=last_modified.isoformat(),
            current_time=current_time,
            memory_types=['WORKING_SOLUTION']
        )

        expected_base = (
            (0.9 * 0.40) +
            (0.85 * 0.20) +
            (0.2 * 0.05) +
            (score.recency_score * 0.25) +
            (0.5 * 0.10)
        )
        expected_final = expected_base + 0.08
        assert_close(score.final_score, expected_final, tolerance=0.01, msg="Final score includes memory boost")

        # Empty chunks
        score = service.calculate_session_score(
            session_id="test-3",
            chunk_similarities=[],
            total_chunks_in_session=10
        )
        assert_equal(score.final_score, 0.0, "Empty chunks results in zero score")

        # Perfect match
        last_modified = current_time - timedelta(minutes=1)
        score = service.calculate_session_score(
            session_id="test-4",
            chunk_similarities=[1.0] * 10,
            total_chunks_in_session=10,
            session_last_modified=last_modified.isoformat(),
            current_time=current_time,
            memory_types=['PATTERN', 'WORKING_SOLUTION', 'WAITING']
        )
        assert_true(score.final_score > 1.0, "Perfect match with all boosts exceeds 1.0")

        passed_tests += 4
        total_tests += 4
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        failed_tests += 4
        total_tests += 4

    # Test 8: SessionScore to_dict
    test_group("SessionScore to_dict()")
    try:
        score = SessionScore(
            session_id="test-1",
            final_score=0.85,
            best_similarity=0.9,
            avg_similarity=0.8,
            chunk_ratio=0.5,
            recency_score=0.7,
            chain_quality=0.5,
            memory_boost=0.05,
            num_chunks_matched=5
        )

        result = score.to_dict()
        assert_equal(result['session_id'], "test-1", "session_id in dict")
        assert_equal(result['final_score'], 0.85, "final_score in dict")
        assert_equal(result['best_similarity'], 0.9, "best_similarity in dict")
        assert_equal(result['avg_similarity'], 0.8, "avg_similarity in dict")
        assert_equal(result['chunk_ratio'], 0.5, "chunk_ratio in dict")
        assert_equal(result['recency_score'], 0.7, "recency_score in dict")
        assert_equal(result['chain_quality'], 0.5, "chain_quality in dict")
        assert_equal(result['memory_boost'], 0.05, "memory_boost in dict")
        assert_equal(result['num_chunks_matched'], 5, "num_chunks_matched in dict")

        passed_tests += 9
        total_tests += 9
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        failed_tests += 9
        total_tests += 9

    # Test 9: Session Ranking
    test_group("Session Ranking")
    try:
        service = ScoringService()

        # Test sorting by score
        scores = [
            SessionScore("s1", 0.5, 0.6, 0.5, 0.3, 0.4, 0.5, 0.0, 3),
            SessionScore("s2", 0.9, 0.95, 0.9, 0.7, 0.8, 0.5, 0.05, 8),
            SessionScore("s3", 0.7, 0.8, 0.7, 0.5, 0.6, 0.5, 0.0, 5),
        ]

        ranked = service.rank_sessions(scores, top_k=3)
        assert_equal(ranked[0].session_id, "s2", "Top ranked is s2")
        assert_equal(ranked[1].session_id, "s3", "Second ranked is s3")
        assert_equal(ranked[2].session_id, "s1", "Third ranked is s1")

        # Test top_k limiting
        scores = [
            SessionScore(f"s{i}", float(i) / 10, 0.0, 0.0, 0.0, 0.0, 0.5, 0.0, 1)
            for i in range(10)
        ]
        ranked = service.rank_sessions(scores, top_k=3)
        assert_equal(len(ranked), 3, "Returns only top_k results")

        # Test fewer than k
        scores = [
            SessionScore("s1", 0.8, 0.8, 0.8, 0.5, 0.7, 0.5, 0.0, 5),
            SessionScore("s2", 0.6, 0.7, 0.6, 0.4, 0.5, 0.5, 0.0, 4),
        ]
        ranked = service.rank_sessions(scores, top_k=5)
        assert_equal(len(ranked), 2, "Returns all when fewer than top_k")

        # Test empty list
        ranked = service.rank_sessions([], top_k=5)
        assert_equal(len(ranked), 0, "Returns empty list for empty input")

        passed_tests += 7
        total_tests += 7
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        failed_tests += 7
        total_tests += 7

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total Tests:  {total_tests}")
    print(f"Passed:       {passed_tests}")
    print(f"Failed:       {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")

    if failed_tests == 0:
        print("\n✓ ALL TESTS PASSED")
        return 0
    else:
        print(f"\n✗ {failed_tests} TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
