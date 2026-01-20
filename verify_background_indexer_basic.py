#!/usr/bin/env python3
"""
Basic verification for BackgroundIndexer implementation.

This script verifies the code structure and API without running full tests.
"""

import ast
import sys
from pathlib import Path


def verify_file_exists():
    """Verify the background_indexer.py file exists."""
    file_path = Path('src/smart_fork/background_indexer.py')
    if not file_path.exists():
        return False, f"File not found: {file_path}"
    return True, f"✓ File exists: {file_path}"


def verify_code_structure():
    """Verify the code structure using AST parsing."""
    file_path = Path('src/smart_fork/background_indexer.py')

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content)
    except Exception as e:
        return False, f"Failed to parse file: {e}"

    # Find classes
    classes = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}

    # Verify required classes exist
    required_classes = ['BackgroundIndexer', 'IndexingTask', 'SessionFileHandler']
    for class_name in required_classes:
        if class_name not in classes:
            return False, f"Missing class: {class_name}"

    # Verify BackgroundIndexer methods
    indexer_class = classes['BackgroundIndexer']
    methods = {node.name for node in ast.walk(indexer_class) if isinstance(node, ast.FunctionDef)}

    required_methods = [
        '__init__',
        'start',
        'stop',
        '_on_file_changed',
        '_count_messages',
        '_monitor_loop',
        '_index_session',
        'index_file',
        'scan_directory',
        'get_stats',
        'is_running',
        'get_pending_count'
    ]

    missing_methods = [m for m in required_methods if m not in methods]
    if missing_methods:
        return False, f"Missing methods in BackgroundIndexer: {missing_methods}"

    return True, f"✓ All required classes and methods present"


def verify_imports():
    """Verify required imports."""
    file_path = Path('src/smart_fork/background_indexer.py')

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    required_imports = [
        'watchdog',
        'SessionParser',
        'ChunkingService',
        'EmbeddingService',
        'VectorDBService',
        'SessionRegistry',
        'threading',
        'concurrent.futures',
    ]

    missing = []
    for imp in required_imports:
        if imp not in content:
            missing.append(imp)

    if missing:
        return False, f"Missing imports: {missing}"

    return True, "✓ All required imports present"


def verify_test_file():
    """Verify test file exists and has test classes."""
    test_path = Path('tests/test_background_indexer.py')

    if not test_path.exists():
        return False, f"Test file not found: {test_path}"

    with open(test_path, 'r', encoding='utf-8') as f:
        content = f.read()

    tree = ast.parse(content)
    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

    required_test_classes = [
        'TestIndexingTask',
        'TestSessionFileHandler',
        'TestBackgroundIndexer',
        'TestBackgroundIndexerIntegration'
    ]

    missing = [c for c in required_test_classes if c not in classes]
    if missing:
        return False, f"Missing test classes: {missing}"

    return True, f"✓ Test file exists with all required test classes"


def verify_manual_test():
    """Verify manual test file exists."""
    manual_test = Path('manual_test_background_indexer.py')

    if not manual_test.exists():
        return False, f"Manual test file not found: {manual_test}"

    return True, f"✓ Manual test file exists: {manual_test}"


def verify_features():
    """Verify key features are implemented."""
    file_path = Path('src/smart_fork/background_indexer.py')

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    features = {
        'debounce_seconds': 'Debouncing support',
        'checkpoint_interval': 'Checkpoint indexing',
        'ThreadPoolExecutor': 'Thread pool processing',
        'Observer': 'File system monitoring with watchdog',
        '_pending_tasks': 'Pending task management',
        'current_time - task.last_modified >= self.debounce_seconds': 'Debouncing logic',
    }

    results = []
    for feature, description in features.items():
        if feature in content:
            results.append(f"  ✓ {description}")
        else:
            return False, f"Missing feature: {description}"

    return True, "✓ All key features implemented:\n" + "\n".join(results)


def main():
    """Run all verifications."""
    print("=" * 70)
    print("BackgroundIndexer Implementation Verification")
    print("=" * 70)

    verifications = [
        ("File exists", verify_file_exists),
        ("Code structure", verify_code_structure),
        ("Imports", verify_imports),
        ("Test file", verify_test_file),
        ("Manual test file", verify_manual_test),
        ("Key features", verify_features),
    ]

    all_passed = True

    for name, verify_func in verifications:
        print(f"\n{name}:")
        try:
            passed, message = verify_func()
            print(f"  {message}")
            if not passed:
                all_passed = False
        except Exception as e:
            print(f"  ✗ Error: {e}")
            all_passed = False
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    if all_passed:
        print("✓ All verifications passed!")
        print("=" * 70)
        return 0
    else:
        print("✗ Some verifications failed")
        print("=" * 70)
        return 1


if __name__ == '__main__':
    sys.exit(main())
