"""Test that the project structure is set up correctly."""

import sys
from pathlib import Path


def test_project_structure():
    """Verify that all required directories and files exist."""
    project_root = Path(__file__).parent.parent

    # Check directories
    assert (project_root / "src" / "smart_fork").exists()
    assert (project_root / "tests").exists()
    assert (project_root / "configs").exists()

    # Check key files
    assert (project_root / "pyproject.toml").exists()
    assert (project_root / "setup.py").exists()
    assert (project_root / "requirements.txt").exists()
    assert (project_root / "requirements-dev.txt").exists()
    assert (project_root / "src" / "smart_fork" / "__init__.py").exists()
    assert (project_root / "src" / "smart_fork" / "server.py").exists()


def test_import_smart_fork():
    """Test that smart_fork package can be imported."""
    # Add src to path for import
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root / "src"))

    import smart_fork
    assert smart_fork.__version__ == "0.1.0"


def test_server_module_exists():
    """Test that server module exists and has main function."""
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root / "src"))

    from smart_fork import server
    assert hasattr(server, "main")
    assert callable(server.main)
