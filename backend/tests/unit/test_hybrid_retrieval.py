"""
Unit tests for hybrid retrieval system.

Tests verify:
1. RRF output always returns ≥ 5 chunks
2. Fused rank is never worse than worst individual rank
3. Dense search functionality
4. Sparse search functionality
5. RRF fusion correctness
6. Fallback behavior when ChromaDB unavailable
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from hypothesis import given, strategies as st, settings as hypothesis_settings, HealthCheck

from app.ml.hybrid_retrieval import HybridRetriever, ScoredChunk
from app.models import Chunk


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db_session_factory():
    """Create a mock database session factory."""
    async def factory():
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        return mock_session
    return factory


@pytest.fixture
def sample_chunks():
    """Create sample chunks for testing."""
    chunks = []
    for i in range(20):
        chunk = Mock(spec=Chunk)
        chunk.id = i + 1
        chunk.chunk_text = f"This is sample chunk {i+1} about financial data and revenue metrics."
        chunk.section_label = f"Item {(i % 7) + 1}"
        chunk.page_number = (i // 5) + 1
        chunks.append(chunk)
    return chunks


@pytest.fixture
def retriever_with_mocked_chroma(mock_db_session_factory):
    """Create a retriever with mocked ChromaDB."""
    with patch('app.ml.hybrid_retrieval.chromadb.PersistentClient') as mock_chroma, \
         patch('app.ml.hybrid_retrieval.SentenceTransformer') as mock_transformer:
        
        # Mock ChromaDB collection
        mock_collection = Mock()
        mock_client = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chroma.return_value = mock_client
        
        # Mock embedding model
        mock_model = Mock()
        mock_model.encode.return_value = Mock(tolist=lambda: [0.1] * 384)
        mock_transformer.return_value = mock_model
        
        retriever = HybridRetriever(mock_db_session_factory)
        retriever.collection = mock_collection
        
        yield retriever


# ============================================================================
# Unit Tests
# ============================================================================

class TestDenseSearch:
    """Tests for dense semantic search."""
    
    def test_dense_search_returns_scored_chunks(self, retriever_with_mocked_chroma):
        """Test that dense search returns properly formatted ScoredChunk objects."""
        # Mock ChromaDB query response
        retriever_with_mocked_chroma.collection.query.return_value = {
            'ids': [['1', '2', '3']],
            'documents': [['chunk 1 text', 'chunk 2 text', 'chunk 3 text']],
            'distances': [[0.1, 0.2, 0.3]],
            'metadatas': [[
                {'section_label': 'Item 1', 'page_number': '1', 'company': 'Apple', 'filing_type': '10-K'},
                {'section_label': 'Item 2', 'page_number': '2', 'company': 'Apple', 'filing_type': '10-K'},
                {'section_label': 'Item 3', 'page_number': '3', 'company': 'Apple', 'filing_type': '10-K'}
            ]]
        }
        
        results = retriever_with_mocked_chroma.dense_search("test query", top_k=3)
        
        assert len(results) == 3
        assert all(isinstance(chunk, ScoredChunk) for chunk in results)
        assert results[0].chunk_id == 1
        assert results[0].score == pytest.approx(0.9, abs=0.01)  # 1 - 0.1
        assert results[0].section_label == 'Item 1'
    
    def test_dense_search_handles_empty_results(self, retriever_with_mocked_chroma):
        """Test that dense search handles empty results gracefully."""
        retriever_with_mocked_chroma.collection.query.return_value = {
            'ids': [[]],
            'documents': [[]],
            'distances': [[]],
            'metadatas': [[]]
        }
        
        results = retriever_with_mocked_chroma.dense_search("test query", top_k=5)
        
        assert results == []
    
    def test_dense_search_when_chroma_unavailable(self, mock_db_session_factory):
        """Test that dense search returns empty list when ChromaDB unavailable."""
        with patch('app.ml.hybrid_retrieval.chromadb.PersistentClient', side_effect=Exception("Connection failed")):
            retriever = HybridRetriever(mock_db_session_factory)
            results = retriever.dense_search("test query", top_k=5)
            assert results == []


class TestSparseSearch:
    """Tests for sparse BM25 search."""
    
    @pytest.mark.asyncio
    async def test_sparse_search_returns_scored_chunks(self, retriever_with_mocked_chroma, sample_chunks):
        """Test that sparse search returns properly formatted ScoredChunk objects."""
        # Build BM25 index with sample chunks
        retriever_with_mocked_chroma.bm25_chunks = sample_chunks
        retriever_with_mocked_chroma.bm25_chunk_ids = [chunk.id for chunk in sample_chunks]
        
        # Mock BM25 index
        mock_bm25 = Mock()
        mock_bm25.get_scores.return_value = [10.0, 8.0, 6.0, 4.0, 2.0] + [0.0] * 15
        retriever_with_mocked_chroma.bm25_index = mock_bm25
        
        results = retriever_with_mocked_chroma.sparse_search("revenue metrics", top_k=5)
        
        assert len(results) == 5
        assert all(isinstance(chunk, ScoredChunk) for chunk in results)
        assert results[0].score > results[1].score  # Scores should be descending
    
    def test_sparse_search_when_index_unavailable(self, retriever_with_mocked_chroma):
        """Test that sparse search returns empty list when BM25 index unavailable."""
        retriever_with_mocked_chroma.bm25_index = None
        retriever_with_mocked_chroma.bm25_chunks = []
        
        results = retriever_with_mocked_chroma.sparse_search("test query", top_k=5)
        
        assert results == []


class TestRRFFusion:
    """Tests for Reciprocal Rank Fusion."""
    
    def test_rrf_fusion_combines_results(self, retriever_with_mocked_chroma):
        """Test that RRF fusion correctly combines dense and sparse results."""
        dense_results = [
            ScoredChunk(chunk_id=1, chunk_text="chunk 1", score=0.9),
            ScoredChunk(chunk_id=2, chunk_text="chunk 2", score=0.8),
            ScoredChunk(chunk_id=3, chunk_text="chunk 3", score=0.7),
        ]
        
        sparse_results = [
            ScoredChunk(chunk_id=2, chunk_text="chunk 2", score=10.0),
            ScoredChunk(chunk_id=4, chunk_text="chunk 4", score=8.0),
            ScoredChunk(chunk_id=1, chunk_text="chunk 1", score=6.0),
        ]
        
        fused = retriever_with_mocked_chroma.rrf_fusion(dense_results, sparse_results, k=60)
        
        # Verify all unique chunks are present
        chunk_ids = [chunk.chunk_id for chunk in fused]
        assert set(chunk_ids) == {1, 2, 3, 4}
        
        # Verify scores are RRF scores (not original scores)
        assert all(0 < chunk.score < 1 for chunk in fused)
    
    def test_rrf_fusion_rank_property(self, retriever_with_mocked_chroma):
        """
        Test that fused rank is never worse than worst individual rank.
        
        **Validates: Requirements 3**
        
        For any chunk appearing in both dense and sparse results,
        its RRF rank should be at least as good as its worst individual rank.
        """
        dense_results = [
            ScoredChunk(chunk_id=1, chunk_text="chunk 1", score=0.9),
            ScoredChunk(chunk_id=2, chunk_text="chunk 2", score=0.8),
            ScoredChunk(chunk_id=3, chunk_text="chunk 3", score=0.7),
        ]
        
        sparse_results = [
            ScoredChunk(chunk_id=2, chunk_text="chunk 2", score=10.0),
            ScoredChunk(chunk_id=3, chunk_text="chunk 3", score=8.0),
            ScoredChunk(chunk_id=1, chunk_text="chunk 1", score=6.0),
        ]
        
        fused = retriever_with_mocked_chroma.rrf_fusion(dense_results, sparse_results, k=60)
        
        # Build rank maps
        dense_ranks = {chunk.chunk_id: rank + 1 for rank, chunk in enumerate(dense_results)}
        sparse_ranks = {chunk.chunk_id: rank + 1 for rank, chunk in enumerate(sparse_results)}
        fused_ranks = {chunk.chunk_id: rank + 1 for rank, chunk in enumerate(fused)}
        
        # For each chunk in both lists, verify fused rank ≤ max(dense_rank, sparse_rank)
        for chunk_id in set(dense_ranks.keys()) & set(sparse_ranks.keys()):
            worst_individual_rank = max(dense_ranks[chunk_id], sparse_ranks[chunk_id])
            fused_rank = fused_ranks[chunk_id]
            assert fused_rank <= worst_individual_rank, \
                f"Chunk {chunk_id}: fused rank {fused_rank} worse than worst individual rank {worst_individual_rank}"
    
    def test_rrf_fusion_with_empty_dense(self, retriever_with_mocked_chroma):
        """Test RRF fusion when dense results are empty."""
        sparse_results = [
            ScoredChunk(chunk_id=1, chunk_text="chunk 1", score=10.0),
            ScoredChunk(chunk_id=2, chunk_text="chunk 2", score=8.0),
        ]
        
        fused = retriever_with_mocked_chroma.rrf_fusion([], sparse_results, k=60)
        
        assert len(fused) == 2
        assert all(chunk.chunk_id in [1, 2] for chunk in fused)
    
    def test_rrf_fusion_with_empty_sparse(self, retriever_with_mocked_chroma):
        """Test RRF fusion when sparse results are empty."""
        dense_results = [
            ScoredChunk(chunk_id=1, chunk_text="chunk 1", score=0.9),
            ScoredChunk(chunk_id=2, chunk_text="chunk 2", score=0.8),
        ]
        
        fused = retriever_with_mocked_chroma.rrf_fusion(dense_results, [], k=60)
        
        assert len(fused) == 2
        assert all(chunk.chunk_id in [1, 2] for chunk in fused)


class TestRetrieve:
    """Tests for main retrieve method."""
    
    def test_retrieve_returns_minimum_5_chunks(self, retriever_with_mocked_chroma):
        """
        Test that retrieve always returns at least 5 chunks.
        
        **Validates: Requirements 3**
        """
        # Mock dense search to return 3 chunks
        retriever_with_mocked_chroma.dense_search = Mock(return_value=[
            ScoredChunk(chunk_id=1, chunk_text="chunk 1", score=0.9),
            ScoredChunk(chunk_id=2, chunk_text="chunk 2", score=0.8),
            ScoredChunk(chunk_id=3, chunk_text="chunk 3", score=0.7),
        ])
        
        # Mock sparse search to return 3 chunks
        retriever_with_mocked_chroma.sparse_search = Mock(return_value=[
            ScoredChunk(chunk_id=4, chunk_text="chunk 4", score=10.0),
            ScoredChunk(chunk_id=5, chunk_text="chunk 5", score=8.0),
            ScoredChunk(chunk_id=6, chunk_text="chunk 6", score=6.0),
        ])
        
        # Request only 3 chunks, but should get at least 5
        results = retriever_with_mocked_chroma.retrieve("test query", top_k=3)
        
        assert len(results) >= 5
    
    def test_retrieve_fallback_to_sparse_only(self, retriever_with_mocked_chroma):
        """Test that retrieve falls back to sparse-only when ChromaDB unavailable."""
        # Mock dense search to return empty (simulating ChromaDB unavailable)
        retriever_with_mocked_chroma.dense_search = Mock(return_value=[])
        
        # Mock sparse search to return results
        sparse_results = [
            ScoredChunk(chunk_id=i, chunk_text=f"chunk {i}", score=10.0 - i)
            for i in range(1, 8)
        ]
        retriever_with_mocked_chroma.sparse_search = Mock(return_value=sparse_results)
        
        results = retriever_with_mocked_chroma.retrieve("test query", top_k=5)
        
        assert len(results) >= 5
        assert all(chunk.chunk_id in range(1, 8) for chunk in results)
    
    def test_retrieve_fallback_to_dense_only(self, retriever_with_mocked_chroma):
        """Test that retrieve falls back to dense-only when BM25 unavailable."""
        # Mock dense search to return results
        dense_results = [
            ScoredChunk(chunk_id=i, chunk_text=f"chunk {i}", score=0.9 - i * 0.1)
            for i in range(1, 8)
        ]
        retriever_with_mocked_chroma.dense_search = Mock(return_value=dense_results)
        
        # Mock sparse search to return empty (simulating BM25 unavailable)
        retriever_with_mocked_chroma.sparse_search = Mock(return_value=[])
        
        results = retriever_with_mocked_chroma.retrieve("test query", top_k=5)
        
        assert len(results) >= 5
        assert all(chunk.chunk_id in range(1, 8) for chunk in results)
    
    def test_retrieve_returns_empty_when_both_fail(self, retriever_with_mocked_chroma):
        """Test that retrieve returns empty list when both dense and sparse fail."""
        retriever_with_mocked_chroma.dense_search = Mock(return_value=[])
        retriever_with_mocked_chroma.sparse_search = Mock(return_value=[])
        
        results = retriever_with_mocked_chroma.retrieve("test query", top_k=5)
        
        assert results == []


# ============================================================================
# Property-Based Tests
# ============================================================================

class TestRRFProperties:
    """Property-based tests for RRF fusion."""
    
    @given(
        dense_count=st.integers(min_value=1, max_value=20),
        sparse_count=st.integers(min_value=1, max_value=20),
        overlap_count=st.integers(min_value=0, max_value=10)
    )
    @hypothesis_settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_rrf_rank_property(self, dense_count, sparse_count, overlap_count, retriever_with_mocked_chroma):
        """
        Property test: For any query, RRF rank of a chunk must be ≥ min(dense_rank, sparse_rank).
        
        **Validates: Requirements 3**
        
        This is the core property of RRF fusion - a chunk that appears in both
        dense and sparse results should never be ranked worse in the fused results
        than its best individual rank.
        """
        # Ensure overlap doesn't exceed either list size
        overlap_count = min(overlap_count, dense_count, sparse_count)
        
        # Generate dense results
        dense_results = [
            ScoredChunk(chunk_id=i, chunk_text=f"chunk {i}", score=1.0 - i * 0.01)
            for i in range(1, dense_count + 1)
        ]
        
        # Generate sparse results with some overlap
        sparse_chunk_ids = list(range(1, overlap_count + 1)) + \
                          list(range(dense_count + 1, dense_count + sparse_count - overlap_count + 1))
        sparse_results = [
            ScoredChunk(chunk_id=cid, chunk_text=f"chunk {cid}", score=20.0 - i)
            for i, cid in enumerate(sparse_chunk_ids)
        ]
        
        # Perform RRF fusion
        fused = retriever_with_mocked_chroma.rrf_fusion(dense_results, sparse_results, k=60)
        
        # Build rank maps
        dense_ranks = {chunk.chunk_id: rank + 1 for rank, chunk in enumerate(dense_results)}
        sparse_ranks = {chunk.chunk_id: rank + 1 for rank, chunk in enumerate(sparse_results)}
        fused_ranks = {chunk.chunk_id: rank + 1 for rank, chunk in enumerate(fused)}
        
        # Verify property: for chunks in both lists, fused_rank ≤ min(dense_rank, sparse_rank)
        overlapping_chunks = set(dense_ranks.keys()) & set(sparse_ranks.keys())
        for chunk_id in overlapping_chunks:
            best_individual_rank = min(dense_ranks[chunk_id], sparse_ranks[chunk_id])
            fused_rank = fused_ranks[chunk_id]
            assert fused_rank <= best_individual_rank, \
                f"Chunk {chunk_id}: fused rank {fused_rank} worse than best individual rank {best_individual_rank}"
