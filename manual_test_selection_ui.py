#!/usr/bin/env python3
"""
Manual test script for SelectionUI.

Run this script to manually verify the selection UI implementation.
"""

from datetime import datetime
from dataclasses import dataclass

from src.smart_fork.selection_ui import SelectionUI, SelectionOption
from src.smart_fork.search_service import SessionSearchResult
from src.smart_fork.scoring_service import SessionScore


@dataclass
class MockSessionMetadata:
    """Mock session metadata for testing."""
    project: str
    created_at: str
    message_count: int
    chunk_count: int
    tags: list


def create_mock_result(
    session_id: str,
    score: float,
    project: str = "test-project",
    preview: str = "Test preview content"
) -> SessionSearchResult:
    """Create a mock search result for testing."""
    session_score = SessionScore(
        final_score=score,
        best_similarity=score * 0.4,
        avg_similarity=score * 0.2,
        chunk_ratio=score * 0.05,
        recency_score=score * 0.25,
        chain_quality=0.5,
        memory_boost=0.05
    )

    metadata = MockSessionMetadata(
        project=project,
        created_at="2026-01-20T15:30:00Z",
        message_count=50,
        chunk_count=10,
        tags=["authentication", "api"]
    )

    return SessionSearchResult(
        session_id=session_id,
        score=session_score,
        metadata=metadata,
        preview=preview,
        matched_chunks=[]
    )


def test_group_1_basic_initialization():
    """Test Group 1: Basic initialization."""
    print("\n" + "=" * 80)
    print("TEST GROUP 1: Basic Initialization")
    print("=" * 80)

    try:
        ui = SelectionUI()
        print("✓ SelectionUI initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to initialize SelectionUI: {e}")
        return False


def test_group_2_date_formatting():
    """Test Group 2: Date formatting."""
    print("\n" + "=" * 80)
    print("TEST GROUP 2: Date Formatting")
    print("=" * 80)

    ui = SelectionUI()
    tests_passed = 0
    tests_total = 3

    # Test ISO format
    try:
        date_str = "2026-01-20T15:30:00Z"
        formatted = ui.format_date(date_str)
        assert "2026-01-20" in formatted
        print(f"✓ ISO format: {date_str} -> {formatted}")
        tests_passed += 1
    except Exception as e:
        print(f"✗ ISO format failed: {e}")

    # Test alternative format
    try:
        date_str = "2026-01-20T15:30:00+00:00"
        formatted = ui.format_date(date_str)
        assert "2026-01-20" in formatted
        print(f"✓ Alternative format: {date_str} -> {formatted}")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Alternative format failed: {e}")

    # Test invalid format
    try:
        date_str = "invalid-date"
        formatted = ui.format_date(date_str)
        assert formatted == "invalid-date"
        print(f"✓ Invalid format handled: {date_str} -> {formatted}")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Invalid format failed: {e}")

    print(f"\nPassed: {tests_passed}/{tests_total}")
    return tests_passed == tests_total


def test_group_3_preview_truncation():
    """Test Group 3: Preview truncation."""
    print("\n" + "=" * 80)
    print("TEST GROUP 3: Preview Truncation")
    print("=" * 80)

    ui = SelectionUI()
    tests_passed = 0
    tests_total = 3

    # Test short preview (no truncation)
    try:
        preview = "Short preview"
        truncated = ui.truncate_preview(preview, max_length=150)
        assert truncated == preview
        print(f"✓ Short preview not truncated: '{preview}'")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Short preview failed: {e}")

    # Test long preview (truncation)
    try:
        preview = "A" * 200
        truncated = ui.truncate_preview(preview, max_length=150)
        assert len(truncated) <= 153  # 150 + "..."
        assert truncated.endswith("...")
        print(f"✓ Long preview truncated: {len(preview)} chars -> {len(truncated)} chars")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Long preview failed: {e}")

    # Test word boundary truncation
    try:
        preview = "word1 word2 word3 " + "A" * 200
        truncated = ui.truncate_preview(preview, max_length=20)
        assert truncated.endswith("...")
        print(f"✓ Word boundary truncation: '{preview[:30]}...' -> '{truncated}'")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Word boundary truncation failed: {e}")

    print(f"\nPassed: {tests_passed}/{tests_total}")
    return tests_passed == tests_total


def test_group_4_create_options_with_results():
    """Test Group 4: Create options with results."""
    print("\n" + "=" * 80)
    print("TEST GROUP 4: Create Options with Results")
    print("=" * 80)

    ui = SelectionUI()
    results = [
        create_mock_result("abc123def456", 0.92, "smart-fork", "Implementing session parser for JSONL files with UTF-8 support"),
        create_mock_result("def456ghi789", 0.85, "api-server", "Building REST API endpoints with FastAPI and error handling"),
        create_mock_result("ghi789jkl012", 0.78, "database", "Creating ChromaDB wrapper for vector storage and retrieval"),
    ]
    query = "search for sessions related to parsing files"

    tests_passed = 0
    tests_total = 8

    try:
        options = ui.create_options(results, query)

        # Test 1: Exactly 5 options
        if len(options) == 5:
            print(f"✓ Created exactly 5 options")
            tests_passed += 1
        else:
            print(f"✗ Expected 5 options, got {len(options)}")

        # Test 2: First 3 are results
        if (options[0].session_id == "abc123def456" and
            options[1].session_id == "def456ghi789" and
            options[2].session_id == "ghi789jkl012"):
            print(f"✓ First 3 options are search results")
            tests_passed += 1
        else:
            print(f"✗ First 3 options are not correct search results")

        # Test 3: First is recommended
        if options[0].is_recommended:
            print(f"✓ First result marked as recommended")
            tests_passed += 1
        else:
            print(f"✗ First result not marked as recommended")

        # Test 4: Others not recommended
        if not options[1].is_recommended and not options[2].is_recommended:
            print(f"✓ Other results not marked as recommended")
            tests_passed += 1
        else:
            print(f"✗ Other results incorrectly marked as recommended")

        # Test 5: 'None' option present
        none_option = [opt for opt in options if opt.id == "none"]
        if none_option:
            print(f"✓ 'None' option present: {none_option[0].label}")
            tests_passed += 1
        else:
            print(f"✗ 'None' option not found")

        # Test 6: 'Refine' option present
        refine_option = [opt for opt in options if opt.id == "refine"]
        if refine_option:
            print(f"✓ 'Refine' option present: {refine_option[0].label}")
            tests_passed += 1
        else:
            print(f"✗ 'Refine' option not found")

        # Test 7: Labels contain markers
        if "⭐" in options[0].label and "RECOMMENDED" in options[0].label:
            print(f"✓ Recommended label has markers: {options[0].label[:50]}...")
            tests_passed += 1
        else:
            print(f"✗ Recommended label missing markers")

        # Test 8: Scores are shown
        if "92%" in options[0].label or "85%" in options[1].label:
            print(f"✓ Scores shown in labels")
            tests_passed += 1
        else:
            print(f"✗ Scores not shown in labels")

    except Exception as e:
        print(f"✗ Exception during option creation: {e}")

    print(f"\nPassed: {tests_passed}/{tests_total}")
    return tests_passed == tests_total


def test_group_5_create_options_no_results():
    """Test Group 5: Create options with no results."""
    print("\n" + "=" * 80)
    print("TEST GROUP 5: Create Options with No Results")
    print("=" * 80)

    ui = SelectionUI()
    results = []
    query = "search for nonexistent sessions"

    tests_passed = 0
    tests_total = 3

    try:
        options = ui.create_options(results, query)

        # Test 1: Still has 5 options
        if len(options) == 5:
            print(f"✓ Created 5 options even with no results")
            tests_passed += 1
        else:
            print(f"✗ Expected 5 options, got {len(options)}")

        # Test 2: 'None' option present
        none_option = [opt for opt in options if opt.id == "none"]
        if none_option:
            print(f"✓ 'None' option present")
            tests_passed += 1
        else:
            print(f"✗ 'None' option not found")

        # Test 3: 'Refine' option present
        refine_option = [opt for opt in options if opt.id == "refine"]
        if refine_option:
            print(f"✓ 'Refine' option present")
            tests_passed += 1
        else:
            print(f"✗ 'Refine' option not found")

    except Exception as e:
        print(f"✗ Exception during option creation: {e}")

    print(f"\nPassed: {tests_passed}/{tests_total}")
    return tests_passed == tests_total


def test_group_6_format_selection_prompt():
    """Test Group 6: Format selection prompt."""
    print("\n" + "=" * 80)
    print("TEST GROUP 6: Format Selection Prompt")
    print("=" * 80)

    ui = SelectionUI()
    results = [
        create_mock_result("abc123", 0.9),
        create_mock_result("def456", 0.8),
    ]
    query = "test query"

    tests_passed = 0
    tests_total = 6

    try:
        options = ui.create_options(results, query)
        prompt = ui.format_selection_prompt(options, query)

        # Test 1: Contains title
        if "Fork Detection - Select a Session" in prompt:
            print(f"✓ Prompt contains title")
            tests_passed += 1
        else:
            print(f"✗ Prompt missing title")

        # Test 2: Contains query
        if query in prompt:
            print(f"✓ Prompt contains query")
            tests_passed += 1
        else:
            print(f"✗ Prompt missing query")

        # Test 3: Contains session IDs
        if "abc123" in prompt and "def456" in prompt:
            print(f"✓ Prompt contains session IDs")
            tests_passed += 1
        else:
            print(f"✗ Prompt missing session IDs")

        # Test 4: Contains options
        if "None of these - start fresh" in prompt and "Type something else" in prompt:
            print(f"✓ Prompt contains standard options")
            tests_passed += 1
        else:
            print(f"✗ Prompt missing standard options")

        # Test 5: Contains keyboard shortcuts
        if "Keyboard shortcuts" in prompt:
            print(f"✓ Prompt contains keyboard shortcuts")
            tests_passed += 1
        else:
            print(f"✗ Prompt missing keyboard shortcuts")

        # Test 6: Contains tip
        if "chat" in prompt.lower():
            print(f"✓ Prompt contains chat tip")
            tests_passed += 1
        else:
            print(f"✗ Prompt missing chat tip")

        print(f"\n--- PROMPT PREVIEW ---")
        print(prompt[:500] + "...\n")

    except Exception as e:
        print(f"✗ Exception during prompt formatting: {e}")

    print(f"\nPassed: {tests_passed}/{tests_total}")
    return tests_passed == tests_total


def test_group_7_format_chat_option():
    """Test Group 7: Format chat option."""
    print("\n" + "=" * 80)
    print("TEST GROUP 7: Format Chat Option")
    print("=" * 80)

    ui = SelectionUI()
    result = create_mock_result(
        "abc123def456",
        0.92,
        "smart-fork",
        "This is a preview of the session content showing what was discussed."
    )

    tests_passed = 0
    tests_total = 5

    try:
        chat_prompt = ui.format_chat_option(result)

        # Test 1: Contains session ID
        if "abc123def456" in chat_prompt:
            print(f"✓ Chat prompt contains session ID")
            tests_passed += 1
        else:
            print(f"✗ Chat prompt missing session ID")

        # Test 2: Contains project
        if "smart-fork" in chat_prompt:
            print(f"✓ Chat prompt contains project")
            tests_passed += 1
        else:
            print(f"✗ Chat prompt missing project")

        # Test 3: Contains score breakdown
        if "Score Breakdown" in chat_prompt:
            print(f"✓ Chat prompt contains score breakdown")
            tests_passed += 1
        else:
            print(f"✗ Chat prompt missing score breakdown")

        # Test 4: Contains preview
        if "Preview:" in chat_prompt and result.preview in chat_prompt:
            print(f"✓ Chat prompt contains preview")
            tests_passed += 1
        else:
            print(f"✗ Chat prompt missing preview")

        # Test 5: Contains call to action
        if "What would you like to know" in chat_prompt:
            print(f"✓ Chat prompt contains call to action")
            tests_passed += 1
        else:
            print(f"✗ Chat prompt missing call to action")

        print(f"\n--- CHAT PROMPT PREVIEW ---")
        print(chat_prompt[:400] + "...\n")

    except Exception as e:
        print(f"✗ Exception during chat option formatting: {e}")

    print(f"\nPassed: {tests_passed}/{tests_total}")
    return tests_passed == tests_total


def test_group_8_display_selection():
    """Test Group 8: Display selection."""
    print("\n" + "=" * 80)
    print("TEST GROUP 8: Display Selection")
    print("=" * 80)

    ui = SelectionUI()
    results = [
        create_mock_result("abc123", 0.9),
        create_mock_result("def456", 0.8),
    ]
    query = "test query"

    tests_passed = 0
    tests_total = 6

    try:
        display_data = ui.display_selection(results, query)

        # Test 1: Contains prompt
        if 'prompt' in display_data and display_data['prompt']:
            print(f"✓ Display data contains prompt")
            tests_passed += 1
        else:
            print(f"✗ Display data missing prompt")

        # Test 2: Contains options
        if 'options' in display_data and len(display_data['options']) == 5:
            print(f"✓ Display data contains 5 options")
            tests_passed += 1
        else:
            print(f"✗ Display data missing or wrong number of options")

        # Test 3: Contains query
        if 'query' in display_data and display_data['query'] == query:
            print(f"✓ Display data contains query")
            tests_passed += 1
        else:
            print(f"✗ Display data missing query")

        # Test 4: Contains num_results
        if 'num_results' in display_data and display_data['num_results'] == 2:
            print(f"✓ Display data contains correct num_results")
            tests_passed += 1
        else:
            print(f"✗ Display data missing or wrong num_results")

        # Test 5: Options have required fields
        option = display_data['options'][0]
        required_fields = ['id', 'label', 'description', 'session_id', 'is_recommended']
        if all(field in option for field in required_fields):
            print(f"✓ Options have all required fields")
            tests_passed += 1
        else:
            print(f"✗ Options missing required fields")

        # Test 6: First option is recommended
        if display_data['options'][0]['is_recommended']:
            print(f"✓ First option is marked as recommended")
            tests_passed += 1
        else:
            print(f"✗ First option not marked as recommended")

    except Exception as e:
        print(f"✗ Exception during display selection: {e}")

    print(f"\nPassed: {tests_passed}/{tests_total}")
    return tests_passed == tests_total


def test_group_9_handle_selection():
    """Test Group 9: Handle selection."""
    print("\n" + "=" * 80)
    print("TEST GROUP 9: Handle Selection")
    print("=" * 80)

    ui = SelectionUI()
    results = [
        create_mock_result("abc123", 0.9),
    ]
    query = "test query"
    options = ui.create_options(results, query)

    tests_passed = 0
    tests_total = 4

    # Test 1: Select session
    try:
        result = ui.handle_selection("result_0", options)
        if (result['status'] == 'selected' and
            result['action'] == 'fork' and
            result['session_id'] == 'abc123'):
            print(f"✓ Session selection handled correctly")
            tests_passed += 1
        else:
            print(f"✗ Session selection handled incorrectly: {result}")
    except Exception as e:
        print(f"✗ Session selection failed: {e}")

    # Test 2: Select none
    try:
        result = ui.handle_selection("none", options)
        if result['status'] == 'selected' and result['action'] == 'start_fresh':
            print(f"✓ 'None' selection handled correctly")
            tests_passed += 1
        else:
            print(f"✗ 'None' selection handled incorrectly: {result}")
    except Exception as e:
        print(f"✗ 'None' selection failed: {e}")

    # Test 3: Select refine
    try:
        result = ui.handle_selection("refine", options)
        if result['status'] == 'selected' and result['action'] == 'refine':
            print(f"✓ 'Refine' selection handled correctly")
            tests_passed += 1
        else:
            print(f"✗ 'Refine' selection handled incorrectly: {result}")
    except Exception as e:
        print(f"✗ 'Refine' selection failed: {e}")

    # Test 4: Invalid selection
    try:
        result = ui.handle_selection("invalid_id", options)
        if result['status'] == 'error':
            print(f"✓ Invalid selection handled correctly")
            tests_passed += 1
        else:
            print(f"✗ Invalid selection handled incorrectly: {result}")
    except Exception as e:
        print(f"✗ Invalid selection failed: {e}")

    print(f"\nPassed: {tests_passed}/{tests_total}")
    return tests_passed == tests_total


def test_group_10_end_to_end_flow():
    """Test Group 10: End-to-end selection flow."""
    print("\n" + "=" * 80)
    print("TEST GROUP 10: End-to-End Selection Flow")
    print("=" * 80)

    ui = SelectionUI()
    results = [
        create_mock_result("session_abc123", 0.92, "smart-fork-project", "Implementing session parser for JSONL files"),
        create_mock_result("session_def456", 0.85, "api-server-project", "Building REST API with FastAPI"),
        create_mock_result("session_ghi789", 0.78, "database-project", "Creating ChromaDB wrapper"),
    ]
    query = "find sessions about parsing and file handling"

    tests_passed = 0
    tests_total = 5

    try:
        # Step 1: Display selection
        display_data = ui.display_selection(results, query)
        if display_data and 'prompt' in display_data:
            print(f"✓ Step 1: Display selection successful")
            tests_passed += 1
        else:
            print(f"✗ Step 1: Display selection failed")

        # Step 2: Get options
        options = ui.create_options(results, query)
        if len(options) == 5:
            print(f"✓ Step 2: Created 5 options")
            tests_passed += 1
        else:
            print(f"✗ Step 2: Wrong number of options")

        # Step 3: Select first result
        selection_result = ui.handle_selection("result_0", options)
        if (selection_result['status'] == 'selected' and
            selection_result['session_id'] == 'session_abc123'):
            print(f"✓ Step 3: Selected first result successfully")
            tests_passed += 1
        else:
            print(f"✗ Step 3: Selection failed")

        # Step 4: Chat about result
        chat_prompt = ui.format_chat_option(results[0])
        if "session_abc123" in chat_prompt and "smart-fork-project" in chat_prompt:
            print(f"✓ Step 4: Chat option formatted successfully")
            tests_passed += 1
        else:
            print(f"✗ Step 4: Chat option formatting failed")

        # Step 5: Full flow simulation
        print(f"\n--- FULL FLOW SIMULATION ---")
        print(f"Query: {query}")
        print(f"Results found: {len(results)}")
        print(f"Top result: {results[0].session_id} ({int(results[0].score.final_score * 100)}%)")
        print(f"Options created: {len(options)}")
        print(f"Selection handled: {selection_result['action']} for {selection_result['session_id']}")
        print(f"✓ Step 5: Full flow completed")
        tests_passed += 1

    except Exception as e:
        print(f"✗ End-to-end flow failed: {e}")
        import traceback
        traceback.print_exc()

    print(f"\nPassed: {tests_passed}/{tests_total}")
    return tests_passed == tests_total


def main():
    """Run all test groups."""
    print("\n" + "=" * 80)
    print("MANUAL TEST SCRIPT FOR SELECTION UI")
    print("=" * 80)

    test_groups = [
        ("Basic Initialization", test_group_1_basic_initialization),
        ("Date Formatting", test_group_2_date_formatting),
        ("Preview Truncation", test_group_3_preview_truncation),
        ("Create Options with Results", test_group_4_create_options_with_results),
        ("Create Options with No Results", test_group_5_create_options_no_results),
        ("Format Selection Prompt", test_group_6_format_selection_prompt),
        ("Format Chat Option", test_group_7_format_chat_option),
        ("Display Selection", test_group_8_display_selection),
        ("Handle Selection", test_group_9_handle_selection),
        ("End-to-End Selection Flow", test_group_10_end_to_end_flow),
    ]

    results = []
    for name, test_func in test_groups:
        passed = test_func()
        results.append((name, passed))

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed_count}/{total_count} test groups passed")

    if passed_count == total_count:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test group(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
