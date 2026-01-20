"""Tests for MCP server boilerplate."""

import json
from io import StringIO
from typing import Any, Dict
from unittest.mock import patch

import pytest

from smart_fork.server import MCPServer, create_server, fork_detect_handler


class TestMCPServer:
    """Test cases for the MCP server."""

    def test_server_initialization(self) -> None:
        """Test that server initializes correctly."""
        server = MCPServer()
        assert server.server_info["name"] == "smart-fork"
        assert server.server_info["version"] == "0.1.0"
        assert len(server.tools) == 0

    def test_register_tool(self) -> None:
        """Test tool registration."""
        server = MCPServer()

        def dummy_handler(args: Dict[str, Any]) -> str:
            return "test"

        server.register_tool(
            name="test-tool",
            description="A test tool",
            input_schema={"type": "object"},
            handler=dummy_handler
        )

        assert "test-tool" in server.tools
        assert server.tools["test-tool"]["name"] == "test-tool"
        assert server.tools["test-tool"]["description"] == "A test tool"

    def test_handle_initialize(self) -> None:
        """Test initialize request handling."""
        server = MCPServer()
        result = server.handle_initialize({})

        assert result["protocolVersion"] == "2024-11-05"
        assert "capabilities" in result
        assert "serverInfo" in result
        assert result["serverInfo"]["name"] == "smart-fork"

    def test_handle_tools_list_empty(self) -> None:
        """Test tools/list with no tools registered."""
        server = MCPServer()
        result = server.handle_tools_list({})

        assert "tools" in result
        assert result["tools"] == []

    def test_handle_tools_list_with_tools(self) -> None:
        """Test tools/list with registered tools."""
        server = create_server()
        result = server.handle_tools_list({})

        assert "tools" in result
        assert len(result["tools"]) == 1
        assert result["tools"][0]["name"] == "fork-detect"
        assert "description" in result["tools"][0]
        assert "inputSchema" in result["tools"][0]

    def test_handle_tools_call(self) -> None:
        """Test tools/call request handling."""
        server = create_server()

        result = server.handle_tools_call({
            "name": "fork-detect",
            "arguments": {"query": "test query"}
        })

        assert "content" in result
        assert len(result["content"]) > 0
        assert result["content"][0]["type"] == "text"
        assert "test query" in result["content"][0]["text"]

    def test_handle_tools_call_unknown_tool(self) -> None:
        """Test tools/call with unknown tool raises error."""
        server = MCPServer()

        with pytest.raises(ValueError, match="Unknown tool"):
            server.handle_tools_call({
                "name": "unknown-tool",
                "arguments": {}
            })

    def test_handle_request_initialize(self) -> None:
        """Test full request handling for initialize."""
        server = MCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }

        response = server.handle_request(request)

        assert response is not None
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["serverInfo"]["name"] == "smart-fork"

    def test_handle_request_tools_list(self) -> None:
        """Test full request handling for tools/list."""
        server = create_server()
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }

        response = server.handle_request(request)

        assert response is not None
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "result" in response
        assert "tools" in response["result"]

    def test_handle_request_tools_call(self) -> None:
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

        assert response is not None
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 3
        assert "result" in response
        assert "content" in response["result"]

    def test_handle_request_notification(self) -> None:
        """Test handling of notifications (no response expected)."""
        server = MCPServer()
        request = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }

        response = server.handle_request(request)

        assert response is None

    def test_handle_request_unknown_method(self) -> None:
        """Test handling of unknown method returns error."""
        server = MCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "unknown/method",
            "params": {}
        }

        response = server.handle_request(request)

        assert response is not None
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 4
        assert "error" in response
        assert "Unknown method" in response["error"]["message"]

    def test_fork_detect_handler(self) -> None:
        """Test the fork-detect tool handler."""
        result = fork_detect_handler({"query": "implement authentication"})

        assert isinstance(result, str)
        assert "implement authentication" in result
        assert "Fork Detection" in result
        assert "Placeholder" in result

    def test_fork_detect_handler_empty_query(self) -> None:
        """Test fork-detect handler with empty query."""
        result = fork_detect_handler({})

        assert isinstance(result, str)
        assert "Fork Detection" in result

    def test_create_server(self) -> None:
        """Test server creation and configuration."""
        server = create_server()

        assert isinstance(server, MCPServer)
        assert "fork-detect" in server.tools
        assert server.tools["fork-detect"]["name"] == "fork-detect"
        assert callable(server.tools["fork-detect"]["handler"])


class TestMCPProtocol:
    """Test MCP protocol compliance."""

    def test_protocol_version(self) -> None:
        """Test that server reports correct protocol version."""
        server = MCPServer()
        result = server.handle_initialize({})
        assert "protocolVersion" in result
        assert result["protocolVersion"] == "2024-11-05"

    def test_server_capabilities(self) -> None:
        """Test that server reports its capabilities."""
        server = MCPServer()
        result = server.handle_initialize({})
        assert "capabilities" in result
        assert "tools" in result["capabilities"]

    def test_jsonrpc_version(self) -> None:
        """Test that responses include correct JSON-RPC version."""
        server = MCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }

        response = server.handle_request(request)
        assert response is not None
        assert response["jsonrpc"] == "2.0"

    def test_error_response_format(self) -> None:
        """Test that error responses follow JSON-RPC format."""
        server = MCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "unknown",
            "params": {}
        }

        response = server.handle_request(request)
        assert response is not None
        assert "error" in response
        assert "code" in response["error"]
        assert "message" in response["error"]
        assert response["error"]["code"] == -32603
