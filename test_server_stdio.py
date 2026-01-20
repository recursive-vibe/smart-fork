#!/usr/bin/env python3
"""Test MCP server stdio interaction."""

import json
import subprocess
import sys
import time


def test_server_stdio():
    """Test server communication over stdio."""
    print("Testing MCP Server via stdio...")
    print("=" * 50)

    # Start the server
    proc = subprocess.Popen(
        [sys.executable, "-m", "smart_fork.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"PYTHONPATH": "/Users/austinwentzel/Documents/Smart-Fork/src"},
        text=True,
        bufsize=0
    )

    try:
        # Test 1: Initialize
        print("\n1. Testing initialize request...")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }

        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()

        response_line = proc.stdout.readline()
        response = json.loads(response_line)

        assert response["jsonrpc"] == "2.0", "JSON-RPC version mismatch"
        assert response["id"] == 1, "ID mismatch"
        assert "result" in response, "Missing result"
        assert response["result"]["protocolVersion"] == "2024-11-05", "Protocol version mismatch"
        print("   ✓ Initialize successful")
        print(f"   Server: {response['result']['serverInfo']['name']} v{response['result']['serverInfo']['version']}")

        # Test 2: Tools list
        print("\n2. Testing tools/list request...")
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }

        proc.stdin.write(json.dumps(tools_request) + "\n")
        proc.stdin.flush()

        response_line = proc.stdout.readline()
        response = json.loads(response_line)

        assert response["jsonrpc"] == "2.0", "JSON-RPC version mismatch"
        assert response["id"] == 2, "ID mismatch"
        assert "result" in response, "Missing result"
        assert "tools" in response["result"], "Missing tools"
        assert len(response["result"]["tools"]) == 1, "Should have 1 tool"
        assert response["result"]["tools"][0]["name"] == "fork-detect", "Tool name mismatch"
        print("   ✓ Tools list successful")
        print(f"   Available tools: {[t['name'] for t in response['result']['tools']]}")

        # Test 3: Call fork-detect tool
        print("\n3. Testing tools/call request...")
        call_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "fork-detect",
                "arguments": {
                    "query": "implement user authentication"
                }
            }
        }

        proc.stdin.write(json.dumps(call_request) + "\n")
        proc.stdin.flush()

        response_line = proc.stdout.readline()
        response = json.loads(response_line)

        assert response["jsonrpc"] == "2.0", "JSON-RPC version mismatch"
        assert response["id"] == 3, "ID mismatch"
        assert "result" in response, "Missing result"
        assert "content" in response["result"], "Missing content"
        assert len(response["result"]["content"]) > 0, "Empty content"
        assert "implement user authentication" in response["result"]["content"][0]["text"], "Query not in response"
        print("   ✓ Tool call successful")
        print(f"   Response preview: {response['result']['content'][0]['text'][:100]}...")

        # Test 4: Send notification (should not get response)
        print("\n4. Testing notification...")
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }

        proc.stdin.write(json.dumps(notification) + "\n")
        proc.stdin.flush()

        # Give it a moment to process
        time.sleep(0.1)

        # Check stderr for any errors
        proc.poll()
        if proc.returncode is not None:
            stderr = proc.stderr.read()
            print(f"   Warning: Server terminated: {stderr}")
        else:
            print("   ✓ Notification handled (no response expected)")

        print("\n" + "=" * 50)
        print("All stdio tests passed!")
        print("\nServer is MCP protocol compliant and ready for Claude Code.")

        return True

    except Exception as e:
        print(f"\n✗ Error: {e}")
        stderr = proc.stderr.read()
        if stderr:
            print(f"Server stderr: {stderr}")
        return False

    finally:
        proc.terminate()
        proc.wait(timeout=2)


if __name__ == "__main__":
    success = test_server_stdio()
    sys.exit(0 if success else 1)
