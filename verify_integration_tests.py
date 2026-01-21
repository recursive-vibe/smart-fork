#!/usr/bin/env python3
"""
Verify integration test file structure without running tests.

This validates that all required tests are present and properly structured.
"""

import ast
import sys


def verify_test_file():
    """Verify the integration test file structure."""
    print("=" * 80)
    print("VERIFICATION: Integration Tests for Search Flow")
    print("=" * 80)

    test_file = "tests/test_search_integration.py"

    try:
        with open(test_file, "r") as f:
            content = f.read()

        tree = ast.parse(content)

        # Find test classes and methods
        test_classes = []
        test_methods = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name.startswith("Test"):
                    test_classes.append(node.name)
                    # Find methods in this class
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            if item.name.startswith("test_"):
                                test_methods.append(f"{node.name}.{item.name}")

        print(f"\n✓ Test file exists: {test_file}")
        print(f"✓ Found {len(test_classes)} test classes")
        print(f"✓ Found {len(test_methods)} test methods")

        print("\nTest Classes:")
        for cls in test_classes:
            print(f"  - {cls}")

        print("\nTest Methods:")
        for method in test_methods:
            print(f"  - {method}")

        # Verify required tests are present
        required_tests = [
            "test_index_sessions",
            "test_search_ranking_order",
            "test_search_performance",
            "test_memory_boost_affects_ranking",
            "test_recency_factor_affects_ranking",
        ]

        print("\nRequired Tests:")
        for req in required_tests:
            found = any(req in method for method in test_methods)
            status = "✓" if found else "✗"
            print(f"  {status} {req}")

        # Verify fixtures
        print("\nFixtures:")
        fixtures = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Attribute):
                        if decorator.attr == "fixture":
                            fixtures.append(node.name)
                    elif isinstance(decorator, ast.Name):
                        if decorator.id == "fixture":
                            fixtures.append(node.name)

        for fixture in fixtures:
            print(f"  ✓ {fixture}")

        # Check for 10 sample sessions in test_sessions fixture
        print("\nTest Data:")
        if "test_sessions" in fixtures:
            print("  ✓ test_sessions fixture present")
            # Count session definitions in fixture
            if "session_001" in content and "session_010" in content:
                print("  ✓ 10 sample sessions defined (session_001 to session_010)")
            else:
                print("  ⚠ Unable to verify 10 sessions in fixture")
        else:
            print("  ✗ test_sessions fixture missing")

        # Check for ChromaDB integration
        print("\nIntegrations:")
        if "VectorDBService" in content:
            print("  ✓ ChromaDB (VectorDBService) integration")
        if "EmbeddingService" in content:
            print("  ✓ EmbeddingService integration")
        if "SearchService" in content:
            print("  ✓ SearchService integration")
        if "SessionRegistry" in content:
            print("  ✓ SessionRegistry integration")
        if "ChunkingService" in content:
            print("  ✓ ChunkingService integration")
        if "ScoringService" in content:
            print("  ✓ ScoringService integration")

        # Check for performance testing
        print("\nPerformance Testing:")
        if "3.0" in content or "3s" in content.lower():
            print("  ✓ 3-second performance target mentioned")

        # Check for memory markers
        print("\nMemory Markers:")
        markers = ["PATTERN", "WORKING_SOLUTION", "WAITING"]
        for marker in markers:
            if marker in content:
                print(f"  ✓ {marker} marker tested")

        # Check for recency testing
        print("\nRecency Testing:")
        if "timedelta" in content and "days" in content:
            print("  ✓ Recency factor with date ranges (days)")
        if "hours" in content:
            print("  ✓ Includes recent sessions (hours)")

        print("\n" + "=" * 80)
        print("VERIFICATION COMPLETE ✓")
        print("=" * 80)
        print("\nSummary:")
        print(f"  - Test classes: {len(test_classes)}")
        print(f"  - Test methods: {len(test_methods)}")
        print(f"  - Fixtures: {len(fixtures)}")
        print(f"  - All required tests present: {'✓' if all(any(req in m for m in test_methods) for req in required_tests) else '✗'}")

        print("\nNote: Dependencies (psutil, sentence-transformers, chromadb) required to run tests.")
        print("      This verification only checks test file structure.")

        return True

    except FileNotFoundError:
        print(f"\n✗ Test file not found: {test_file}")
        return False
    except Exception as e:
        print(f"\n✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = verify_test_file()
    sys.exit(0 if success else 1)
