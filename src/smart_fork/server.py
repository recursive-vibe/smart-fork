"""Main MCP server entry point for Smart Fork."""

import json
import sys
from typing import Any, Dict, List, Optional


class MCPServer:
    """Basic MCP server implementing JSON-RPC 2.0 over stdio."""

    def __init__(self) -> None:
        """Initialize the MCP server."""
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.server_info = {
            "name": "smart-fork",
            "version": "0.1.0"
        }

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Any
    ) -> None:
        """Register a tool with the MCP server."""
        self.tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema,
            "handler": handler
        }

    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": self.server_info
        }

    def handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools_list = [
            {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": tool["inputSchema"]
            }
            for tool in self.tools.values()
        ]
        return {"tools": tools_list}

    def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        handler = self.tools[tool_name]["handler"]
        result = handler(arguments)

        return {
            "content": [
                {
                    "type": "text",
                    "text": result
                }
            ]
        }

    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a JSON-RPC request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "initialize":
                result = self.handle_initialize(params)
            elif method == "tools/list":
                result = self.handle_tools_list(params)
            elif method == "tools/call":
                result = self.handle_tools_call(params)
            elif method == "notifications/initialized":
                # Notification, no response needed
                return None
            else:
                raise ValueError(f"Unknown method: {method}")

            if request_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            return None

        except Exception as e:
            if request_id is not None:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
            return None

    def run(self) -> None:
        """Run the MCP server on stdio."""
        # Write server started message to stderr for debugging
        print("Smart Fork MCP Server started", file=sys.stderr)
        print(f"Server info: {self.server_info}", file=sys.stderr)
        print(f"Registered tools: {list(self.tools.keys())}", file=sys.stderr)

        # Process requests from stdin
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
                response = self.handle_request(request)

                if response is not None:
                    print(json.dumps(response), flush=True)

            except json.JSONDecodeError as e:
                print(f"Invalid JSON: {e}", file=sys.stderr)
            except Exception as e:
                print(f"Error handling request: {e}", file=sys.stderr)


def fork_detect_handler(arguments: Dict[str, Any]) -> str:
    """Placeholder handler for /fork-detect tool."""
    query = arguments.get("query", "")

    return f"""Fork Detection (Placeholder)

Your query: {query}

This is a placeholder response. The full implementation will:
1. Search vector database for relevant sessions
2. Calculate composite scores
3. Return top 5 ranked sessions with metadata

Status: MCP server is running correctly, but search features are not yet implemented.
"""


def create_server() -> MCPServer:
    """Create and configure the MCP server."""
    server = MCPServer()

    # Register /fork-detect tool
    server.register_tool(
        name="fork-detect",
        description="Search for relevant past Claude Code sessions to fork from",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language description of what you want to do"
                }
            },
            "required": ["query"]
        },
        handler=fork_detect_handler
    )

    return server


def main() -> None:
    """Main entry point for the Smart Fork MCP server."""
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
