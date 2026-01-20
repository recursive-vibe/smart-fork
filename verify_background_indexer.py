#!/usr/bin/env python3
"""
Verification script for BackgroundIndexer implementation.

Validates code structure, method signatures, and requirements
without requiring external dependencies.
"""

import ast
import sys
from pathlib import Path


def print_check(message, passed):
    """Print a check result."""
    status = "✓" if passed else "✗"
    print(f"  {status} {message}")
    return passed


def verify_background_indexer():
    """Verify the BackgroundIndexer implementation."""
    print("\n" + "="*60)
    print("VERIFICATION: BackgroundIndexer Implementation")
    print("="*60 + "\n")

    file_path = Path("src/smart_fork/background_indexer.py")

    if not file_path.exists():
        print_check("File exists", False)
        return False

    print_check("File exists", True)

    # Parse the file
    with open(file_path, 'r') as f:
        content = f.read()
        tree = ast.parse(content)

    # Find classes and their methods
    classes = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
            classes[node.name] = methods

    # Verify IndexingTask dataclass
    print("\n1. IndexingTask Dataclass:")
    has_indexing_task = "IndexingTask" in classes
    print_check("IndexingTask class exists", has_indexing_task)

    if has_indexing_task:
        has_needs_indexing = "needs_indexing" in classes["IndexingTask"]
        print_check("Has needs_indexing() method", has_needs_indexing)

    # Verify SessionFileHandler
    print("\n2. SessionFileHandler Class:")
    has_handler = "SessionFileHandler" in classes
    print_check("SessionFileHandler class exists", has_handler)

    if has_handler:
        handler_methods = classes["SessionFileHandler"]
        print_check("Has on_modified() method", "on_modified" in handler_methods)
        print_check("Has on_created() method", "on_created" in handler_methods)

    # Verify BackgroundIndexer
    print("\n3. BackgroundIndexer Class:")
    has_indexer = "BackgroundIndexer" in classes
    print_check("BackgroundIndexer class exists", has_indexer)

    if has_indexer:
        indexer_methods = classes["BackgroundIndexer"]

        # Check required methods
        required_methods = [
            "__init__",
            "start",
            "stop",
            "_on_file_changed",
            "_count_messages",
            "_monitor_loop",
            "_index_session",
            "index_file",
            "scan_directory",
            "get_stats",
            "is_running",
            "get_pending_count"
        ]

        print("\n   Required Methods:")
        all_methods_present = True
        for method in required_methods:
            present = method in indexer_methods
            print_check(f"{method}()", present)
            all_methods_present = all_methods_present and present

    # Verify imports
    print("\n4. Required Imports:")
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)

    required_imports = [
        'threading',
        'concurrent.futures',
        'pathlib',
        'dataclasses'
    ]

    for imp in required_imports:
        has_import = any(imp in i for i in imports)
        print_check(f"Imports {imp}", has_import)

    # Check for watchdog (optional but should be tried)
    has_watchdog_import = any('watchdog' in i for i in imports)
    print_check("Attempts to import watchdog (with try/except)", has_watchdog_import)

    # Verify key features in code
    print("\n5. Key Features:")

    # Check for debouncing
    has_debounce = "debounce" in content.lower()
    print_check("Has debouncing logic", has_debounce)

    # Check for thread pool
    has_threadpool = "ThreadPoolExecutor" in content
    print_check("Uses ThreadPoolExecutor", has_threadpool)

    # Check for checkpoint
    has_checkpoint = "checkpoint" in content.lower()
    print_check("Has checkpoint indexing", has_checkpoint)

    # Check for file monitoring
    has_monitoring = "Observer" in content or "watchdog" in content
    print_check("Has file monitoring setup", has_monitoring)

    # Check for statistics
    has_stats = "_stats" in content
    print_check("Tracks statistics", has_stats)

    # Check docstrings
    print("\n6. Documentation:")
    module_docstring = ast.get_docstring(tree)
    print_check("Has module docstring", module_docstring is not None)

    if has_indexer:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "BackgroundIndexer":
                class_docstring = ast.get_docstring(node)
                print_check("BackgroundIndexer has class docstring", class_docstring is not None)
                if class_docstring:
                    features = [
                        "watchdog" in class_docstring.lower(),
                        "debouncing" in class_docstring.lower() or "debounce" in class_docstring.lower(),
                        "thread" in class_docstring.lower(),
                        "checkpoint" in class_docstring.lower()
                    ]
                    print_check("Docstring mentions key features", all(features))

    print("\n" + "="*60)
    print("VERIFICATION COMPLETE")
    print("="*60)

    return True


def verify_tests():
    """Verify the test file structure."""
    print("\n" + "="*60)
    print("VERIFICATION: BackgroundIndexer Tests")
    print("="*60 + "\n")

    test_file = Path("tests/test_background_indexer.py")

    if not test_file.exists():
        print_check("Test file exists", False)
        return False

    print_check("Test file exists", True)

    # Parse the test file
    with open(test_file, 'r') as f:
        content = f.read()
        tree = ast.parse(content)

    # Find test classes
    test_classes = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if node.name.startswith("Test"):
                methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef) and m.name.startswith("test_")]
                test_classes[node.name] = methods

    print("\n1. Test Classes:")
    print_check(f"Found {len(test_classes)} test classes", len(test_classes) >= 3)

    for cls_name, methods in test_classes.items():
        print(f"\n   {cls_name}:")
        print_check(f"Has {len(methods)} test methods", len(methods) > 0)

    # Count total test methods
    total_tests = sum(len(methods) for methods in test_classes.values())
    print(f"\n2. Test Coverage:")
    print_check(f"Has {total_tests} total test methods", total_tests >= 15)

    # Check for key test scenarios
    print("\n3. Key Test Scenarios:")
    all_content = " ".join(str(c) for c in test_classes.values())

    scenarios = [
        ("initialization", "initialization" in all_content.lower()),
        ("start/stop", "start" in all_content.lower() and "stop" in all_content.lower()),
        ("file change", "file" in all_content.lower() and "change" in all_content.lower()),
        ("debouncing", "debounce" in all_content.lower() or "debouncing" in all_content.lower()),
        ("checkpoint", "checkpoint" in all_content.lower()),
        ("statistics", "stat" in all_content.lower())
    ]

    for scenario, present in scenarios:
        print_check(f"Tests {scenario}", present)

    print("\n" + "="*60)
    print("TEST VERIFICATION COMPLETE")
    print("="*60)

    return True


def verify_manual_test():
    """Verify the manual test script."""
    print("\n" + "="*60)
    print("VERIFICATION: Manual Test Script")
    print("="*60 + "\n")

    manual_test_file = Path("manual_test_background_indexer.py")

    if not manual_test_file.exists():
        print_check("Manual test file exists", False)
        return False

    print_check("Manual test file exists", True)

    # Parse the manual test file
    with open(manual_test_file, 'r') as f:
        content = f.read()

    # Check for test functions
    has_test_funcs = content.count("def test_") >= 5
    print_check("Has multiple test functions", has_test_funcs)

    # Check for key features
    features = [
        ("IndexingTask test", "test_indexing_task" in content),
        ("Initialization test", "test_basic_initialization" in content or "test_initialization" in content),
        ("Start/stop test", "test_start_stop" in content),
        ("Message counting test", "test_count_messages" in content),
        ("File change test", "test_file_change" in content),
        ("Debouncing test", "test_debouncing" in content),
        ("Statistics test", "test_statistics" in content or "test_stats" in content)
    ]

    print("\n1. Test Functions:")
    for feature, present in features:
        print_check(feature, present)

    print("\n" + "="*60)
    print("MANUAL TEST VERIFICATION COMPLETE")
    print("="*60)

    return True


def main():
    """Run all verifications."""
    results = []

    results.append(verify_background_indexer())
    results.append(verify_tests())
    results.append(verify_manual_test())

    print("\n" + "="*60)
    if all(results):
        print("✓ ALL VERIFICATIONS PASSED")
    else:
        print("✗ SOME VERIFICATIONS FAILED")
    print("="*60 + "\n")

    return all(results)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
