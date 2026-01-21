"""Tests for project-scoped search functionality."""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from smart_fork.server import detect_project_from_cwd, create_fork_detect_handler
from smart_fork.search_service import SearchService, SessionSearchResult
from smart_fork.session_registry import SessionMetadata


class TestProjectDetection:
    """Test cases for project detection from CWD."""

    def test_detect_project_from_unix_path(self) -> None:
        """Test project detection from Unix-style path."""
        cwd = "/Users/john/Documents/MyProject"
        result = detect_project_from_cwd(cwd)
        assert result == "-Users-john-Documents-MyProject"

    def test_detect_project_from_windows_path(self) -> None:
        """Test project detection from Windows-style path."""
        # Note: Path.resolve() will convert relative paths to absolute
        # On Unix systems, even "C:\Users\..." will be resolved relative to CWD
        # This test mainly verifies the function handles different input formats gracefully
        with patch('os.sep', '\\'):
            # Use a path that won't be resolved by Path
            cwd = "C:\\Users\\john\\Documents\\MyProject"
            result = detect_project_from_cwd(cwd)
            # Just verify it returns a valid project name
            assert result is not None
            assert result.startswith("-")

    def test_detect_project_from_nested_path(self) -> None:
        """Test project detection from deeply nested path."""
        cwd = "/Users/john/Documents/Work/Projects/MyProject/src"
        result = detect_project_from_cwd(cwd)
        assert result == "-Users-john-Documents-Work-Projects-MyProject-src"

    def test_detect_project_with_spaces(self) -> None:
        """Test project detection with spaces in path."""
        cwd = "/Users/john/My Documents/My Project"
        result = detect_project_from_cwd(cwd)
        # Path resolution will normalize spaces, but the conversion should still work
        assert result.startswith("-Users-john-My")

    def test_detect_project_from_current_directory(self) -> None:
        """Test project detection using current directory."""
        result = detect_project_from_cwd()
        assert result is not None
        assert result.startswith("-")
        assert len(result) > 1

    def test_detect_project_with_invalid_path(self) -> None:
        """Test project detection with invalid path."""
        # Path.resolve() might raise an exception for invalid paths
        # The function should handle this gracefully
        result = detect_project_from_cwd("")
        # Should either return a valid project name or None
        assert result is None or result.startswith("-")


class TestForkDetectWithProjectScope:
    """Test cases for fork-detect handler with project scope."""

    @pytest.fixture
    def mock_search_service(self) -> Mock:
        """Create a mock search service."""
        service = Mock(spec=SearchService)
        service.search = Mock(return_value=[])
        return service

    @pytest.fixture
    def mock_session_registry(self) -> Mock:
        """Create a mock session registry."""
        registry = Mock()
        registry.get_stats = Mock(return_value={"total_sessions": 100})
        return registry

    def test_fork_detect_without_project_parameter(
        self, mock_search_service: Mock, mock_session_registry: Mock
    ) -> None:
        """Test fork-detect without project parameter searches all projects."""
        handler = create_fork_detect_handler(
            mock_search_service,
            claude_dir="~/.claude",
            session_registry=mock_session_registry
        )

        result = handler({"query": "test query"})

        # Verify search was called without filter
        mock_search_service.search.assert_called_once()
        call_args = mock_search_service.search.call_args
        assert call_args[0][0] == "test query"
        assert call_args[1].get("filter_metadata") is None

    def test_fork_detect_with_explicit_project(
        self, mock_search_service: Mock, mock_session_registry: Mock
    ) -> None:
        """Test fork-detect with explicit project parameter."""
        handler = create_fork_detect_handler(
            mock_search_service,
            claude_dir="~/.claude",
            session_registry=mock_session_registry
        )

        result = handler({
            "query": "test query",
            "project": "-Users-john-Documents-MyProject"
        })

        # Verify search was called with project filter
        mock_search_service.search.assert_called_once()
        call_args = mock_search_service.search.call_args
        assert call_args[0][0] == "test query"
        filter_metadata = call_args[1].get("filter_metadata")
        assert filter_metadata is not None
        assert filter_metadata["project"] == "-Users-john-Documents-MyProject"

    def test_fork_detect_with_current_project(
        self, mock_search_service: Mock, mock_session_registry: Mock
    ) -> None:
        """Test fork-detect with project='current' auto-detects from CWD."""
        handler = create_fork_detect_handler(
            mock_search_service,
            claude_dir="~/.claude",
            session_registry=mock_session_registry
        )

        with patch('smart_fork.server.detect_project_from_cwd') as mock_detect:
            mock_detect.return_value = "-Users-john-Documents-MyProject"

            result = handler({
                "query": "test query",
                "project": "current"
            })

            # Verify detection was called
            mock_detect.assert_called_once()

            # Verify search was called with detected project
            mock_search_service.search.assert_called_once()
            call_args = mock_search_service.search.call_args
            filter_metadata = call_args[1].get("filter_metadata")
            assert filter_metadata is not None
            assert filter_metadata["project"] == "-Users-john-Documents-MyProject"

    def test_fork_detect_with_scope_project(
        self, mock_search_service: Mock, mock_session_registry: Mock
    ) -> None:
        """Test fork-detect with scope='project' auto-detects from CWD."""
        handler = create_fork_detect_handler(
            mock_search_service,
            claude_dir="~/.claude",
            session_registry=mock_session_registry
        )

        with patch('smart_fork.server.detect_project_from_cwd') as mock_detect:
            mock_detect.return_value = "-Users-john-Documents-MyProject"

            result = handler({
                "query": "test query",
                "scope": "project"
            })

            # Verify detection was called
            mock_detect.assert_called_once()

            # Verify search was called with detected project
            mock_search_service.search.assert_called_once()
            call_args = mock_search_service.search.call_args
            filter_metadata = call_args[1].get("filter_metadata")
            assert filter_metadata is not None
            assert filter_metadata["project"] == "-Users-john-Documents-MyProject"

    def test_fork_detect_project_detection_fails(
        self, mock_search_service: Mock, mock_session_registry: Mock
    ) -> None:
        """Test fork-detect when project detection fails falls back to all projects."""
        handler = create_fork_detect_handler(
            mock_search_service,
            claude_dir="~/.claude",
            session_registry=mock_session_registry
        )

        with patch('smart_fork.server.detect_project_from_cwd') as mock_detect:
            mock_detect.return_value = None

            result = handler({
                "query": "test query",
                "project": "current"
            })

            # Verify search was called without filter (fallback behavior)
            mock_search_service.search.assert_called_once()
            call_args = mock_search_service.search.call_args
            filter_metadata = call_args[1].get("filter_metadata")
            assert filter_metadata is None

    def test_fork_detect_with_scope_all(
        self, mock_search_service: Mock, mock_session_registry: Mock
    ) -> None:
        """Test fork-detect with scope='all' searches all projects."""
        handler = create_fork_detect_handler(
            mock_search_service,
            claude_dir="~/.claude",
            session_registry=mock_session_registry
        )

        result = handler({
            "query": "test query",
            "scope": "all"
        })

        # Verify search was called without filter
        mock_search_service.search.assert_called_once()
        call_args = mock_search_service.search.call_args
        filter_metadata = call_args[1].get("filter_metadata")
        assert filter_metadata is None

    def test_fork_detect_displays_project_scope(
        self, mock_search_service: Mock, mock_session_registry: Mock
    ) -> None:
        """Test that fork-detect displays project scope in results."""
        handler = create_fork_detect_handler(
            mock_search_service,
            claude_dir="~/.claude",
            session_registry=mock_session_registry
        )

        # Mock search to return results
        mock_result = Mock(spec=SessionSearchResult)
        mock_result.session_id = "test-session-001"
        mock_result.score = Mock(final_score=0.95)
        mock_result.preview = "Test preview"
        mock_result.metadata = SessionMetadata(
            session_id="test-session-001",
            project="-Users-john-Documents-MyProject",
            created_at=1234567890,
            last_modified=1234567890,
            chunk_count=10,
            message_count=20,
            tags=[]
        )
        mock_search_service.search.return_value = [mock_result]

        result = handler({
            "query": "test query",
            "project": "-Users-john-Documents-MyProject"
        })

        # Verify result contains project scope information
        assert "Project:" in result or "Scope:" in result

    def test_fork_detect_empty_query_with_project(
        self, mock_search_service: Mock, mock_session_registry: Mock
    ) -> None:
        """Test fork-detect with empty query returns error even with project."""
        handler = create_fork_detect_handler(
            mock_search_service,
            claude_dir="~/.claude",
            session_registry=mock_session_registry
        )

        result = handler({
            "query": "",
            "project": "-Users-john-Documents-MyProject"
        })

        assert "Error" in result
        assert "provide a query" in result


class TestProjectScopeIntegration:
    """Integration tests for project-scoped search."""

    def test_project_filter_passed_to_vector_db(self) -> None:
        """Test that project filter is passed through to vector database."""
        # This is more of an integration test and would require a real SearchService
        # For now, we verify the flow by checking the mock calls
        mock_search_service = Mock(spec=SearchService)
        mock_search_service.search = Mock(return_value=[])

        handler = create_fork_detect_handler(
            mock_search_service,
            claude_dir="~/.claude",
            session_registry=Mock()
        )

        handler({
            "query": "authentication flow",
            "project": "-Users-john-Documents-AuthService"
        })

        # Verify the filter was passed correctly
        call_args = mock_search_service.search.call_args
        assert call_args[1]["filter_metadata"] == {
            "project": "-Users-john-Documents-AuthService"
        }
