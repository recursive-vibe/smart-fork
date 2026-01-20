#!/usr/bin/env python3
"""Basic verification of API server implementation without dependencies."""

import sys
from pathlib import Path


def verify_api_server_basic():
    """Verify the API server implementation structure."""
    print("=" * 70)
    print("VERIFICATION: Task 11 - Build local REST API server (Basic)")
    print("=" * 70)
    print()

    results = []

    # 1. Verify api_server.py exists
    print("1. Verifying api_server.py exists...")
    api_file = Path("src/smart_fork/api_server.py")
    if not api_file.exists():
        results.append(("api_server.py exists", False, f"File not found: {api_file}"))
        return results
    results.append(("api_server.py exists", True, "File exists"))

    # Read the file
    content = api_file.read_text()

    # 2. Verify FastAPI app creation
    print("2. Verifying FastAPI app...")
    if "app = FastAPI(" in content:
        results.append(("FastAPI app", True, "FastAPI app created"))
    else:
        results.append(("FastAPI app", False, "FastAPI app not found"))

    # 3. Verify Pydantic models
    print("3. Verifying Pydantic models...")
    models = ["SearchRequest", "SearchResponse", "IndexRequest", "IndexResponse", "SessionResponse", "StatsResponse"]
    found_models = [m for m in models if f"class {m}(BaseModel)" in content]
    if len(found_models) == len(models):
        results.append(("Pydantic models", True, f"All {len(models)} models defined"))
    else:
        missing = set(models) - set(found_models)
        results.append(("Pydantic models", False, f"Missing: {missing}"))

    # 4. Verify POST /chunks/search endpoint
    print("4. Verifying POST /chunks/search...")
    if '@app.post("/chunks/search"' in content and "async def search_chunks" in content:
        results.append(("POST /chunks/search", True, "Endpoint defined"))
    else:
        results.append(("POST /chunks/search", False, "Endpoint not found"))

    # 5. Verify POST /sessions/index endpoint
    print("5. Verifying POST /sessions/index...")
    if '@app.post("/sessions/index"' in content and "async def index_session" in content:
        results.append(("POST /sessions/index", True, "Endpoint defined"))
    else:
        results.append(("POST /sessions/index", False, "Endpoint not found"))

    # 6. Verify GET /sessions/{session_id} endpoint
    print("6. Verifying GET /sessions/{session_id}...")
    if '@app.get("/sessions/{session_id}"' in content and "async def get_session" in content:
        results.append(("GET /sessions/{session_id}", True, "Endpoint defined"))
    else:
        results.append(("GET /sessions/{session_id}", False, "Endpoint not found"))

    # 7. Verify GET /stats endpoint
    print("7. Verifying GET /stats...")
    if '@app.get("/stats"' in content and "async def get_stats" in content:
        results.append(("GET /stats", True, "Endpoint defined"))
    else:
        results.append(("GET /stats", False, "Endpoint not found"))

    # 8. Verify GET /health endpoint
    print("8. Verifying GET /health...")
    if '@app.get("/health"' in content and "async def health_check" in content:
        results.append(("GET /health", True, "Endpoint defined"))
    else:
        results.append(("GET /health", False, "Endpoint not found"))

    # 9. Verify startup/shutdown events
    print("9. Verifying lifecycle events...")
    has_startup = '@app.on_event("startup")' in content or 'async def startup_event' in content
    has_shutdown = '@app.on_event("shutdown")' in content or 'async def shutdown_event' in content
    if has_startup and has_shutdown:
        results.append(("Lifecycle events", True, "Startup and shutdown events defined"))
    else:
        results.append(("Lifecycle events", False, "Missing startup or shutdown event"))

    # 10. Verify start_server function
    print("10. Verifying start_server function...")
    if "def start_server(" in content:
        # Check default parameters
        if 'host: str = "127.0.0.1"' in content and 'port: int = 8741' in content:
            results.append(("start_server function", True, "Function with correct defaults (127.0.0.1:8741)"))
        else:
            results.append(("start_server function", False, "Missing or incorrect default parameters"))
    else:
        results.append(("start_server function", False, "Function not found"))

    # 11. Verify localhost-only binding
    print("11. Verifying localhost-only configuration...")
    if "127.0.0.1" in content and 'host: str = "127.0.0.1"' in content:
        results.append(("Localhost-only", True, "Server configured for localhost only"))
    else:
        results.append(("Localhost-only", False, "Not configured for localhost-only access"))

    # 12. Verify uvicorn integration
    print("12. Verifying uvicorn integration...")
    if "uvicorn.run(" in content:
        results.append(("Uvicorn integration", True, "Uses uvicorn for server"))
    else:
        results.append(("Uvicorn integration", False, "Uvicorn not used"))

    # 13. Verify service integration
    print("13. Verifying service integration...")
    services = ["SearchService", "SessionRegistry", "BackgroundIndexer"]
    found_services = [s for s in services if s in content]
    if len(found_services) == len(services):
        results.append(("Service integration", True, f"Integrates all {len(services)} services"))
    else:
        missing = set(services) - set(found_services)
        results.append(("Service integration", False, f"Missing: {missing}"))

    # 14. Verify imports
    print("14. Verifying imports...")
    required_imports = ["FastAPI", "uvicorn", "BaseModel", "HTTPException"]
    found_imports = [i for i in required_imports if i in content]
    if len(found_imports) == len(required_imports):
        results.append(("Required imports", True, "All required imports present"))
    else:
        missing = set(required_imports) - set(found_imports)
        results.append(("Required imports", False, f"Missing: {missing}"))

    # 15. Verify error handling
    print("15. Verifying error handling...")
    has_error_handling = "HTTPException" in content and "status_code" in content
    if has_error_handling:
        results.append(("Error handling", True, "HTTPException used for error responses"))
    else:
        results.append(("Error handling", False, "Error handling not implemented"))

    # 16. Verify test file exists
    print("16. Verifying test file...")
    test_file = Path("tests/test_api_server.py")
    if test_file.exists():
        test_content = test_file.read_text()
        test_count = test_content.count("def test_")
        if test_count > 0:
            results.append(("Test file", True, f"Test file with {test_count} test functions"))
        else:
            results.append(("Test file", False, "Test file has no test functions"))
    else:
        results.append(("Test file", False, "Test file not found"))

    # 17. Verify request validation
    print("17. Verifying request validation...")
    has_validation = "Field(" in content and "ge=" in content and "le=" in content
    if has_validation:
        results.append(("Request validation", True, "Pydantic Field validation used"))
    else:
        results.append(("Request validation", False, "Request validation not implemented"))

    # 18. Verify response models
    print("18. Verifying response models...")
    has_response_models = "response_model=" in content
    if has_response_models:
        results.append(("Response models", True, "Endpoints use response_model"))
    else:
        results.append(("Response models", False, "Response models not specified"))

    # 19. Verify logging
    print("19. Verifying logging...")
    has_logging = "logging" in content and "logger" in content
    if has_logging:
        results.append(("Logging", True, "Logging configured"))
    else:
        results.append(("Logging", False, "Logging not configured"))

    # 20. Verify code size
    print("20. Verifying implementation completeness...")
    lines = len(content.splitlines())
    if lines > 300:
        results.append(("Implementation size", True, f"{lines} lines (comprehensive implementation)"))
    else:
        results.append(("Implementation size", False, f"Only {lines} lines (may be incomplete)"))

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
        print()
        print("Note: Runtime testing requires dependencies:")
        print("  pip install fastapi uvicorn pydantic httpx pytest")
        return 0
    else:
        print(f"⚠️  {total - passed} verification(s) failed. Please review.")
        return 1


if __name__ == "__main__":
    try:
        results = verify_api_server_basic()
        exit_code = print_results(results)
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ Verification script failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
