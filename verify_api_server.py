#!/usr/bin/env python3
"""Verification script for REST API server implementation."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def verify_api_server():
    """Verify the API server implementation."""
    print("=" * 70)
    print("VERIFICATION: Task 11 - Build local REST API server")
    print("=" * 70)
    print()

    results = []

    # 1. Verify module structure
    print("1. Verifying module structure...")
    try:
        from smart_fork import api_server
        results.append(("Module import", True, "api_server module exists"))
    except ImportError as e:
        results.append(("Module import", False, f"Failed to import: {e}"))
        return results

    # 2. Verify FastAPI app exists
    print("2. Verifying FastAPI app...")
    try:
        assert hasattr(api_server, 'app'), "FastAPI app not found"
        from fastapi import FastAPI
        assert isinstance(api_server.app, FastAPI), "app is not a FastAPI instance"
        results.append(("FastAPI app", True, "FastAPI app created"))
    except Exception as e:
        results.append(("FastAPI app", False, str(e)))

    # 3. Verify Pydantic models
    print("3. Verifying Pydantic models...")
    try:
        from smart_fork.api_server import (
            SearchRequest, SearchResponse,
            IndexRequest, IndexResponse,
            SessionResponse, StatsResponse
        )
        results.append(("Pydantic models", True, "All request/response models defined"))
    except ImportError as e:
        results.append(("Pydantic models", False, f"Missing models: {e}"))

    # 4. Verify endpoints registered
    print("4. Verifying endpoints...")
    try:
        routes = [route.path for route in api_server.app.routes]

        required_endpoints = [
            "/chunks/search",
            "/sessions/index",
            "/sessions/{session_id}",
            "/stats",
            "/health"
        ]

        missing = [ep for ep in required_endpoints if ep not in routes]
        if missing:
            results.append(("Endpoints", False, f"Missing: {missing}"))
        else:
            results.append(("Endpoints", True, f"All {len(required_endpoints)} endpoints registered"))
    except Exception as e:
        results.append(("Endpoints", False, str(e)))

    # 5. Verify POST /chunks/search
    print("5. Verifying POST /chunks/search endpoint...")
    try:
        route = next((r for r in api_server.app.routes if r.path == "/chunks/search"), None)
        assert route is not None, "Endpoint not found"
        assert "POST" in route.methods, "POST method not registered"
        results.append(("POST /chunks/search", True, "Endpoint registered with POST method"))
    except Exception as e:
        results.append(("POST /chunks/search", False, str(e)))

    # 6. Verify POST /sessions/index
    print("6. Verifying POST /sessions/index endpoint...")
    try:
        route = next((r for r in api_server.app.routes if r.path == "/sessions/index"), None)
        assert route is not None, "Endpoint not found"
        assert "POST" in route.methods, "POST method not registered"
        results.append(("POST /sessions/index", True, "Endpoint registered with POST method"))
    except Exception as e:
        results.append(("POST /sessions/index", False, str(e)))

    # 7. Verify GET /sessions/{session_id}
    print("7. Verifying GET /sessions/{session_id} endpoint...")
    try:
        route = next((r for r in api_server.app.routes if r.path == "/sessions/{session_id}"), None)
        assert route is not None, "Endpoint not found"
        assert "GET" in route.methods, "GET method not registered"
        results.append(("GET /sessions/{session_id}", True, "Endpoint registered with GET method"))
    except Exception as e:
        results.append(("GET /sessions/{session_id}", False, str(e)))

    # 8. Verify GET /stats
    print("8. Verifying GET /stats endpoint...")
    try:
        route = next((r for r in api_server.app.routes if r.path == "/stats"), None)
        assert route is not None, "Endpoint not found"
        assert "GET" in route.methods, "GET method not registered"
        results.append(("GET /stats", True, "Endpoint registered with GET method"))
    except Exception as e:
        results.append(("GET /stats", False, str(e)))

    # 9. Verify GET /health
    print("9. Verifying GET /health endpoint...")
    try:
        route = next((r for r in api_server.app.routes if r.path == "/health"), None)
        assert route is not None, "Endpoint not found"
        assert "GET" in route.methods, "GET method not registered"
        results.append(("GET /health", True, "Endpoint registered with GET method"))
    except Exception as e:
        results.append(("GET /health", False, str(e)))

    # 10. Verify startup/shutdown events
    print("10. Verifying lifecycle events...")
    try:
        assert hasattr(api_server, 'startup_event'), "startup_event not defined"
        assert hasattr(api_server, 'shutdown_event'), "shutdown_event not defined"
        results.append(("Lifecycle events", True, "startup and shutdown events defined"))
    except Exception as e:
        results.append(("Lifecycle events", False, str(e)))

    # 11. Verify start_server function
    print("11. Verifying start_server function...")
    try:
        assert hasattr(api_server, 'start_server'), "start_server function not found"
        import inspect
        sig = inspect.signature(api_server.start_server)
        assert 'host' in sig.parameters, "Missing host parameter"
        assert 'port' in sig.parameters, "Missing port parameter"
        # Check default values
        assert sig.parameters['host'].default == "127.0.0.1", "Host should default to 127.0.0.1"
        assert sig.parameters['port'].default == 8741, "Port should default to 8741"
        results.append(("start_server function", True, "Function with correct signature (host=127.0.0.1, port=8741)"))
    except Exception as e:
        results.append(("start_server function", False, str(e)))

    # 12. Verify localhost-only binding
    print("12. Verifying localhost-only configuration...")
    try:
        import inspect
        source = inspect.getsource(api_server.start_server)
        assert "127.0.0.1" in source, "Should bind to 127.0.0.1 for localhost-only access"
        results.append(("Localhost-only", True, "Server configured to bind to 127.0.0.1 only"))
    except Exception as e:
        results.append(("Localhost-only", False, str(e)))

    # 13. Verify test file exists
    print("13. Verifying test file...")
    try:
        test_file = Path(__file__).parent / "tests" / "test_api_server.py"
        assert test_file.exists(), f"Test file not found: {test_file}"

        # Check test file has content
        content = test_file.read_text()
        assert len(content) > 1000, "Test file seems too small"
        assert "def test_" in content, "No test functions found"

        # Count test functions
        test_count = content.count("def test_")
        results.append(("Test file", True, f"Test file exists with {test_count} test functions"))
    except Exception as e:
        results.append(("Test file", False, str(e)))

    # 14. Verify SearchRequest validation
    print("14. Verifying SearchRequest validation...")
    try:
        from smart_fork.api_server import SearchRequest
        from pydantic import ValidationError

        # Test valid request
        req = SearchRequest(query="test")
        assert req.k_chunks == 200, "Default k_chunks should be 200"
        assert req.top_n_sessions == 5, "Default top_n_sessions should be 5"

        # Test boundaries
        try:
            SearchRequest(query="test", k_chunks=0)
            results.append(("SearchRequest validation", False, "Should reject k_chunks=0"))
        except:
            pass  # Expected

        try:
            SearchRequest(query="test", k_chunks=1001)
            results.append(("SearchRequest validation", False, "Should reject k_chunks>1000"))
        except:
            pass  # Expected

        results.append(("SearchRequest validation", True, "Request validation working (defaults and boundaries)"))
    except Exception as e:
        results.append(("SearchRequest validation", False, str(e)))

    # 15. Verify service integration
    print("15. Verifying service integration...")
    try:
        import inspect

        # Check startup_event initializes services
        startup_source = inspect.getsource(api_server.startup_event)
        assert "SessionRegistry" in startup_source, "Should initialize SessionRegistry"
        assert "SearchService" in startup_source, "Should initialize SearchService"
        assert "BackgroundIndexer" in startup_source, "Should initialize BackgroundIndexer"

        results.append(("Service integration", True, "All services initialized in startup event"))
    except Exception as e:
        results.append(("Service integration", False, str(e)))

    return results


def print_results(results):
    """Print verification results."""
    print()
    print("=" * 70)
    print("VERIFICATION RESULTS")
    print("=" * 70)
    print()

    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    for name, success, message in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8} | {name:30} | {message}")

    print()
    print("-" * 70)
    print(f"Total: {passed}/{total} verifications passed")
    print("-" * 70)
    print()

    if passed == total:
        print("🎉 All verifications passed! Task 11 implementation complete.")
        return 0
    else:
        print(f"⚠️  {total - passed} verification(s) failed. Please review.")
        return 1


if __name__ == "__main__":
    try:
        results = verify_api_server()
        exit_code = print_results(results)
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ Verification script failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
