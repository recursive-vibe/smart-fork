#!/usr/bin/env python3
"""
Verification script for Task 4: SelectionUI Integration with MCP Server Flow

This script verifies:
1. SelectionUI creates 5 options (top 3 + None + Type something)
2. Highest-scoring result is marked as 'Recommended'
3. Fork commands are included in the output for each result
4. MCP server properly formats and returns the selection UI with fork commands
5. User can copy-paste fork commands directly from the output
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from smart_fork.selection_ui import SelectionUI, SelectionOption
from smart_fork.fork_generator import ForkGenerator
from smart_fork.search_service import SessionSearchResult
from smart_fork.scoring_service import SessionScore
from smart_fork.session_registry import SessionMetadata
from smart_fork.server import format_search_results_with_selection


def create_mock_result(session_id: str, score: float, project: str = "test-project") -> SessionSearchResult:
    """Create a mock search result for testing."""
    session_score = SessionScore(
        session_id=session_id,
        final_score=score,
        best_similarity=score * 0.4,
        avg_similarity=score * 0.2,
        chunk_ratio=score * 0.05,
        recency_score=score * 0.25,
        chain_quality=0.5,
        memory_boost=0.0,
        num_chunks_matched=5
    )

    metadata = SessionMetadata(
        session_id=session_id,
        project=project,
        created_at="2026-01-20T15:30:00Z",
        last_synced="2026-01-20T15:30:00Z",
        message_count=50,
        chunk_count=10,
        tags=["tag1", "tag2"]
    )

    return SessionSearchResult(
        session_id=session_id,
        score=session_score,
        metadata=metadata,
        preview=f"This is a preview of session {session_id} with some content that demonstrates the search results.",
        matched_chunks=[]
    )


def verify_selection_ui_with_fork_commands():
    """Verify SelectionUI generates fork commands."""
    print("=" * 80)
    print("TEST 1: SelectionUI with ForkGenerator")
    print("=" * 80)

    fork_generator = ForkGenerator(claude_sessions_dir="~/.claude")
    selection_ui = SelectionUI(fork_generator=fork_generator)

    results = [
        create_mock_result("abc123def456", 0.94, "realtime-dashboard"),
        create_mock_result("ghi789jkl012", 0.87, "api-websockets"),
        create_mock_result("mno345pqr678", 0.81, "frontend-react"),
    ]
    query = "implement real-time dashboard updates with WebSocket"

    options = selection_ui.create_options(results, query)

    # Verify we have 5 options
    assert len(options) == 5, f"Expected 5 options, got {len(options)}"
    print("✓ Created exactly 5 options")

    # Verify first 3 are results
    assert options[0].session_id == "abc123def456"
    assert options[1].session_id == "ghi789jkl012"
    assert options[2].session_id == "mno345pqr678"
    print("✓ First 3 options are search results")

    # Verify highest is marked as recommended
    assert options[0].is_recommended is True
    assert options[1].is_recommended is False
    assert options[2].is_recommended is False
    print("✓ Highest-scoring result marked as 'Recommended'")

    # Verify fork commands are present
    assert options[0].fork_terminal_cmd is not None
    assert "claude --resume abc123def456" in options[0].fork_terminal_cmd
    assert options[0].fork_in_session_cmd is not None
    assert "/fork abc123def456" in options[0].fork_in_session_cmd
    print("✓ Fork commands generated for result 1")

    assert options[1].fork_terminal_cmd is not None
    assert "claude --resume ghi789jkl012" in options[1].fork_terminal_cmd
    print("✓ Fork commands generated for result 2")

    assert options[2].fork_terminal_cmd is not None
    assert "claude --resume mno345pqr678" in options[2].fork_terminal_cmd
    print("✓ Fork commands generated for result 3")

    # Verify None and refine options exist
    assert options[3].id == "none"
    assert options[3].fork_terminal_cmd is None
    print("✓ 'None - start fresh' option present (no fork command)")

    assert options[4].id == "refine"
    assert options[4].fork_terminal_cmd is None
    print("✓ 'Type something else' option present (no fork command)")

    print("\n✓✓✓ All SelectionUI tests PASSED\n")


def verify_formatted_output():
    """Verify formatted output includes fork commands."""
    print("=" * 80)
    print("TEST 2: Formatted Output with Fork Commands")
    print("=" * 80)

    fork_generator = ForkGenerator(claude_sessions_dir="~/.claude")
    selection_ui = SelectionUI(fork_generator=fork_generator)

    results = [
        create_mock_result("abc123def456", 0.94, "realtime-dashboard"),
        create_mock_result("ghi789jkl012", 0.87, "api-websockets"),
    ]
    query = "implement real-time dashboard with WebSocket"

    options = selection_ui.create_options(results, query)
    prompt = selection_ui.format_selection_prompt(options, query)

    # Verify fork commands are in the prompt
    assert "Fork Commands (copy & paste):" in prompt
    print("✓ Fork commands section present in prompt")

    assert "New terminal:" in prompt
    assert "In-session:" in prompt
    print("✓ Both fork methods labeled in prompt")

    assert "claude --resume abc123def456" in prompt
    assert "/fork abc123def456" in prompt
    print("✓ Fork commands for result 1 in prompt")

    assert "claude --resume ghi789jkl012" in prompt
    assert "/fork ghi789jkl012" in prompt
    print("✓ Fork commands for result 2 in prompt")

    # Verify RECOMMENDED marker
    assert "⭐" in prompt
    assert "RECOMMENDED" in prompt
    print("✓ Recommended marker present in prompt")

    print("\n✓✓✓ All formatted output tests PASSED\n")


def verify_mcp_server_integration():
    """Verify MCP server integration."""
    print("=" * 80)
    print("TEST 3: MCP Server Integration")
    print("=" * 80)

    results = [
        create_mock_result("abc123def456", 0.94, "realtime-dashboard"),
    ]
    query = "implement real-time dashboard"

    # Call the function that the MCP server uses
    formatted_output = format_search_results_with_selection(
        query,
        results,
        claude_dir="~/.claude"
    )

    # Verify output structure
    assert "Fork Detection - Select a Session" in formatted_output
    print("✓ MCP server returns formatted selection UI")

    assert "Fork Commands (copy & paste):" in formatted_output
    print("✓ Fork commands included in MCP response")

    assert "claude --resume abc123def456" in formatted_output
    print("✓ Terminal fork command present")

    assert "/fork abc123def456" in formatted_output
    print("✓ In-session fork command present")

    assert "None of these - start fresh" in formatted_output
    print("✓ 'None' option present")

    assert "Type something else" in formatted_output
    print("✓ 'Refine search' option present")

    print("\n✓✓✓ All MCP server integration tests PASSED\n")


def verify_display_selection_data():
    """Verify display_selection returns proper data structure."""
    print("=" * 80)
    print("TEST 4: Display Selection Data Structure")
    print("=" * 80)

    fork_generator = ForkGenerator(claude_sessions_dir="~/.claude")
    selection_ui = SelectionUI(fork_generator=fork_generator)

    results = [
        create_mock_result("abc123def456", 0.94, "realtime-dashboard"),
    ]
    query = "test query"

    display_data = selection_ui.display_selection(results, query)

    # Verify structure
    assert 'prompt' in display_data
    assert 'options' in display_data
    assert 'query' in display_data
    assert 'num_results' in display_data
    print("✓ Display data has correct structure")

    # Verify options include fork commands
    assert len(display_data['options']) == 5
    print("✓ Display data has 5 options")

    result_option = display_data['options'][0]
    assert 'fork_terminal_cmd' in result_option
    assert 'fork_in_session_cmd' in result_option
    print("✓ Options include fork command fields")

    assert result_option['fork_terminal_cmd'] is not None
    assert "claude --resume abc123def456" in result_option['fork_terminal_cmd']
    print("✓ Fork terminal command is populated")

    assert result_option['fork_in_session_cmd'] is not None
    assert "/fork abc123def456" in result_option['fork_in_session_cmd']
    print("✓ Fork in-session command is populated")

    print("\n✓✓✓ All data structure tests PASSED\n")


def print_example_output():
    """Print example output to show what users will see."""
    print("=" * 80)
    print("EXAMPLE: What Users Will See")
    print("=" * 80)

    fork_generator = ForkGenerator(claude_sessions_dir="~/.claude")
    selection_ui = SelectionUI(fork_generator=fork_generator)

    results = [
        create_mock_result("abc123def456", 0.94, "realtime-dashboard"),
        create_mock_result("ghi789jkl012", 0.87, "api-websockets"),
        create_mock_result("mno345pqr678", 0.81, "frontend-react"),
    ]
    query = "implement real-time dashboard updates with WebSocket"

    formatted_output = format_search_results_with_selection(
        query,
        results,
        claude_dir="~/.claude"
    )

    print(formatted_output)
    print("\n" + "=" * 80)


def main():
    """Run all verification tests."""
    print("\n" + "=" * 80)
    print("PHASE 2 TASK 4 VERIFICATION")
    print("Integrate SelectionUI with MCP Server Flow")
    print("=" * 80 + "\n")

    try:
        verify_selection_ui_with_fork_commands()
        verify_formatted_output()
        verify_mcp_server_integration()
        verify_display_selection_data()

        print("\n" + "=" * 80)
        print("✅ ALL VERIFICATION TESTS PASSED")
        print("=" * 80 + "\n")

        print_example_output()

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print("✓ SelectionUI creates exactly 5 options")
        print("✓ Top 3 results are displayed with scores and previews")
        print("✓ Highest-scoring result marked as 'Recommended'")
        print("✓ Fork commands included for all results")
        print("✓ Both terminal and in-session fork commands available")
        print("✓ 'None - start fresh' option present")
        print("✓ 'Type something else' refinement option present")
        print("✓ MCP server properly integrates SelectionUI")
        print("✓ Users can copy-paste fork commands directly")
        print("\n✓✓✓ Task 4 integration is COMPLETE and FUNCTIONAL\n")

        return 0

    except AssertionError as e:
        print(f"\n❌ VERIFICATION FAILED: {e}\n")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
