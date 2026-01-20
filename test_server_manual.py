#!/usr/bin/env python3
"""Manual test script for MCP server (no pytest required)."""

import json
import sys
from io import StringIO
from smart_fork.server import MCPServer, create_server, fork_detect_handler


def test_server_initialization():
    """Test that server initializes correctly."""
    server = MCPServer()
    assert server.server_info["name"] == "smart-fork", "Server name incorrect"
    assert server.server_info["version"] == "0.1.0", "Server version incorrect"
    assert len(server.tools) == 0, "Server should start with no tools"
    print("✓ Server initialization")


def test_register_tool():
    """Test tool registration."""
    server = MCPServer()

    def dummy_handler(args):
        return "test"

    server.register_tool(
        name="test-tool",
        description="A test tool",
        input_schema={"type": "object"},
        handler=dummy_handler
    )

    assert "test-tool" in server.tools, "Tool not registered"
    assert server.tools["test-tool"]["name"] == "test-tool", "Tool name incorrect"
    print("✓ Tool registration")


def test_handle_initialize():
    """Test initialize request handling."""
    server = MCPServer()
    result = server.handle_initialize({})

    assert result["protocolVersion"] == "2024-11-05", "Protocol version incorrect"
    assert "capabilities" in result, "Missing capabilities"
    assert "serverInfo" in result, "Missing server info"
    assert result["serverInfo"]["name"] == "smart-fork", "Server name incorrect in response"
    print("✓ Initialize handler")


def test_handle_tools_list_empty():
    """Test tools/list with no tools registered."""
    server = MCPServer()
    result = server.handle_tools_list({})

    assert "tools" in result, "Missing tools in response"
    assert result["tools"] == [], "Tools list should be empty"
    print("✓ Tools list (empty)")


def test_handle_tools_list_with_tools():
    """Test tools/list with registered tools."""
    server = create_server()
    result = server.handle_tools_list({})

    assert "tools" in result, "Missing tools in response"
    assert len(result["tools"]) == 1, "Should have exactly 1 tool"
    assert result["tools"][0]["name"] == "fork-detect", "Tool name incorrect"
    assert "description" in result["tools"][0], "Missing description"
    assert "inputSchema" in result["tools"][0], "Missing input schema"
    print("✓ Tools list (with tools)")


def test_handle_tools_call():
    """Test tools/call request handling."""
    server = create_server()

    result = server.handle_tools_call({
        "name": "fork-detect",
        "arguments": {"query": "test query"}
    })

    assert "content" in result, "Missing content in response"
    assert len(result["content"]) > 0, "Content should not be empty"
    assert result["content"][0]["type"] == "text", "Content type incorrect"
    assert "test query" in result["content"][0]["text"], "Query not in response"
    print("✓ Tools call")


def test_handle_tools_call_unknown_tool():
    """Test tools/call with unknown tool raises error."""
    server = MCPServer()

    try:
        server.handle_tools_call({
            "name": "unknown-tool",
            "arguments": {}
        })
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unknown tool" in str(e), "Error message incorrect"
    print("✓ Unknown tool error")


def test_handle_request_initialize():
    """Test full request handling for initialize."""
    server = MCPServer()
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }

    response = server.handle_request(request)

    assert response is not None, "Response should not be None"
    assert response["jsonrpc"] == "2.0", "JSON-RPC version incorrect"
    assert response["id"] == 1, "Request ID mismatch"
    assert "result" in response, "Missing result"
    assert response["result"]["serverInfo"]["name"] == "smart-fork", "Server name incorrect"
    print("✓ Full initialize request")


def test_handle_request_tools_list():
    """Test full request handling for tools/list."""
    server = create_server()
    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }

    response = server.handle_request(request)

    assert response is not None, "Response should not be None"
    assert response["jsonrpc"] == "2.0", "JSON-RPC version incorrect"
    assert response["id"] == 2, "Request ID mismatch"
    assert "result" in response, "Missing result"
    assert "tools" in response["result"], "Missing tools in result"
    print("✓ Full tools/list request")


def test_handle_request_tools_call():
    """Test full request handling for tools/call."""
    server = create_server()
    request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "fork-detect",
            "arguments": {"query": "test"}
        }
    }

    response = server.handle_request(request)

    assert response is not None, "Response should not be None"
    assert response["jsonrpc"] == "2.0", "JSON-RPC version incorrect"
    assert response["id"] == 3, "Request ID mismatch"
    assert "result" in response, "Missing result"
    assert "content" in response["result"], "Missing content in result"
    print("✓ Full tools/call request")


def test_handle_request_notification():
    """Test handling of notifications (no response expected)."""
    server = MCPServer()
    request = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {}
    }

    response = server.handle_request(request)

    assert response is None, "Notifications should not return a response"
    print("✓ Notification handling")


def test_handle_request_unknown_method():
    """Test handling of unknown method returns error."""
    server = MCPServer()
    request = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "unknown/method",
        "params": {}
    }

    response = server.handle_request(request)

    assert response is not None, "Response should not be None"
    assert response["jsonrpc"] == "2.0", "JSON-RPC version incorrect"
    assert response["id"] == 4, "Request ID mismatch"
    assert "error" in response, "Missing error"
    assert "Unknown method" in response["error"]["message"], "Error message incorrect"
    print("✓ Unknown method error")


def test_fork_detect_handler():
    """Test the fork-detect tool handler."""
    result = fork_detect_handler({"query": "implement authentication"})

    assert isinstance(result, str), "Result should be a string"
    assert "implement authentication" in result, "Query not in result"
    assert "Fork Detection" in result, "Missing title"
    assert "Placeholder" in result, "Missing placeholder notice"
    print("✓ Fork detect handler")


def test_fork_detect_handler_empty_query():
    """Test fork-detect handler with empty query."""
    result = fork_detect_handler({})

    assert isinstance(result, str), "Result should be a string"
    assert "Fork Detection" in result, "Missing title"
    print("✓ Fork detect handler (empty query)")


def test_create_server():
    """Test server creation and configuration."""
    server = create_server()

    assert isinstance(server, MCPServer), "Server type incorrect"
    assert "fork-detect" in server.tools, "fork-detect tool not registered"
    assert server.tools["fork-detect"]["name"] == "fork-detect", "Tool name incorrect"
    assert callable(server.tools["fork-detect"]["handler"]), "Handler not callable"
    print("✓ Server creation")


def test_protocol_compliance():
    """Test MCP protocol compliance."""
    server = MCPServer()

    # Test protocol version
    result = server.handle_initialize({})
    assert "protocolVersion" in result, "Missing protocol version"
    assert result["protocolVersion"] == "2024-11-05", "Protocol version incorrect"

    # Test capabilities
    assert "capabilities" in result, "Missing capabilities"
    assert "tools" in result["capabilities"], "Missing tools capability"

    # Test JSON-RPC version
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }
    response = server.handle_request(request)
    assert response["jsonrpc"] == "2.0", "JSON-RPC version incorrect"

    # Test error format
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "unknown",
        "params": {}
    }
    response = server.handle_request(request)
    assert "error" in response, "Missing error"
    assert "code" in response["error"], "Missing error code"
    assert "message" in response["error"], "Missing error message"
    assert response["error"]["code"] == -32603, "Error code incorrect"

    print("✓ Protocol compliance")


def main():
    """Run all tests."""
    print("Running MCP Server Tests")
    print("=" * 50)

    tests = [
        test_server_initialization,
        test_register_tool,
        test_handle_initialize,
        test_handle_tools_list_empty,
        test_handle_tools_list_with_tools,
        test_handle_tools_call,
        test_handle_tools_call_unknown_tool,
        test_handle_request_initialize,
        test_handle_request_tools_list,
        test_handle_request_tools_call,
        test_handle_request_notification,
        test_handle_request_unknown_method,
        test_fork_detect_handler,
        test_fork_detect_handler_empty_query,
        test_create_server,
        test_protocol_compliance,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: Unexpected error: {e}")
            failed += 1

    print("=" * 50)
    print(f"Tests passed: {passed}/{len(tests)}")
    print(f"Tests failed: {failed}/{len(tests)}")

    if failed == 0:
        print("\nAll tests passed!")
        return 0
    else:
        print(f"\n{failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
