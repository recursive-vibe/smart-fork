"""
Tests for the /fork-detect MCP command handler.

This module tests the integration of SearchService with the MCP server
and verifies the fork-detect tool functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

from smart_fork.server import (
    MCPServer,
    create_server,
    create_fork_detect_handler,
    format_search_results,
    initialize_services
)
from smart_fork.search_service import SessionSearchResult
from smart_fork.scoring_service import SessionScore
from smart_fork.session_registry import SessionMetadata


class TestFormatSearchResults(unittest.TestCase):
    """Test the format_search_results function."""

    def test_format_empty_results(self):
        """Test formatting when no results are found."""
        query = "test query"
        results = []

        output = format_search_results(query, results)

        self.assertIn("No Results Found", output)
        self.assertIn(query, output)
        self.assertIn("database is empty", output)

    def test_format_single_result(self):
        """Test formatting a single search result."""
        query = "implement authentication"

        score = SessionScore(
            session_id="session-123",
            best_similarity=0.85,
            avg_similarity=0.72,
            chunk_ratio=0.15,
            recency_score=0.90,
            chain_quality=0.5,
            memory_boost=0.05,
            final_score=0.78,
            num_chunks_matched=5
        )

        metadata = SessionMetadata(
            session_id="session-123",
            project="my-project",
            created_at="2026-01-15T10:00:00",
            last_modified="2026-01-15T12:00:00",
            chunk_count=50,
            message_count=100,
            tags=["auth", "security"]
        )

        result = SessionSearchResult(
            session_id="session-123",
            score=score,
            metadata=metadata,
            preview="This is a preview of the session content...",
            matched_chunks=[]
        )

        output = format_search_results(query, [result])

        # Verify key information is present
        self.assertIn("Found 1 Relevant Session", output)
        self.assertIn(query, output)
        self.assertIn("session-123", output)
        self.assertIn("78.00%", output)  # Final score
        self.assertIn("my-project", output)
        self.assertIn("Messages: 100", output)
        self.assertIn("Chunks: 50", output)
        self.assertIn("auth, security", output)
        self.assertIn("This is a preview", output)

        # Verify score breakdown
        self.assertIn("Best Similarity: 85.00%", output)
        self.assertIn("Avg Similarity: 72.00%", output)
        self.assertIn("Chunk Ratio: 15.00%", output)
        self.assertIn("Recency: 90.00%", output)
        self.assertIn("Chain Quality: 50.00%", output)
        self.assertIn("Memory Boost: +5.00%", output)

    def test_format_multiple_results(self):
        """Test formatting multiple search results."""
        query = "database optimization"

        results = []
        for i in range(3):
            score = SessionScore(
                session_id=f"session-{i}",
                best_similarity=0.9 - i*0.1,
                avg_similarity=0.7 - i*0.1,
                chunk_ratio=0.2,
                recency_score=0.8,
                chain_quality=0.5,
                memory_boost=0.0,
                final_score=0.8 - i*0.1,
                num_chunks_matched=10 + i
            )

            metadata = SessionMetadata(
                session_id=f"session-{i}",
                project=f"project-{i}",
                created_at="2026-01-15T10:00:00",
                last_modified="2026-01-15T12:00:00",
                chunk_count=50 + i*10,
                message_count=100 + i*20,
                tags=[]
            )

            result = SessionSearchResult(
                session_id=f"session-{i}",
                score=score,
                metadata=metadata,
                preview=f"Preview for session {i}",
                matched_chunks=[]
            )
            results.append(result)

        output = format_search_results(query, results)

        # Verify all results are present
        self.assertIn("Found 3 Relevant Session", output)
        for i in range(3):
            self.assertIn(f"session-{i}", output)
            self.assertIn(f"project-{i}", output)

    def test_format_result_without_metadata(self):
        """Test formatting when metadata is None."""
        query = "test"

        score = SessionScore(
            session_id="session-123",
            best_similarity=0.8,
            avg_similarity=0.7,
            chunk_ratio=0.1,
            recency_score=0.9,
            chain_quality=0.5,
            memory_boost=0.0,
            final_score=0.75,
            num_chunks_matched=5
        )

        result = SessionSearchResult(
            session_id="session-123",
            score=score,
            metadata=None,
            preview="Preview text",
            matched_chunks=[]
        )

        output = format_search_results(query, [result])

        # Should still format without errors
        self.assertIn("session-123", output)
        self.assertIn("75.00%", output)
        self.assertNotIn("Project:", output)

    def test_format_long_preview(self):
        """Test formatting truncates long previews."""
        query = "test"

        score = SessionScore(
            session_id="session-123",
            best_similarity=0.8,
            avg_similarity=0.7,
            chunk_ratio=0.1,
            recency_score=0.9,
            chain_quality=0.5,
            memory_boost=0.0,
            final_score=0.75,
            num_chunks_matched=5
        )

        # Create a preview with many lines
        long_preview = "\n".join([f"Line {i}" for i in range(10)])

        result = SessionSearchResult(
            session_id="session-123",
            score=score,
            metadata=None,
            preview=long_preview,
            matched_chunks=[]
        )

        output = format_search_results(query, [result])

        # Should show first 3 lines and ellipsis
        self.assertIn("Line 0", output)
        self.assertIn("Line 1", output)
        self.assertIn("Line 2", output)
        self.assertIn("...", output)


class TestForkDetectHandler(unittest.TestCase):
    """Test the fork_detect_handler function."""

    def test_handler_with_no_query(self):
        """Test handler with empty query."""
        mock_search_service = Mock()
        handler = create_fork_detect_handler(mock_search_service)

        result = handler({"query": ""})

        self.assertIn("Error", result)
        self.assertIn("provide a query", result)
        mock_search_service.search.assert_not_called()

    def test_handler_with_no_search_service(self):
        """Test handler when search service is None."""
        handler = create_fork_detect_handler(None)

        result = handler({"query": "test query"})

        self.assertIn("Service Not Initialized", result)
        self.assertIn("test query", result)

    def test_handler_successful_search(self):
        """Test handler with successful search."""
        mock_search_service = Mock()

        # Create mock result
        score = SessionScore(
            session_id="session-123",
            best_similarity=0.85,
            avg_similarity=0.72,
            chunk_ratio=0.15,
            recency_score=0.90,
            chain_quality=0.5,
            memory_boost=0.05,
            final_score=0.78,
            num_chunks_matched=5
        )

        metadata = SessionMetadata(
            session_id="session-123",
            project="test-project",
            created_at="2026-01-15T10:00:00",
            last_modified="2026-01-15T12:00:00",
            chunk_count=50,
            message_count=100,
            tags=[]
        )

        mock_result = SessionSearchResult(
            session_id="session-123",
            score=score,
            metadata=metadata,
            preview="Preview text",
            matched_chunks=[]
        )

        mock_search_service.search.return_value = [mock_result]

        handler = create_fork_detect_handler(mock_search_service)
        result = handler({"query": "implement auth"})

        # Verify search was called with correct parameters
        mock_search_service.search.assert_called_once_with("implement auth", top_n=5)

        # Verify output contains expected information
        self.assertIn("Found 1 Relevant Session", result)
        self.assertIn("implement auth", result)
        self.assertIn("session-123", result)

    def test_handler_no_results(self):
        """Test handler when no results are found."""
        mock_search_service = Mock()
        mock_search_service.search.return_value = []

        handler = create_fork_detect_handler(mock_search_service)
        result = handler({"query": "nonexistent topic"})

        self.assertIn("No Results Found", result)
        self.assertIn("nonexistent topic", result)

    def test_handler_error_handling(self):
        """Test handler when search raises an exception."""
        mock_search_service = Mock()
        mock_search_service.search.side_effect = Exception("Database error")

        handler = create_fork_detect_handler(mock_search_service)
        result = handler({"query": "test query"})

        self.assertIn("Error", result)
        self.assertIn("Database error", result)


class TestMCPServerIntegration(unittest.TestCase):
    """Test MCP server integration with fork-detect tool."""

    def test_server_with_search_service(self):
        """Test creating server with search service."""
        mock_search_service = Mock()
        server = create_server(search_service=mock_search_service)

        # Verify server is created
        self.assertIsInstance(server, MCPServer)
        self.assertEqual(server.search_service, mock_search_service)

        # Verify fork-detect tool is registered
        self.assertIn("fork-detect", server.tools)
        tool = server.tools["fork-detect"]
        self.assertEqual(tool["name"], "fork-detect")
        self.assertIn("Search for relevant", tool["description"])

    def test_server_without_search_service(self):
        """Test creating server without search service."""
        server = create_server(search_service=None)

        # Verify server is created
        self.assertIsInstance(server, MCPServer)
        self.assertIsNone(server.search_service)

        # Verify fork-detect tool is still registered
        self.assertIn("fork-detect", server.tools)

    def test_tool_call_through_server(self):
        """Test calling fork-detect through server protocol."""
        mock_search_service = Mock()
        mock_search_service.search.return_value = []

        server = create_server(search_service=mock_search_service)

        # Simulate tools/call request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "fork-detect",
                "arguments": {
                    "query": "test query"
                }
            }
        }

        response = server.handle_request(request)

        # Verify response structure
        self.assertIsNotNone(response)
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 1)
        self.assertIn("result", response)

        # Verify content
        content = response["result"]["content"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["type"], "text")
        self.assertIn("No Results Found", content[0]["text"])


class TestInitializeServices(unittest.TestCase):
    """Test service initialization."""

    def setUp(self):
        """Create temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('smart_fork.server.EmbeddingService')
    @patch('smart_fork.server.VectorDBService')
    @patch('smart_fork.server.ScoringService')
    @patch('smart_fork.server.SessionRegistry')
    @patch('smart_fork.server.SearchService')
    def test_initialize_services_success(
        self,
        mock_search_service,
        mock_session_registry,
        mock_scoring_service,
        mock_vector_db_service,
        mock_embedding_service
    ):
        """Test successful service initialization."""
        # Setup mocks
        mock_search_service.return_value = Mock()

        # Initialize services
        search_service = initialize_services(storage_dir=self.temp_dir)

        # Verify services were created
        self.assertIsNotNone(search_service)
        mock_embedding_service.assert_called_once()
        mock_vector_db_service.assert_called_once()
        mock_scoring_service.assert_called_once()
        mock_session_registry.assert_called_once()
        mock_search_service.assert_called_once()

        # Verify storage directory was created
        self.assertTrue(Path(self.temp_dir).exists())

    @patch('smart_fork.server.EmbeddingService')
    def test_initialize_services_failure(self, mock_embedding_service):
        """Test service initialization failure."""
        # Make initialization fail
        mock_embedding_service.side_effect = Exception("Init failed")

        # Initialize services
        search_service = initialize_services(storage_dir=self.temp_dir)

        # Should return None on failure
        self.assertIsNone(search_service)

    @patch('smart_fork.server.EmbeddingService')
    @patch('smart_fork.server.VectorDBService')
    @patch('smart_fork.server.ScoringService')
    @patch('smart_fork.server.SessionRegistry')
    @patch('smart_fork.server.SearchService')
    def test_initialize_services_default_path(
        self,
        mock_search_service,
        mock_session_registry,
        mock_scoring_service,
        mock_vector_db_service,
        mock_embedding_service
    ):
        """Test service initialization with default path."""
        mock_search_service.return_value = Mock()

        with patch('smart_fork.server.Path.mkdir'):
            search_service = initialize_services(storage_dir=None)

        # Should use default path and succeed
        self.assertIsNotNone(search_service)


if __name__ == '__main__':
    unittest.main()
