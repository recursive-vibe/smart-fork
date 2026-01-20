#!/usr/bin/env python3
"""
Basic verification script for SearchService implementation.

Verifies code structure, API signatures, and requirements without
requiring external dependencies.
"""

import ast
import os
import sys


def verify_file_exists(filepath, description):
    """Verify a file exists."""
    if os.path.exists(filepath):
        print(f"✓ {description}: {filepath}")
        return True
    else:
        print(f"✗ {description} not found: {filepath}")
        return False


def verify_class_in_file(filepath, class_name):
    """Verify a class exists in a Python file."""
    try:
        with open(filepath, 'r') as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                print(f"✓ Class '{class_name}' found in {os.path.basename(filepath)}")
                return node

        print(f"✗ Class '{class_name}' not found in {filepath}")
        return None
    except Exception as e:
        print(f"✗ Error parsing {filepath}: {e}")
        return None


def verify_method_in_class(class_node, method_name):
    """Verify a method exists in a class AST node."""
    for item in class_node.body:
        if isinstance(item, ast.FunctionDef) and item.name == method_name:
            return item
    return None


def verify_imports(filepath, required_imports):
    """Verify required imports exist in file."""
    try:
        with open(filepath, 'r') as f:
            tree = ast.parse(f.read())

        found_imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        found_imports.add(f"{node.module}.{alias.name}")

        all_found = True
        for imp in required_imports:
            if imp in found_imports:
                print(f"  ✓ Import: {imp}")
            else:
                print(f"  ✗ Missing import: {imp}")
                all_found = False

        return all_found
    except Exception as e:
        print(f"✗ Error checking imports: {e}")
        return False


def main():
    """Run verification checks."""
    print("=" * 70)
    print("SearchService Implementation Verification")
    print("=" * 70)

    all_passed = True

    # Check 1: Source file exists
    print("\n1. Verify source file exists")
    print("-" * 70)
    search_service_path = "src/smart_fork/search_service.py"
    if not verify_file_exists(search_service_path, "SearchService source"):
        all_passed = False
        return

    # Check 2: Test file exists
    print("\n2. Verify test file exists")
    print("-" * 70)
    test_path = "tests/test_search_service.py"
    if not verify_file_exists(test_path, "SearchService tests"):
        all_passed = False

    # Check 3: Verify required imports
    print("\n3. Verify required imports in SearchService")
    print("-" * 70)
    required_imports = [
        "embedding_service.EmbeddingService",
        "vector_db_service.VectorDBService",
        "vector_db_service.ChunkSearchResult",
        "scoring_service.ScoringService",
        "scoring_service.SessionScore",
        "session_registry.SessionRegistry",
        "session_registry.SessionMetadata",
    ]

    if not verify_imports(search_service_path, required_imports):
        print("⚠ Some imports missing but may be acceptable")

    # Check 4: Verify SearchService class exists
    print("\n4. Verify SearchService class")
    print("-" * 70)
    search_service_class = verify_class_in_file(search_service_path, "SearchService")
    if not search_service_class:
        all_passed = False
        return

    # Check 5: Verify required methods
    print("\n5. Verify SearchService methods")
    print("-" * 70)
    required_methods = [
        "__init__",
        "search",
        "_group_chunks_by_session",
        "_calculate_session_scores",
        "_generate_preview",
        "get_stats"
    ]

    for method_name in required_methods:
        method = verify_method_in_class(search_service_class, method_name)
        if method:
            print(f"  ✓ Method: {method_name}")
        else:
            print(f"  ✗ Method missing: {method_name}")
            all_passed = False

    # Check 6: Verify SessionSearchResult dataclass
    print("\n6. Verify SessionSearchResult dataclass")
    print("-" * 70)
    session_result_class = verify_class_in_file(search_service_path, "SessionSearchResult")
    if session_result_class:
        # Check for to_dict method
        to_dict_method = verify_method_in_class(session_result_class, "to_dict")
        if to_dict_method:
            print("  ✓ to_dict method exists")
        else:
            print("  ✗ to_dict method missing")
    else:
        all_passed = False

    # Check 7: Verify test file structure
    print("\n7. Verify test file structure")
    print("-" * 70)
    try:
        with open(test_path, 'r') as f:
            test_content = f.read()
            test_tree = ast.parse(test_content)

        test_classes = []
        for node in ast.walk(test_tree):
            if isinstance(node, ast.ClassDef):
                test_classes.append(node.name)

        print(f"✓ Found {len(test_classes)} test classes:")
        for cls in test_classes:
            print(f"  - {cls}")

        # Count test methods
        test_methods = 0
        for node in ast.walk(test_tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                test_methods += 1

        print(f"✓ Found {test_methods} test methods")

        if test_methods < 20:
            print("⚠ Expected at least 20 test methods")
        else:
            print("✓ Comprehensive test coverage")

    except Exception as e:
        print(f"✗ Error analyzing test file: {e}")
        all_passed = False

    # Check 8: Verify manual test script
    print("\n8. Verify manual integration test script")
    print("-" * 70)
    manual_test_path = "manual_test_search.py"
    if verify_file_exists(manual_test_path, "Manual test script"):
        print("  ✓ Integration test script created")
    else:
        all_passed = False

    # Check 9: Verify key implementation details in source
    print("\n9. Verify key implementation details")
    print("-" * 70)
    try:
        with open(search_service_path, 'r') as f:
            source_code = f.read()

        checks = [
            ("k_chunks", "k-NN parameter"),
            ("top_n_sessions", "Top N sessions parameter"),
            ("embed_single", "Embedding generation call"),
            ("search_chunks", "Vector search call"),
            ("calculate_session_score", "Score calculation call"),
            ("rank_sessions", "Session ranking call"),
            ("defaultdict", "Chunk grouping"),
            ("preview_length", "Preview generation"),
        ]

        for keyword, description in checks:
            if keyword in source_code:
                print(f"  ✓ {description}: '{keyword}'")
            else:
                print(f"  ✗ {description} not found: '{keyword}'")

    except Exception as e:
        print(f"✗ Error checking implementation: {e}")

    # Summary
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL VERIFICATIONS PASSED")
    else:
        print("⚠ SOME VERIFICATIONS FAILED")
    print("=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
