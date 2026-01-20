"""
Unit tests for MemoryExtractor class.

Tests cover:
- Memory marker detection (PATTERN, WORKING_SOLUTION, WAITING)
- Context extraction around markers
- Memory type extraction from content
- Memory boost calculation
- Edge cases and error handling
"""

import unittest
from smart_fork.memory_extractor import MemoryExtractor, MemoryMarker


class TestMemoryExtractorInit(unittest.TestCase):
    """Test MemoryExtractor initialization."""

    def test_default_initialization(self):
        """Test default initialization."""
        extractor = MemoryExtractor()
        self.assertEqual(extractor.context_window, 100)

    def test_custom_context_window(self):
        """Test custom context window."""
        extractor = MemoryExtractor(context_window=50)
        self.assertEqual(extractor.context_window, 50)


class TestPatternDetection(unittest.TestCase):
    """Test PATTERN marker detection."""

    def setUp(self):
        self.extractor = MemoryExtractor()

    def test_detect_pattern_keyword(self):
        """Test detection of 'pattern' keyword."""
        content = "We should use the factory pattern here."
        types = self.extractor.extract_memory_types(content)
        self.assertIn('PATTERN', types)

    def test_detect_design_pattern(self):
        """Test detection of 'design pattern'."""
        content = "This is a common design pattern in React."
        types = self.extractor.extract_memory_types(content)
        self.assertIn('PATTERN', types)

    def test_detect_architectural_pattern(self):
        """Test detection of 'architectural pattern'."""
        content = "The architectural pattern we use is microservices."
        types = self.extractor.extract_memory_types(content)
        self.assertIn('PATTERN', types)

    def test_detect_approach(self):
        """Test detection of 'approach'."""
        content = "This approach works well for our use case."
        types = self.extractor.extract_memory_types(content)
        self.assertIn('PATTERN', types)

    def test_detect_strategy(self):
        """Test detection of 'strategy'."""
        content = "Our caching strategy improves performance."
        types = self.extractor.extract_memory_types(content)
        self.assertIn('PATTERN', types)

    def test_case_insensitive_pattern(self):
        """Test case-insensitive detection."""
        content = "We use the PATTERN here."
        types = self.extractor.extract_memory_types(content)
        self.assertIn('PATTERN', types)

    def test_no_pattern_detected(self):
        """Test when no pattern is present."""
        content = "Just some regular text without markers."
        types = self.extractor.extract_memory_types(content)
        self.assertNotIn('PATTERN', types)


class TestWorkingSolutionDetection(unittest.TestCase):
    """Test WORKING_SOLUTION marker detection."""

    def setUp(self):
        self.extractor = MemoryExtractor()

    def test_detect_working_solution(self):
        """Test detection of 'working solution'."""
        content = "This is a working solution that we've tested."
        types = self.extractor.extract_memory_types(content)
        self.assertIn('WORKING_SOLUTION', types)

    def test_detect_proven_implementation(self):
        """Test detection of 'proven implementation'."""
        content = "The proven implementation handles edge cases."
        types = self.extractor.extract_memory_types(content)
        self.assertIn('WORKING_SOLUTION', types)

    def test_detect_successful(self):
        """Test detection of 'successful'."""
        content = "The deployment was successful."
        types = self.extractor.extract_memory_types(content)
        self.assertIn('WORKING_SOLUTION', types)

    def test_detect_tested(self):
        """Test detection of 'tested'."""
        content = "This code has been tested thoroughly."
        types = self.extractor.extract_memory_types(content)
        self.assertIn('WORKING_SOLUTION', types)

    def test_detect_verified(self):
        """Test detection of 'verified'."""
        content = "The fix has been verified in production."
        types = self.extractor.extract_memory_types(content)
        self.assertIn('WORKING_SOLUTION', types)

    def test_detect_all_tests_pass(self):
        """Test detection of 'all tests pass'."""
        content = "Great! All tests pass now."
        types = self.extractor.extract_memory_types(content)
        self.assertIn('WORKING_SOLUTION', types)

    def test_no_working_solution_detected(self):
        """Test when no working solution is present."""
        content = "This is still in progress."
        types = self.extractor.extract_memory_types(content)
        self.assertNotIn('WORKING_SOLUTION', types)


class TestWaitingDetection(unittest.TestCase):
    """Test WAITING marker detection."""

    def setUp(self):
        self.extractor = MemoryExtractor()

    def test_detect_waiting(self):
        """Test detection of 'waiting'."""
        content = "We're waiting for the API response."
        types = self.extractor.extract_memory_types(content)
        self.assertIn('WAITING', types)

    def test_detect_pending(self):
        """Test detection of 'pending'."""
        content = "This feature is pending approval."
        types = self.extractor.extract_memory_types(content)
        self.assertIn('WAITING', types)

    def test_detect_to_be_completed(self):
        """Test detection of 'to be completed'."""
        content = "This task is to be completed later."
        types = self.extractor.extract_memory_types(content)
        self.assertIn('WAITING', types)

    def test_detect_todo(self):
        """Test detection of 'todo'."""
        content = "TODO: Implement caching layer."
        types = self.extractor.extract_memory_types(content)
        self.assertIn('WAITING', types)

    def test_detect_in_progress(self):
        """Test detection of 'in progress'."""
        content = "This feature is in progress."
        types = self.extractor.extract_memory_types(content)
        self.assertIn('WAITING', types)

    def test_detect_blocked(self):
        """Test detection of 'blocked'."""
        content = "The deployment is blocked by dependencies."
        types = self.extractor.extract_memory_types(content)
        self.assertIn('WAITING', types)

    def test_no_waiting_detected(self):
        """Test when no waiting is present."""
        content = "Everything is complete and working."
        types = self.extractor.extract_memory_types(content)
        self.assertNotIn('WAITING', types)


class TestMultipleMemoryTypes(unittest.TestCase):
    """Test detection of multiple memory types in same content."""

    def setUp(self):
        self.extractor = MemoryExtractor()

    def test_pattern_and_working_solution(self):
        """Test detection of both PATTERN and WORKING_SOLUTION."""
        content = "We used the factory pattern and it's a working solution."
        types = self.extractor.extract_memory_types(content)
        self.assertIn('PATTERN', types)
        self.assertIn('WORKING_SOLUTION', types)

    def test_all_three_types(self):
        """Test detection of all three memory types."""
        content = """
        We implemented the observer pattern successfully.
        The solution has been tested and verified.
        Still waiting for code review before merging.
        """
        types = self.extractor.extract_memory_types(content)
        self.assertIn('PATTERN', types)
        self.assertIn('WORKING_SOLUTION', types)
        self.assertIn('WAITING', types)
        self.assertEqual(len(types), 3)

    def test_sorted_output(self):
        """Test that output is sorted alphabetically."""
        content = "Waiting for the pattern to be tested successfully."
        types = self.extractor.extract_memory_types(content)
        # Should be sorted: PATTERN, WAITING, WORKING_SOLUTION
        expected = sorted(types)
        self.assertEqual(types, expected)


class TestExtractMarkers(unittest.TestCase):
    """Test detailed marker extraction with context."""

    def setUp(self):
        self.extractor = MemoryExtractor(context_window=30)

    def test_extract_single_marker(self):
        """Test extracting a single marker."""
        content = "We should use the factory pattern here for better modularity."
        markers = self.extractor.extract_markers(content)
        self.assertEqual(len(markers), 1)
        self.assertEqual(markers[0].memory_type, 'PATTERN')
        self.assertIsInstance(markers[0].position, int)
        self.assertIn('pattern', markers[0].context.lower())

    def test_extract_multiple_markers(self):
        """Test extracting multiple markers."""
        content = "The pattern works and has been tested. Still pending review."
        markers = self.extractor.extract_markers(content)
        self.assertGreaterEqual(len(markers), 2)
        types = [m.memory_type for m in markers]
        self.assertIn('PATTERN', types)
        self.assertIn('WORKING_SOLUTION', types)

    def test_markers_sorted_by_position(self):
        """Test that markers are sorted by position."""
        content = "Pending review of the tested pattern implementation."
        markers = self.extractor.extract_markers(content)
        positions = [m.position for m in markers]
        self.assertEqual(positions, sorted(positions))

    def test_context_extraction(self):
        """Test context extraction around marker."""
        content = "A" * 100 + " pattern " + "B" * 100
        markers = self.extractor.extract_markers(content)
        self.assertGreater(len(markers), 0)
        # Context should include text before and after
        self.assertIn('pattern', markers[0].context)

    def test_context_with_ellipsis(self):
        """Test that ellipsis is added when context is truncated."""
        content = "A" * 200 + " pattern " + "B" * 200
        markers = self.extractor.extract_markers(content)
        self.assertGreater(len(markers), 0)
        context = markers[0].context
        # Should have ellipsis on both sides
        self.assertTrue(context.startswith('...') or context.endswith('...'))


class TestHasMemoryType(unittest.TestCase):
    """Test has_memory_type method."""

    def setUp(self):
        self.extractor = MemoryExtractor()

    def test_has_pattern(self):
        """Test checking for PATTERN."""
        content = "We use the factory pattern."
        self.assertTrue(self.extractor.has_memory_type(content, 'PATTERN'))
        self.assertFalse(self.extractor.has_memory_type(content, 'WAITING'))

    def test_has_working_solution(self):
        """Test checking for WORKING_SOLUTION."""
        content = "This is a working solution."
        self.assertTrue(self.extractor.has_memory_type(content, 'WORKING_SOLUTION'))
        self.assertFalse(self.extractor.has_memory_type(content, 'PATTERN'))

    def test_has_waiting(self):
        """Test checking for WAITING."""
        content = "This is pending approval."
        self.assertTrue(self.extractor.has_memory_type(content, 'WAITING'))
        self.assertFalse(self.extractor.has_memory_type(content, 'PATTERN'))

    def test_case_insensitive_type(self):
        """Test that memory_type parameter is case-insensitive."""
        content = "We use a pattern."
        self.assertTrue(self.extractor.has_memory_type(content, 'pattern'))
        self.assertTrue(self.extractor.has_memory_type(content, 'PATTERN'))
        self.assertTrue(self.extractor.has_memory_type(content, 'Pattern'))

    def test_invalid_memory_type(self):
        """Test with invalid memory type."""
        content = "Some content."
        self.assertFalse(self.extractor.has_memory_type(content, 'INVALID'))


class TestMemoryBoost(unittest.TestCase):
    """Test memory boost calculation."""

    def setUp(self):
        self.extractor = MemoryExtractor()

    def test_pattern_boost(self):
        """Test PATTERN boost (5%)."""
        boost = self.extractor.get_memory_boost(['PATTERN'])
        self.assertEqual(boost, 0.05)

    def test_working_solution_boost(self):
        """Test WORKING_SOLUTION boost (8%)."""
        boost = self.extractor.get_memory_boost(['WORKING_SOLUTION'])
        self.assertEqual(boost, 0.08)

    def test_waiting_boost(self):
        """Test WAITING boost (2%)."""
        boost = self.extractor.get_memory_boost(['WAITING'])
        self.assertEqual(boost, 0.02)

    def test_multiple_boosts(self):
        """Test additive boosts."""
        boost = self.extractor.get_memory_boost(['PATTERN', 'WORKING_SOLUTION'])
        self.assertEqual(boost, 0.13)  # 5% + 8%

    def test_all_boosts(self):
        """Test all three boosts."""
        boost = self.extractor.get_memory_boost(['PATTERN', 'WORKING_SOLUTION', 'WAITING'])
        self.assertEqual(boost, 0.15)  # 5% + 8% + 2%

    def test_empty_list(self):
        """Test with empty list."""
        boost = self.extractor.get_memory_boost([])
        self.assertEqual(boost, 0.0)

    def test_unknown_type_ignored(self):
        """Test that unknown types are ignored."""
        boost = self.extractor.get_memory_boost(['PATTERN', 'UNKNOWN'])
        self.assertEqual(boost, 0.05)  # Only PATTERN counts


class TestExtractFromMessages(unittest.TestCase):
    """Test extracting memory types from message lists."""

    def setUp(self):
        self.extractor = MemoryExtractor()

    def test_extract_from_single_message(self):
        """Test extraction from single message."""
        messages = [
            {'content': 'We use the factory pattern here.'}
        ]
        types = self.extractor.extract_from_messages(messages)
        self.assertIn('PATTERN', types)

    def test_extract_from_multiple_messages(self):
        """Test extraction from multiple messages."""
        messages = [
            {'content': 'We use a pattern.'},
            {'content': 'The solution has been tested.'},
            {'content': 'Still waiting for approval.'}
        ]
        types = self.extractor.extract_from_messages(messages)
        self.assertIn('PATTERN', types)
        self.assertIn('WORKING_SOLUTION', types)
        self.assertIn('WAITING', types)

    def test_deduplicate_types(self):
        """Test that duplicate types are deduplicated."""
        messages = [
            {'content': 'Pattern one.'},
            {'content': 'Pattern two.'},
            {'content': 'Pattern three.'}
        ]
        types = self.extractor.extract_from_messages(messages)
        self.assertEqual(types.count('PATTERN'), 1)

    def test_empty_messages(self):
        """Test with empty message list."""
        types = self.extractor.extract_from_messages([])
        self.assertEqual(types, [])

    def test_messages_without_content(self):
        """Test messages without content field."""
        messages = [
            {'role': 'user'},
            {'content': ''},
        ]
        types = self.extractor.extract_from_messages(messages)
        self.assertEqual(types, [])

    def test_non_string_content(self):
        """Test handling of non-string content."""
        messages = [
            {'content': None},
            {'content': 123},
            {'content': 'Valid pattern text.'}
        ]
        types = self.extractor.extract_from_messages(messages)
        self.assertIn('PATTERN', types)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        self.extractor = MemoryExtractor()

    def test_empty_content(self):
        """Test with empty content."""
        types = self.extractor.extract_memory_types('')
        self.assertEqual(types, [])

    def test_whitespace_only(self):
        """Test with whitespace-only content."""
        types = self.extractor.extract_memory_types('   \n\t   ')
        self.assertEqual(types, [])

    def test_very_long_content(self):
        """Test with very long content."""
        content = 'pattern ' * 10000
        types = self.extractor.extract_memory_types(content)
        self.assertIn('PATTERN', types)

    def test_unicode_content(self):
        """Test with unicode characters."""
        content = "We use the pattern 模式 here 这里."
        types = self.extractor.extract_memory_types(content)
        self.assertIn('PATTERN', types)

    def test_special_characters(self):
        """Test with special characters."""
        content = "Pattern! @#$% tested&verified waiting..."
        types = self.extractor.extract_memory_types(content)
        self.assertIn('PATTERN', types)
        self.assertIn('WORKING_SOLUTION', types)
        self.assertIn('WAITING', types)

    def test_word_boundaries(self):
        """Test that we match whole words only."""
        # 'patterned' should not match 'pattern' because of \b word boundaries
        content = "This is patterned fabric."
        types = self.extractor.extract_memory_types(content)
        # Should not match because 'pattern' in 'patterned' doesn't have word boundaries
        self.assertNotIn('PATTERN', types)


if __name__ == '__main__':
    unittest.main()
