#!/usr/bin/env python3
"""
Manual test script for /fork-detect MCP command handler.

This script verifies the implementation without requiring full dependencies.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 80)
print("Manual Test: /fork-detect MCP Command Handler")
print("=" * 80)

# Test 1: Verify server module can be imported
print("\n[Test 1] Importing server module...")
try:
    # We'll import with mocked dependencies
    import unittest.mock as mock

    # Mock all dependencies before importing
    sys.modules['psutil'] = mock.MagicMock()
    sys.modules['sentence_transformers'] = mock.MagicMock()
    sys.modules['torch'] = mock.MagicMock()

    # Mock chromadb properly
    chromadb_mock = mock.MagicMock()
    chromadb_config_mock = mock.MagicMock()
    chromadb_mock.config = chromadb_config_mock
    sys.modules['chromadb'] = chromadb_mock
    sys.modules['chromadb.config'] = chromadb_config_mock

    from smart_fork.server import (
        MCPServer,
        create_server,
        create_fork_detect_handler,
        format_search_results,
        initialize_services
    )
    print("✓ Server module imported successfully")
except Exception as e:
    print(f"✗ Failed to import server module: {e}")
    sys.exit(1)

# Test 2: Verify format_search_results handles empty results
print("\n[Test 2] Testing format_search_results with empty results...")
try:
    query = "test query"
    result = format_search_results(query, [])

    assert "No Results Found" in result, "Should indicate no results"
    assert query in result, "Should include the query"
    print("✓ Empty results formatted correctly")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Test 3: Verify format_search_results handles results with data
print("\n[Test 3] Testing format_search_results with mock results...")
try:
    from smart_fork.search_service import SessionSearchResult
    from smart_fork.scoring_service import SessionScore
    from smart_fork.session_registry import SessionMetadata

    # Create mock result
    score = SessionScore(
        session_id="test-session-123",
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
        session_id="test-session-123",
        project="test-project",
        created_at="2026-01-15T10:00:00",
        last_modified="2026-01-15T12:00:00",
        chunk_count=50,
        message_count=100,
        tags=["test", "auth"]
    )

    result = SessionSearchResult(
        session_id="test-session-123",
        score=score,
        metadata=metadata,
        preview="This is a test preview of session content...",
        matched_chunks=[]
    )

    output = format_search_results("implement auth", [result])

    # Verify key elements
    assert "Found 1 Relevant Session" in output
    assert "test-session-123" in output
    assert "78.00%" in output
    assert "test-project" in output
    assert "Best Similarity: 85.00%" in output
    assert "test, auth" in output

    print("✓ Results with data formatted correctly")
    print(f"  - Output length: {len(output)} characters")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Test 4: Verify create_fork_detect_handler with no search service
print("\n[Test 4] Testing fork_detect_handler without search service...")
try:
    handler = create_fork_detect_handler(None)
    result = handler({"query": "test query"})

    assert "Service Not Initialized" in result
    assert "test query" in result
    print("✓ Handler handles missing search service correctly")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Test 5: Verify create_fork_detect_handler with empty query
print("\n[Test 5] Testing fork_detect_handler with empty query...")
try:
    mock_search_service = mock.MagicMock()
    handler = create_fork_detect_handler(mock_search_service)
    result = handler({"query": ""})

    assert "Error" in result
    assert "provide a query" in result
    mock_search_service.search.assert_not_called()
    print("✓ Handler validates empty query correctly")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Test 6: Verify create_fork_detect_handler with mock search service
print("\n[Test 6] Testing fork_detect_handler with mock search service...")
try:
    from smart_fork.search_service import SessionSearchResult
    from smart_fork.scoring_service import SessionScore
    from smart_fork.session_registry import SessionMetadata

    mock_search_service = mock.MagicMock()

    # Create mock result
    score = SessionScore(
        session_id="test-session-123",
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
        session_id="session-456",
        project="auth-project",
        created_at="2026-01-15T10:00:00",
        last_modified="2026-01-15T12:00:00",
        chunk_count=50,
        message_count=100,
        tags=[]
    )

    mock_result = SessionSearchResult(
        session_id="session-456",
        score=score,
        metadata=metadata,
        preview="Authentication implementation preview",
        matched_chunks=[]
    )

    mock_search_service.search.return_value = [mock_result]

    handler = create_fork_detect_handler(mock_search_service)
    result = handler({"query": "implement authentication"})

    # Verify search was called
    mock_search_service.search.assert_called_once_with("implement authentication", top_n=5)

    # Verify output
    assert "Found 1 Relevant Session" in result
    assert "session-456" in result
    assert "implement authentication" in result

    print("✓ Handler calls search service and formats results correctly")
    print(f"  - Search called with query: 'implement authentication'")
    print(f"  - Result contains session ID and score")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Test 7: Verify create_server function
print("\n[Test 7] Testing create_server function...")
try:
    mock_search_service = mock.MagicMock()
    server = create_server(search_service=mock_search_service)

    assert isinstance(server, MCPServer)
    assert server.search_service == mock_search_service
    assert "fork-detect" in server.tools

    tool = server.tools["fork-detect"]
    assert tool["name"] == "fork-detect"
    assert "Search for relevant" in tool["description"]
    assert "query" in tool["inputSchema"]["properties"]

    print("✓ Server created with fork-detect tool registered")
    print(f"  - Tool name: {tool['name']}")
    print(f"  - Required parameters: {tool['inputSchema']['required']}")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Test 8: Verify MCP protocol integration
print("\n[Test 8] Testing MCP protocol integration...")
try:
    mock_search_service = mock.MagicMock()
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

    assert response is not None
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response

    content = response["result"]["content"]
    assert len(content) == 1
    assert content[0]["type"] == "text"
    assert "No Results Found" in content[0]["text"]

    print("✓ MCP protocol integration working correctly")
    print(f"  - Request method: {request['method']}")
    print(f"  - Response ID: {response['id']}")
    print(f"  - Content type: {content[0]['type']}")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Test 9: Verify error handling in handler
print("\n[Test 9] Testing error handling in fork_detect_handler...")
try:
    mock_search_service = mock.MagicMock()
    mock_search_service.search.side_effect = Exception("Test error")

    handler = create_fork_detect_handler(mock_search_service)
    result = handler({"query": "test query"})

    assert "Error" in result
    assert "Test error" in result

    print("✓ Handler handles exceptions correctly")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Test 10: Verify tools/list includes fork-detect
print("\n[Test 10] Testing tools/list MCP method...")
try:
    server = create_server(search_service=None)

    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }

    response = server.handle_request(request)

    assert response is not None
    assert "result" in response
    tools = response["result"]["tools"]

    assert len(tools) >= 1
    fork_detect_tool = next((t for t in tools if t["name"] == "fork-detect"), None)
    assert fork_detect_tool is not None

    print("✓ fork-detect tool listed in tools/list response")
    print(f"  - Total tools: {len(tools)}")
    print(f"  - fork-detect description: {fork_detect_tool['description'][:50]}...")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Summary
print("\n" + "=" * 80)
print("Summary: All 10 manual tests passed successfully!")
print("=" * 80)
print("\nVerifications completed:")
print("  ✓ Server module imports correctly")
print("  ✓ format_search_results handles empty results")
print("  ✓ format_search_results handles results with data")
print("  ✓ Handler handles missing search service")
print("  ✓ Handler validates empty query")
print("  ✓ Handler calls search service correctly")
print("  ✓ Server creates with fork-detect tool")
print("  ✓ MCP protocol integration works")
print("  ✓ Error handling works correctly")
print("  ✓ fork-detect listed in tools/list")
print("\nImplementation Status: ✓ COMPLETE")
print("\nTask 12 Requirements:")
print("  ✓ Register /fork-detect as MCP tool")
print("  ✓ Accept natural language description input")
print("  ✓ Call SearchService to find relevant sessions")
print("  ✓ Return formatted results")
print("  ✓ Handle empty/no-results case gracefully")
print("  ✓ Handle errors gracefully")
print("=" * 80)
