"""Tests for REST API server."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from smart_fork.api_server import app, SearchRequest, IndexRequest
from smart_fork.scoring_service import SessionScore
from smart_fork.search_service import SessionSearchResult
from smart_fork.session_registry import SessionMetadata


# Test fixtures

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_search_service():
    """Create a mock search service."""
    service = MagicMock()
    service.vector_db = MagicMock()
    service.vector_db.get_stats.return_value = {
        "total_chunks": 100,
        "total_sessions": 10
    }
    service.get_stats.return_value = {
        "total_searches": 5,
        "avg_search_time_ms": 150.5
    }
    return service


@pytest.fixture
def mock_session_registry():
    """Create a mock session registry."""
    registry = MagicMock()
    registry.get_stats.return_value = {
        "total_sessions": 10,
        "total_chunks": 100,
        "total_messages": 500,
        "unique_projects": 3
    }
    return registry


@pytest.fixture
def mock_background_indexer():
    """Create a mock background indexer."""
    indexer = MagicMock()
    indexer.get_stats.return_value = {
        "files_indexed": 10,
        "chunks_added": 100,
        "errors": 0
    }
    return indexer


@pytest.fixture
def client(mock_search_service, mock_session_registry, mock_background_indexer):
    """Create a test client with mocked services."""
    # Patch the global service instances
    with patch('smart_fork.api_server.search_service', mock_search_service), \
         patch('smart_fork.api_server.session_registry', mock_session_registry), \
         patch('smart_fork.api_server.background_indexer', mock_background_indexer):
        yield TestClient(app)


# Test SearchRequest model

def test_search_request_valid():
    """Test SearchRequest with valid data."""
    request = SearchRequest(
        query="test query",
        k_chunks=100,
        top_n_sessions=3
    )
    assert request.query == "test query"
    assert request.k_chunks == 100
    assert request.top_n_sessions == 3
    assert request.metadata_filter is None


def test_search_request_defaults():
    """Test SearchRequest uses default values."""
    request = SearchRequest(query="test")
    assert request.k_chunks == 200
    assert request.top_n_sessions == 5


def test_search_request_with_metadata_filter():
    """Test SearchRequest with metadata filter."""
    request = SearchRequest(
        query="test",
        metadata_filter={"project": "my-project"}
    )
    assert request.metadata_filter == {"project": "my-project"}


# Test IndexRequest model

def test_index_request_valid():
    """Test IndexRequest with valid data."""
    request = IndexRequest(
        session_file="/path/to/session.jsonl",
        force_reindex=True
    )
    assert request.session_file == "/path/to/session.jsonl"
    assert request.force_reindex is True


def test_index_request_defaults():
    """Test IndexRequest uses default values."""
    request = IndexRequest(session_file="/path/to/session.jsonl")
    assert request.force_reindex is False


# Test POST /chunks/search endpoint

def test_search_chunks_success(client, mock_search_service):
    """Test successful chunk search."""
    # Setup mock response
    mock_score = SessionScore(
        session_id="test-session",
        final_score=0.85,
        best_similarity=0.9,
        avg_similarity=0.8,
        chunk_ratio=0.5,
        recency_score=0.7,
        chain_quality=0.5,
        memory_boost=0.0,
        num_chunks_matched=5
    )
    mock_metadata = SessionMetadata(
        session_id="test-session",
        project="test-project",
        created_at="2024-01-01T00:00:00",
        last_modified="2024-01-02T00:00:00",
        chunk_count=10,
        message_count=50,
        tags=["tag1"]
    )
    mock_result = SessionSearchResult(
        session_id="test-session",
        score=mock_score,
        metadata=mock_metadata,
        preview="This is a preview...",
        matched_chunks=[]
    )
    mock_search_service.search.return_value = [mock_result]

    # Make request
    response = client.post(
        "/chunks/search",
        json={
            "query": "test query",
            "k_chunks": 100,
            "top_n_sessions": 3
        }
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "test query"
    assert data["total_results"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["session_id"] == "test-session"
    assert data["results"][0]["score"]["final_score"] == 0.85
    assert "execution_time_ms" in data

    # Verify search service was called correctly
    mock_search_service.search.assert_called_once_with(
        query="test query",
        k_chunks=100,
        top_n_sessions=3,
        metadata_filter=None
    )


def test_search_chunks_with_metadata_filter(client, mock_search_service):
    """Test chunk search with metadata filter."""
    mock_search_service.search.return_value = []

    response = client.post(
        "/chunks/search",
        json={
            "query": "test query",
            "metadata_filter": {"project": "my-project"}
        }
    )

    assert response.status_code == 200
    mock_search_service.search.assert_called_once()
    call_args = mock_search_service.search.call_args
    assert call_args.kwargs["metadata_filter"] == {"project": "my-project"}


def test_search_chunks_empty_results(client, mock_search_service):
    """Test chunk search with no results."""
    mock_search_service.search.return_value = []

    response = client.post(
        "/chunks/search",
        json={"query": "nonexistent query"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] == 0
    assert data["results"] == []


def test_search_chunks_service_error(client, mock_search_service):
    """Test chunk search with service error."""
    mock_search_service.search.side_effect = Exception("Search failed")

    response = client.post(
        "/chunks/search",
        json={"query": "test query"}
    )

    assert response.status_code == 500
    assert "Search failed" in response.json()["detail"]


def test_search_chunks_missing_query(client):
    """Test chunk search without required query field."""
    response = client.post(
        "/chunks/search",
        json={}
    )

    assert response.status_code == 422  # Unprocessable Entity


# Test POST /sessions/index endpoint

def test_index_session_success(client, mock_background_indexer, mock_session_registry, temp_dir):
    """Test successful session indexing."""
    # Create a test session file
    session_file = temp_dir / "test-session.jsonl"
    session_file.write_text('{"role": "user", "content": "test"}\n')

    # Setup mocks
    mock_session_registry.get_session.return_value = None  # Not already indexed
    mock_background_indexer.index_file.return_value = True
    mock_background_indexer.get_stats.side_effect = [
        {"files_indexed": 0, "chunks_added": 0, "errors": 0},
        {"files_indexed": 1, "chunks_added": 10, "errors": 0}
    ]

    # Make request
    response = client.post(
        "/sessions/index",
        json={"session_file": str(session_file)}
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-session"
    assert data["status"] == "indexed"
    assert data["chunks_added"] == 10
    assert data["messages_processed"] == 1
    assert "execution_time_ms" in data

    # Verify indexer was called
    mock_background_indexer.index_file.assert_called_once_with(str(session_file))


def test_index_session_already_indexed(client, mock_background_indexer, mock_session_registry, temp_dir):
    """Test indexing already indexed session."""
    # Create a test session file
    session_file = temp_dir / "test-session.jsonl"
    session_file.write_text('{"role": "user", "content": "test"}\n')

    # Setup mock - session already exists
    mock_metadata = SessionMetadata(
        session_id="test-session",
        project="test-project",
        created_at="2024-01-01T00:00:00",
        last_modified="2024-01-02T00:00:00",
        last_synced="2024-01-02T00:00:00",
        chunk_count=10,
        message_count=50,
        tags=[]
    )
    mock_session_registry.get_session.return_value = mock_metadata

    # Make request
    response = client.post(
        "/sessions/index",
        json={"session_file": str(session_file)}
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "already_indexed"
    assert data["chunks_added"] == 0

    # Verify indexer was NOT called
    mock_background_indexer.index_file.assert_not_called()


def test_index_session_force_reindex(client, mock_background_indexer, mock_session_registry, temp_dir):
    """Test force reindexing of already indexed session."""
    # Create a test session file
    session_file = temp_dir / "test-session.jsonl"
    session_file.write_text('{"role": "user", "content": "test"}\n')

    # Setup mocks
    mock_metadata = SessionMetadata(
        session_id="test-session",
        project="test-project",
        created_at="2024-01-01T00:00:00",
        last_modified="2024-01-02T00:00:00",
        last_synced="2024-01-02T00:00:00",
        chunk_count=10,
        message_count=50,
        tags=[]
    )
    mock_session_registry.get_session.return_value = mock_metadata
    mock_background_indexer.index_file.return_value = True
    mock_background_indexer.get_stats.side_effect = [
        {"files_indexed": 0, "chunks_added": 0, "errors": 0},
        {"files_indexed": 1, "chunks_added": 10, "errors": 0}
    ]

    # Make request with force_reindex
    response = client.post(
        "/sessions/index",
        json={
            "session_file": str(session_file),
            "force_reindex": True
        }
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "indexed"

    # Verify indexer WAS called despite existing session
    mock_background_indexer.index_file.assert_called_once()


def test_index_session_file_not_found(client):
    """Test indexing nonexistent session file."""
    response = client.post(
        "/sessions/index",
        json={"session_file": "/nonexistent/path/session.jsonl"}
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_index_session_indexing_failed(client, mock_background_indexer, mock_session_registry, temp_dir):
    """Test indexing failure."""
    # Create a test session file
    session_file = temp_dir / "test-session.jsonl"
    session_file.write_text('{"role": "user", "content": "test"}\n')

    # Setup mocks
    mock_session_registry.get_session.return_value = None
    mock_background_indexer.index_file.return_value = False  # Indexing failed

    # Make request
    response = client.post(
        "/sessions/index",
        json={"session_file": str(session_file)}
    )

    # Verify response
    assert response.status_code == 500
    assert "Failed to index" in response.json()["detail"]


# Test GET /sessions/{session_id} endpoint

def test_get_session_success(client, mock_session_registry):
    """Test successful session retrieval."""
    # Setup mock
    mock_metadata = SessionMetadata(
        session_id="test-session",
        project="test-project",
        created_at="2024-01-01T00:00:00",
        last_modified="2024-01-02T00:00:00",
        last_synced="2024-01-02T00:00:00",
        chunk_count=10,
        message_count=50,
        tags=["tag1", "tag2"]
    )
    mock_session_registry.get_session.return_value = mock_metadata

    # Make request
    response = client.get("/sessions/test-session-id")

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-session-id"
    assert data["metadata"]["project"] == "test-project"
    assert data["metadata"]["chunk_count"] == 10
    assert data["metadata"]["message_count"] == 50
    assert data["metadata"]["tags"] == ["tag1", "tag2"]

    # Verify registry was called
    mock_session_registry.get_session.assert_called_once_with("test-session-id")


def test_get_session_not_found(client, mock_session_registry):
    """Test retrieving nonexistent session."""
    mock_session_registry.get_session.return_value = None

    response = client.get("/sessions/nonexistent-session")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


# Test GET /stats endpoint

def test_get_stats_success(client, mock_search_service, mock_session_registry, mock_background_indexer):
    """Test successful stats retrieval."""
    response = client.get("/stats")

    assert response.status_code == 200
    data = response.json()

    # Verify all stat categories are present
    assert "vector_db_stats" in data
    assert "registry_stats" in data
    assert "indexer_stats" in data
    assert "search_stats" in data

    # Verify specific stats
    assert data["vector_db_stats"]["total_chunks"] == 100
    assert data["registry_stats"]["total_sessions"] == 10
    assert data["indexer_stats"]["files_indexed"] == 10
    assert data["search_stats"]["total_searches"] == 5


# Test GET /health endpoint

def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "services" in data
    assert "timestamp" in data


# Test error handling

def test_search_chunks_service_unavailable():
    """Test search when service is not initialized."""
    with patch('smart_fork.api_server.search_service', None):
        client = TestClient(app)
        response = client.post(
            "/chunks/search",
            json={"query": "test"}
        )

    assert response.status_code == 503


def test_index_session_service_unavailable():
    """Test indexing when indexer is not initialized."""
    with patch('smart_fork.api_server.background_indexer', None):
        client = TestClient(app)
        response = client.post(
            "/sessions/index",
            json={"session_file": "/path/to/file.jsonl"}
        )

    assert response.status_code == 503


def test_get_session_service_unavailable():
    """Test session retrieval when registry is not initialized."""
    with patch('smart_fork.api_server.session_registry', None):
        client = TestClient(app)
        response = client.get("/sessions/test-session")

    assert response.status_code == 503


# Test request validation

def test_search_request_validation_k_chunks_too_low():
    """Test SearchRequest validation for k_chunks."""
    with pytest.raises(Exception):  # Pydantic validation error
        SearchRequest(query="test", k_chunks=0)


def test_search_request_validation_k_chunks_too_high():
    """Test SearchRequest validation for k_chunks."""
    with pytest.raises(Exception):  # Pydantic validation error
        SearchRequest(query="test", k_chunks=1001)


def test_search_request_validation_top_n_sessions_too_low():
    """Test SearchRequest validation for top_n_sessions."""
    with pytest.raises(Exception):  # Pydantic validation error
        SearchRequest(query="test", top_n_sessions=0)


def test_search_request_validation_top_n_sessions_too_high():
    """Test SearchRequest validation for top_n_sessions."""
    with pytest.raises(Exception):  # Pydantic validation error
        SearchRequest(query="test", top_n_sessions=51)
