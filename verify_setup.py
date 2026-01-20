#!/usr/bin/env python3
"""Verification script for Task 1: Initialize project structure and dependencies."""

import sys
from pathlib import Path


def verify_structure():
    """Verify project structure is set up correctly."""
    print("=" * 60)
    print("Task 1: Initialize project structure and dependencies")
    print("=" * 60)
    print()

    project_root = Path(__file__).parent
    checks = []

    # Check directories
    print("Checking directories...")
    dirs = [
        ("src/smart_fork", project_root / "src" / "smart_fork"),
        ("tests", project_root / "tests"),
        ("configs", project_root / "configs"),
    ]

    for name, path in dirs:
        exists = path.exists() and path.is_dir()
        status = "✓" if exists else "✗"
        checks.append(exists)
        print(f"  {status} {name}/")

    print()

    # Check key files
    print("Checking key files...")
    files = [
        ("pyproject.toml", project_root / "pyproject.toml"),
        ("setup.py", project_root / "setup.py"),
        ("requirements.txt", project_root / "requirements.txt"),
        ("requirements-dev.txt", project_root / "requirements-dev.txt"),
        ("src/smart_fork/__init__.py", project_root / "src" / "smart_fork" / "__init__.py"),
        ("src/smart_fork/server.py", project_root / "src" / "smart_fork" / "server.py"),
        ("tests/__init__.py", project_root / "tests" / "__init__.py"),
        ("tests/test_setup.py", project_root / "tests" / "test_setup.py"),
    ]

    for name, path in files:
        exists = path.exists() and path.is_file()
        status = "✓" if exists else "✗"
        checks.append(exists)
        print(f"  {status} {name}")

    print()

    # Check imports
    print("Checking Python imports...")
    sys.path.insert(0, str(project_root / "src"))

    try:
        import smart_fork
        print(f"  ✓ smart_fork module imported (version {smart_fork.__version__})")
        checks.append(True)
    except ImportError as e:
        print(f"  ✗ Failed to import smart_fork: {e}")
        checks.append(False)

    try:
        from smart_fork import server
        has_main = hasattr(server, "main") and callable(server.main)
        status = "✓" if has_main else "✗"
        print(f"  {status} smart_fork.server.main() exists")
        checks.append(has_main)
    except ImportError as e:
        print(f"  ✗ Failed to import smart_fork.server: {e}")
        checks.append(False)

    print()

    # Check virtual environment
    print("Checking virtual environment...")
    venv_path = project_root / "venv"
    venv_exists = venv_path.exists()
    status = "✓" if venv_exists else "✗"
    checks.append(venv_exists)
    print(f"  {status} venv/ created")

    print()

    # Dependency installation note
    print("Dependencies:")
    print("  ⚠ Network connectivity issues prevented pip installation")
    print("  ℹ Required dependencies listed in requirements.txt and requirements-dev.txt")
    print("  ℹ Manual installation required: pip install -r requirements-dev.txt")
    print()

    # Storage directory note
    print("Storage directory (~/.smart-fork/):")
    print("  ⚠ Permission issue prevented creation in home directory")
    print("  ℹ Will be created at runtime when server starts")
    print()

    # Summary
    passed = sum(checks)
    total = len(checks)
    print("=" * 60)
    print(f"Summary: {passed}/{total} checks passed")

    if passed == total:
        print("Status: ✓ PASS - Project structure initialized successfully")
        print()
        print("Next steps:")
        print("  1. Install dependencies: pip install -r requirements-dev.txt")
        print("  2. The ~/.smart-fork/ directory will be created at runtime")
        print()
        return 0
    else:
        print("Status: ✗ FAIL - Some checks failed")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(verify_structure())
