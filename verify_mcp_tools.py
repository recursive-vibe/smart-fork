#!/usr/bin/env python3
"""
Verification script for MCP server tool registration (Phase 2, Task 2).

This script tests:
1. MCP server initializes correctly
2. fork-detect tool is properly registered
3. Tool list request returns expected format
4. Tool invocation works correctly
5. Tool schema matches MCP specification
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from smart_fork.server import create_server, MCPServer


def test_server_initialization():
    """Test that MCP server initializes without errors."""
    print("\n1. Testing server initialization...")
    try:
        server = create_server()
        print("   ✓ Server created successfully")
        print(f"   ✓ Server name: {server.server_info['name']}")
        print(f"   ✓ Server version: {server.server_info['version']}")
        return True
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False


def test_tool_registration():
    """Test that fork-detect tool is registered."""
    print("\n2. Testing tool registration...")
    try:
        server = create_server()

        if "fork-detect" not in server.tools:
            print("   ✗ fork-detect tool not registered")
            return False

        tool = server.tools["fork-detect"]
        print("   ✓ fork-detect tool is registered")
        print(f"   ✓ Tool name: {tool['name']}")
        print(f"   ✓ Tool description: {tool['description']}")
        print(f"   ✓ Handler callable: {callable(tool['handler'])}")

        return True
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False


def test_tool_list_request():
    """Test that tools/list request returns correct format."""
    print("\n3. Testing tools/list request...")
    try:
        server = create_server()

        # Simulate MCP tools/list request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }

        response = server.handle_request(request)

        if response is None:
            print("   ✗ No response returned")
            return False

        if "error" in response:
            print(f"   ✗ Error response: {response['error']}")
            return False

        result = response.get("result", {})
        tools = result.get("tools", [])

        if len(tools) == 0:
            print("   ✗ No tools in response")
            return False

        print(f"   ✓ Response format valid")
        print(f"   ✓ Number of tools: {len(tools)}")

        # Check fork-detect tool in list
        fork_detect_tool = next((t for t in tools if t["name"] == "fork-detect"), None)

        if fork_detect_tool is None:
            print("   ✗ fork-detect not in tool list")
            return False

        print("   ✓ fork-detect present in tool list")
        print(f"   ✓ Description: {fork_detect_tool['description']}")

        # Check schema
        schema = fork_detect_tool.get("inputSchema", {})
        if "properties" not in schema:
            print("   ✗ Missing properties in inputSchema")
            return False

        if "query" not in schema["properties"]:
            print("   ✗ Missing 'query' property in inputSchema")
            return False

        print("   ✓ Input schema valid")
        print(f"   ✓ Required fields: {schema.get('required', [])}")

        return True

    except Exception as e:
        print(f"   ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tool_invocation():
    """Test that fork-detect tool can be invoked."""
    print("\n4. Testing tool invocation...")
    try:
        server = create_server()

        # Simulate MCP tools/call request
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "fork-detect",
                "arguments": {
                    "query": "test authentication implementation"
                }
            }
        }

        response = server.handle_request(request)

        if response is None:
            print("   ✗ No response returned")
            return False

        if "error" in response:
            print(f"   ✗ Error response: {response['error']}")
            return False

        result = response.get("result", {})
        content = result.get("content", [])

        if len(content) == 0:
            print("   ✗ No content in response")
            return False

        if content[0]["type"] != "text":
            print("   ✗ Content type is not 'text'")
            return False

        text = content[0]["text"]

        print("   ✓ Tool invocation successful")
        print("   ✓ Response format valid")
        print(f"   ✓ Response includes query: {'test authentication implementation' in text}")
        print(f"   ✓ Response length: {len(text)} characters")

        # Check that response contains expected elements
        if "Fork Detection" in text or "query" in text.lower():
            print("   ✓ Response contains expected content")
        else:
            print("   ⚠ Response content unexpected (but not an error)")

        return True

    except Exception as e:
        print(f"   ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handling():
    """Test error handling for invalid tool calls."""
    print("\n5. Testing error handling...")
    try:
        server = create_server()

        # Test 1: Unknown tool
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "unknown-tool",
                "arguments": {}
            }
        }

        response = server.handle_request(request)

        if response is None or "error" not in response:
            print("   ✗ Should return error for unknown tool")
            return False

        print("   ✓ Returns error for unknown tool")

        # Test 2: Missing query parameter
        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "fork-detect",
                "arguments": {}
            }
        }

        response = server.handle_request(request)

        # Should handle gracefully (query defaults to empty string)
        if response is None:
            print("   ✗ No response for missing query")
            return False

        if "error" in response:
            # This is acceptable - could error on missing required field
            print("   ✓ Errors on missing required query parameter")
        else:
            # Or could handle gracefully with error message in response
            result = response.get("result", {})
            content = result.get("content", [])
            if len(content) > 0:
                text = content[0]["text"]
                if "Error" in text or "provide a query" in text:
                    print("   ✓ Handles missing query gracefully with error message")
                else:
                    print("   ⚠ Response doesn't indicate error for missing query")

        return True

    except Exception as e:
        print(f"   ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mcp_spec_compliance():
    """Test compliance with MCP specification."""
    print("\n6. Testing MCP specification compliance...")
    try:
        server = create_server()

        # Test initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "initialize",
            "params": {}
        }

        response = server.handle_request(init_request)

        if response is None or "error" in response:
            print("   ✗ Initialize request failed")
            return False

        result = response.get("result", {})

        # Check required fields
        if "protocolVersion" not in result:
            print("   ✗ Missing protocolVersion in initialize response")
            return False

        if "capabilities" not in result:
            print("   ✗ Missing capabilities in initialize response")
            return False

        if "serverInfo" not in result:
            print("   ✗ Missing serverInfo in initialize response")
            return False

        print("   ✓ Initialize response has required fields")
        print(f"   ✓ Protocol version: {result['protocolVersion']}")
        print(f"   ✓ Server info: {result['serverInfo']}")

        # Check JSON-RPC format
        if response.get("jsonrpc") != "2.0":
            print("   ✗ Invalid JSON-RPC version")
            return False

        print("   ✓ JSON-RPC 2.0 format compliant")

        return True

    except Exception as e:
        print(f"   ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification tests."""
    print("=" * 70)
    print("MCP Server Tool Registration Verification")
    print("Phase 2, Task 2: Verify and fix MCP server tool registration")
    print("=" * 70)

    tests = [
        ("Server Initialization", test_server_initialization),
        ("Tool Registration", test_tool_registration),
        ("Tools List Request", test_tool_list_request),
        ("Tool Invocation", test_tool_invocation),
        ("Error Handling", test_error_handling),
        ("MCP Spec Compliance", test_mcp_spec_compliance),
    ]

    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    all_passed = all(result for _, result in results)

    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("\nMCP server tool registration is working correctly.")
        print("Tools are properly exposed and respond to requests.")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print("\nPlease review the failures above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
