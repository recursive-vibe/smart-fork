"""
Unit tests for SearchService.

Tests the search orchestration, chunk grouping, score calculation,
ranking, and result generation functionality.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from typing import List

from smart_fork.search_service import SearchService, SessionSearchResult
from smart_fork.embedding_service import EmbeddingService
from smart_fork.vector_db_service import VectorDBService, ChunkSearchResult
from smart_fork.scoring_service import ScoringService, SessionScore
from smart_fork.session_registry import SessionRegistry, SessionMetadata


class TestSearchServiceInit(unittest.TestCase):
    """Test SearchService initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        embedding_service = Mock(spec=EmbeddingService)
        vector_db_service = Mock(spec=VectorDBService)
        scoring_service = Mock(spec=ScoringService)
        session_registry = Mock(spec=SessionRegistry)

        search_service = SearchService(
            embedding_service=embedding_service,
            vector_db_service=vector_db_service,
            scoring_service=scoring_service,
            session_registry=session_registry
        )

        self.assertEqual(search_service.k_chunks, 200)
        self.assertEqual(search_service.top_n_sessions, 5)
        self.assertEqual(search_service.preview_length, 200)

    def test_init_with_custom_parameters(self):
        """Test initialization with custom parameters."""
        embedding_service = Mock(spec=EmbeddingService)
        vector_db_service = Mock(spec=VectorDBService)
        scoring_service = Mock(spec=ScoringService)
        session_registry = Mock(spec=SessionRegistry)

        search_service = SearchService(
            embedding_service=embedding_service,
            vector_db_service=vector_db_service,
            scoring_service=scoring_service,
            session_registry=session_registry,
            k_chunks=100,
            top_n_sessions=10,
            preview_length=150
        )

        self.assertEqual(search_service.k_chunks, 100)
        self.assertEqual(search_service.top_n_sessions, 10)
        self.assertEqual(search_service.preview_length, 150)


class TestSearchServiceGroupChunks(unittest.TestCase):
    """Test chunk grouping functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.embedding_service = Mock(spec=EmbeddingService)
        self.vector_db_service = Mock(spec=VectorDBService)
        self.scoring_service = Mock(spec=ScoringService)
        self.session_registry = Mock(spec=SessionRegistry)

        self.search_service = SearchService(
            embedding_service=self.embedding_service,
            vector_db_service=self.vector_db_service,
            scoring_service=self.scoring_service,
            session_registry=self.session_registry
        )

    def test_group_chunks_single_session(self):
        """Test grouping chunks from a single session."""
        chunks = [
            ChunkSearchResult(
                chunk_id='chunk1',
                session_id='session1',
                content='content1',
                metadata={},
                similarity=0.9,
                chunk_index=0
            ),
            ChunkSearchResult(
                chunk_id='chunk2',
                session_id='session1',
                content='content2',
                metadata={},
                similarity=0.8,
                chunk_index=1
            )
        ]

        grouped = self.search_service._group_chunks_by_session(chunks)

        self.assertEqual(len(grouped), 1)
        self.assertIn('session1', grouped)
        self.assertEqual(len(grouped['session1']), 2)

    def test_group_chunks_multiple_sessions(self):
        """Test grouping chunks from multiple sessions."""
        chunks = [
            ChunkSearchResult(
                chunk_id='chunk1',
                session_id='session1',
                content='content1',
                metadata={},
                similarity=0.9,
                chunk_index=0
            ),
            ChunkSearchResult(
                chunk_id='chunk2',
                session_id='session2',
                content='content2',
                metadata={},
                similarity=0.8,
                chunk_index=0
            ),
            ChunkSearchResult(
                chunk_id='chunk3',
                session_id='session1',
                content='content3',
                metadata={},
                similarity=0.7,
                chunk_index=1
            )
        ]

        grouped = self.search_service._group_chunks_by_session(chunks)

        self.assertEqual(len(grouped), 2)
        self.assertEqual(len(grouped['session1']), 2)
        self.assertEqual(len(grouped['session2']), 1)

    def test_group_chunks_sorted_by_index(self):
        """Test that chunks are sorted by chunk_index within each session."""
        chunks = [
            ChunkSearchResult(
                chunk_id='chunk2',
                session_id='session1',
                content='content2',
                metadata={},
                similarity=0.9,
                chunk_index=2
            ),
            ChunkSearchResult(
                chunk_id='chunk1',
                session_id='session1',
                content='content1',
                metadata={},
                similarity=0.8,
                chunk_index=0
            ),
            ChunkSearchResult(
                chunk_id='chunk3',
                session_id='session1',
                content='content3',
                metadata={},
                similarity=0.7,
                chunk_index=1
            )
        ]

        grouped = self.search_service._group_chunks_by_session(chunks)

        # Verify sorted by chunk_index
        self.assertEqual(grouped['session1'][0].chunk_index, 0)
        self.assertEqual(grouped['session1'][1].chunk_index, 1)
        self.assertEqual(grouped['session1'][2].chunk_index, 2)

    def test_group_chunks_empty_list(self):
        """Test grouping empty chunk list."""
        grouped = self.search_service._group_chunks_by_session([])
        self.assertEqual(len(grouped), 0)


class TestSearchServiceCalculateScores(unittest.TestCase):
    """Test session score calculation."""

    def setUp(self):
        """Set up test fixtures."""
        self.embedding_service = Mock(spec=EmbeddingService)
        self.vector_db_service = Mock(spec=VectorDBService)
        self.scoring_service = ScoringService()
        self.session_registry = Mock(spec=SessionRegistry)

        self.search_service = SearchService(
            embedding_service=self.embedding_service,
            vector_db_service=self.vector_db_service,
            scoring_service=self.scoring_service,
            session_registry=self.session_registry
        )

    def test_calculate_session_scores_with_metadata(self):
        """Test score calculation with session metadata."""
        session_chunks = {
            'session1': [
                ChunkSearchResult(
                    chunk_id='chunk1',
                    session_id='session1',
                    content='content1',
                    metadata={},
                    similarity=0.9,
                    chunk_index=0
                )
            ]
        }

        # Mock session metadata
        session_metadata = SessionMetadata(
            session_id='session1',
            chunk_count=10,
            last_modified=datetime.now().isoformat()
        )
        self.session_registry.get_session.return_value = session_metadata

        scores = self.search_service._calculate_session_scores(session_chunks)

        self.assertEqual(len(scores), 1)
        self.assertEqual(scores[0].session_id, 'session1')
        self.assertGreater(scores[0].final_score, 0)

    def test_calculate_session_scores_without_metadata(self):
        """Test score calculation without session metadata."""
        session_chunks = {
            'session1': [
                ChunkSearchResult(
                    chunk_id='chunk1',
                    session_id='session1',
                    content='content1',
                    metadata={},
                    similarity=0.9,
                    chunk_index=0
                )
            ]
        }

        # Mock no metadata found
        self.session_registry.get_session.return_value = None

        scores = self.search_service._calculate_session_scores(session_chunks)

        self.assertEqual(len(scores), 1)
        self.assertEqual(scores[0].session_id, 'session1')

    def test_calculate_session_scores_with_memory_types(self):
        """Test score calculation extracts memory types from chunks."""
        session_chunks = {
            'session1': [
                ChunkSearchResult(
                    chunk_id='chunk1',
                    session_id='session1',
                    content='content1',
                    metadata={'memory_types': ['PATTERN', 'WORKING_SOLUTION']},
                    similarity=0.9,
                    chunk_index=0
                ),
                ChunkSearchResult(
                    chunk_id='chunk2',
                    session_id='session1',
                    content='content2',
                    metadata={'memory_types': ['WAITING']},
                    similarity=0.8,
                    chunk_index=1
                )
            ]
        }

        session_metadata = SessionMetadata(
            session_id='session1',
            chunk_count=10
        )
        self.session_registry.get_session.return_value = session_metadata

        scores = self.search_service._calculate_session_scores(session_chunks)

        # Score should be boosted by memory types
        self.assertGreater(scores[0].memory_boost, 0)

    def test_calculate_session_scores_multiple_sessions(self):
        """Test score calculation for multiple sessions."""
        session_chunks = {
            'session1': [
                ChunkSearchResult(
                    chunk_id='chunk1',
                    session_id='session1',
                    content='content1',
                    metadata={},
                    similarity=0.9,
                    chunk_index=0
                )
            ],
            'session2': [
                ChunkSearchResult(
                    chunk_id='chunk2',
                    session_id='session2',
                    content='content2',
                    metadata={},
                    similarity=0.8,
                    chunk_index=0
                )
            ]
        }

        self.session_registry.get_session.return_value = SessionMetadata(
            session_id='test',
            chunk_count=10
        )

        scores = self.search_service._calculate_session_scores(session_chunks)

        self.assertEqual(len(scores), 2)


class TestSearchServiceGeneratePreview(unittest.TestCase):
    """Test preview generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.embedding_service = Mock(spec=EmbeddingService)
        self.vector_db_service = Mock(spec=VectorDBService)
        self.scoring_service = Mock(spec=ScoringService)
        self.session_registry = Mock(spec=SessionRegistry)

        self.search_service = SearchService(
            embedding_service=self.embedding_service,
            vector_db_service=self.vector_db_service,
            scoring_service=self.scoring_service,
            session_registry=self.session_registry,
            preview_length=50
        )

    def test_generate_preview_short_content(self):
        """Test preview generation with short content."""
        chunks = [
            ChunkSearchResult(
                chunk_id='chunk1',
                session_id='session1',
                content='Short content',
                metadata={},
                similarity=0.9,
                chunk_index=0
            )
        ]

        preview = self.search_service._generate_preview(chunks)
        self.assertEqual(preview, 'Short content')

    def test_generate_preview_long_content(self):
        """Test preview generation with long content that needs truncation."""
        long_content = 'This is a very long piece of content that will definitely exceed the preview length limit and should be truncated at a word boundary'

        chunks = [
            ChunkSearchResult(
                chunk_id='chunk1',
                session_id='session1',
                content=long_content,
                metadata={},
                similarity=0.9,
                chunk_index=0
            )
        ]

        preview = self.search_service._generate_preview(chunks)

        self.assertLessEqual(len(preview), 54)  # 50 + "..."
        self.assertTrue(preview.endswith('...'))

    def test_generate_preview_uses_best_chunk(self):
        """Test that preview uses the highest-scoring chunk."""
        chunks = [
            ChunkSearchResult(
                chunk_id='chunk1',
                session_id='session1',
                content='Low score content',
                metadata={},
                similarity=0.6,
                chunk_index=0
            ),
            ChunkSearchResult(
                chunk_id='chunk2',
                session_id='session1',
                content='High score content',
                metadata={},
                similarity=0.9,
                chunk_index=1
            )
        ]

        preview = self.search_service._generate_preview(chunks)
        self.assertEqual(preview, 'High score content')

    def test_generate_preview_empty_chunks(self):
        """Test preview generation with empty chunk list."""
        preview = self.search_service._generate_preview([])
        self.assertEqual(preview, '')


class TestSearchServiceSearch(unittest.TestCase):
    """Test full search workflow."""

    def setUp(self):
        """Set up test fixtures."""
        self.embedding_service = Mock(spec=EmbeddingService)
        self.vector_db_service = Mock(spec=VectorDBService)
        self.scoring_service = ScoringService()
        self.session_registry = Mock(spec=SessionRegistry)

        self.search_service = SearchService(
            embedding_service=self.embedding_service,
            vector_db_service=self.vector_db_service,
            scoring_service=self.scoring_service,
            session_registry=self.session_registry,
            top_n_sessions=2
        )

    def test_search_full_workflow(self):
        """Test complete search workflow from query to results."""
        # Mock embedding generation
        query_embedding = [0.1] * 768
        self.embedding_service.embed_single.return_value = query_embedding

        # Mock vector search results
        search_results = [
            ChunkSearchResult(
                chunk_id='chunk1',
                session_id='session1',
                content='Content about Python',
                metadata={},
                similarity=0.9,
                chunk_index=0
            ),
            ChunkSearchResult(
                chunk_id='chunk2',
                session_id='session2',
                content='Content about JavaScript',
                metadata={},
                similarity=0.8,
                chunk_index=0
            ),
            ChunkSearchResult(
                chunk_id='chunk3',
                session_id='session1',
                content='More Python content',
                metadata={},
                similarity=0.7,
                chunk_index=1
            )
        ]
        self.vector_db_service.search_chunks.return_value = search_results

        # Mock session metadata
        def get_session_mock(session_id):
            return SessionMetadata(
                session_id=session_id,
                chunk_count=10,
                project='test-project',
                last_modified=datetime.now().isoformat()
            )
        self.session_registry.get_session.side_effect = get_session_mock

        # Execute search
        results = self.search_service.search('test query')

        # Verify results
        self.assertEqual(len(results), 2)  # top_n_sessions=2
        self.assertIsInstance(results[0], SessionSearchResult)

        # Verify higher-scored session comes first
        self.assertGreaterEqual(
            results[0].score.final_score,
            results[1].score.final_score
        )

        # Verify embedding service was called
        self.embedding_service.load_model.assert_called_once()
        self.embedding_service.embed_single.assert_called_once_with('test query')

        # Verify vector search was called
        self.vector_db_service.search_chunks.assert_called_once()

    def test_search_no_embedding_generated(self):
        """Test search when embedding generation fails."""
        self.embedding_service.embed_single.return_value = []

        results = self.search_service.search('test query')

        self.assertEqual(len(results), 0)

    def test_search_no_chunks_found(self):
        """Test search when no matching chunks found."""
        query_embedding = [0.1] * 768
        self.embedding_service.embed_single.return_value = query_embedding
        self.vector_db_service.search_chunks.return_value = []

        results = self.search_service.search('test query')

        self.assertEqual(len(results), 0)

    def test_search_custom_top_n(self):
        """Test search with custom top_n parameter."""
        query_embedding = [0.1] * 768
        self.embedding_service.embed_single.return_value = query_embedding

        # Create 10 chunks from 5 different sessions
        search_results = []
        for i in range(5):
            for j in range(2):
                search_results.append(ChunkSearchResult(
                    chunk_id=f'chunk{i}_{j}',
                    session_id=f'session{i}',
                    content=f'Content {i}',
                    metadata={},
                    similarity=0.9 - (i * 0.1),
                    chunk_index=j
                ))

        self.vector_db_service.search_chunks.return_value = search_results

        def get_session_mock(session_id):
            return SessionMetadata(
                session_id=session_id,
                chunk_count=10
            )
        self.session_registry.get_session.side_effect = get_session_mock

        # Request top 3
        results = self.search_service.search('test query', top_n=3)

        self.assertEqual(len(results), 3)

    def test_search_with_metadata_filter(self):
        """Test search with metadata filter."""
        query_embedding = [0.1] * 768
        self.embedding_service.embed_single.return_value = query_embedding
        self.vector_db_service.search_chunks.return_value = []

        filter_metadata = {'project': 'test-project'}
        self.search_service.search('test query', filter_metadata=filter_metadata)

        # Verify filter was passed to vector search
        call_args = self.vector_db_service.search_chunks.call_args
        self.assertEqual(call_args.kwargs['filter_metadata'], filter_metadata)


class TestSearchServiceStats(unittest.TestCase):
    """Test statistics functionality."""

    def test_get_stats(self):
        """Test getting service statistics."""
        embedding_service = Mock(spec=EmbeddingService)
        vector_db_service = Mock(spec=VectorDBService)
        scoring_service = Mock(spec=ScoringService)
        session_registry = Mock(spec=SessionRegistry)

        vector_db_service.get_stats.return_value = {
            'total_chunks': 1000,
            'total_sessions': 50
        }

        session_registry.get_stats.return_value = {
            'total_sessions': 50,
            'total_chunks': 1000
        }

        search_service = SearchService(
            embedding_service=embedding_service,
            vector_db_service=vector_db_service,
            scoring_service=scoring_service,
            session_registry=session_registry,
            k_chunks=150,
            top_n_sessions=7,
            preview_length=300
        )

        stats = search_service.get_stats()

        self.assertEqual(stats['k_chunks'], 150)
        self.assertEqual(stats['top_n_sessions'], 7)
        self.assertEqual(stats['preview_length'], 300)
        self.assertIn('vector_db', stats)
        self.assertIn('registry', stats)


class TestSessionSearchResult(unittest.TestCase):
    """Test SessionSearchResult dataclass."""

    def test_to_dict(self):
        """Test converting SessionSearchResult to dictionary."""
        score = SessionScore(
            session_id='session1',
            final_score=0.85,
            best_similarity=0.9,
            avg_similarity=0.8,
            chunk_ratio=0.5,
            recency_score=0.9,
            chain_quality=0.5,
            memory_boost=0.05,
            num_chunks_matched=5,
            preference_boost=0.0
        )

        metadata = SessionMetadata(
            session_id='session1',
            project='test-project'
        )

        chunks = [
            ChunkSearchResult(
                chunk_id='chunk1',
                session_id='session1',
                content='content',
                metadata={},
                similarity=0.9,
                chunk_index=0
            )
        ]

        result = SessionSearchResult(
            session_id='session1',
            score=score,
            metadata=metadata,
            preview='Preview text',
            matched_chunks=chunks
        )

        result_dict = result.to_dict()

        self.assertEqual(result_dict['session_id'], 'session1')
        self.assertEqual(result_dict['preview'], 'Preview text')
        self.assertEqual(result_dict['num_matched_chunks'], 1)
        self.assertIn('score', result_dict)
        self.assertIn('metadata', result_dict)


if __name__ == '__main__':
    unittest.main()
