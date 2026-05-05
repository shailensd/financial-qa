"""
Hybrid retrieval system for FinDoc Intelligence.

This module implements a hybrid retrieval approach combining:
1. Dense retrieval: Semantic search using ChromaDB with all-MiniLM-L6-v2 embeddings
2. Sparse retrieval: Keyword matching using BM25Okapi
3. Reciprocal Rank Fusion (RRF): Merges dense and sparse results

The system provides fallback to sparse-only retrieval if ChromaDB is unavailable.
"""

from typing import List, Optional
from dataclasses import dataclass
import logging

import chromadb
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models import Chunk


logger = logging.getLogger(__name__)


@dataclass
class ScoredChunk:
    """
    Represents a chunk with relevance score.
    
    Attributes:
        chunk_id: Database ID of the chunk
        chunk_text: Text content of the chunk
        score: Relevance score (higher is better)
        section_label: Section identifier
        page_number: Page number in source document
        company: Company name
        filing_type: Type of filing (10-K, 10-Q)
    """
    chunk_id: int
    chunk_text: str
    score: float
    section_label: Optional[str] = None
    page_number: Optional[int] = None
    company: Optional[str] = None
    filing_type: Optional[str] = None


class HybridRetriever:
    """
    Hybrid retrieval system combining dense and sparse search with RRF fusion.
    
    The retriever:
    1. Performs dense semantic search via ChromaDB (cosine similarity)
    2. Performs sparse keyword search via BM25Okapi
    3. Fuses results using Reciprocal Rank Fusion (RRF)
    4. Falls back to sparse-only if ChromaDB is unavailable
    """
    
    def __init__(self, db_session_factory):
        """
        Initialize the hybrid retriever.
        
        Args:
            db_session_factory: Async session factory for database access
        """
        self.db_session_factory = db_session_factory
        
        # Initialize embedding model for dense retrieval
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize ChromaDB client for dense retrieval
        self.chroma_available = True
        try:
            self.chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
            self.collection = self.chroma_client.get_or_create_collection(
                name="document_chunks",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB initialized successfully")
        except Exception as e:
            logger.warning(f"ChromaDB unavailable, falling back to sparse-only retrieval: {e}")
            self.chroma_available = False
            self.chroma_client = None
            self.collection = None
        
        # BM25 index will be built at startup
        self.bm25_index: Optional[BM25Okapi] = None
        self.bm25_chunk_ids: List[int] = []
        self.bm25_chunks: List[Chunk] = []
    
    async def build_bm25_index(self):
        """
        Build BM25 index over all chunk texts at startup.
        
        This method should be called once during application initialization.
        It loads all chunks from the database and builds the BM25 index.
        """
        async with self.db_session_factory() as db:
            # Load all chunks from database
            stmt = select(Chunk)
            result = await db.execute(stmt)
            chunks = list(result.scalars().all())
            
            if not chunks:
                logger.warning("No chunks found in database for BM25 index")
                self.bm25_index = None
                self.bm25_chunk_ids = []
                self.bm25_chunks = []
                return
            
            # Store chunks and their IDs
            self.bm25_chunks = chunks
            self.bm25_chunk_ids = [chunk.id for chunk in chunks]
            
            # Tokenize chunk texts (simple whitespace tokenization)
            tokenized_corpus = [chunk.chunk_text.lower().split() for chunk in chunks]
            
            # Build BM25 index
            self.bm25_index = BM25Okapi(tokenized_corpus)
            
            logger.info(f"BM25 index built with {len(chunks)} chunks")
    
    def dense_search(self, query: str, top_k: int = 10) -> List[ScoredChunk]:
        """
        Perform dense semantic search using ChromaDB.
        
        Embeds the query using all-MiniLM-L6-v2 and queries ChromaDB
        with cosine similarity.
        
        Args:
            query: Search query text
            top_k: Number of top results to return
        
        Returns:
            List of ScoredChunk objects ranked by cosine similarity
        """
        if not self.chroma_available or self.collection is None:
            logger.debug("ChromaDB unavailable, skipping dense search")
            return []
        
        try:
            # Embed query
            query_embedding = self.embedding_model.encode(
                query,
                show_progress_bar=False,
                convert_to_numpy=True
            ).tolist()
            
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Convert to ScoredChunk objects
            scored_chunks = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    chunk_id = int(results['ids'][0][i])
                    chunk_text = results['documents'][0][i]
                    # ChromaDB returns distances, convert to similarity score
                    # For cosine distance: similarity = 1 - distance
                    distance = results['distances'][0][i]
                    score = 1.0 - distance
                    
                    metadata = results['metadatas'][0][i]
                    
                    scored_chunks.append(ScoredChunk(
                        chunk_id=chunk_id,
                        chunk_text=chunk_text,
                        score=score,
                        section_label=metadata.get('section_label'),
                        page_number=int(metadata['page_number']) if metadata.get('page_number') else None,
                        company=metadata.get('company'),
                        filing_type=metadata.get('filing_type')
                    ))
            
            return scored_chunks
        
        except Exception as e:
            logger.error(f"Dense search failed: {e}")
            return []
    
    def sparse_search(self, query: str, top_k: int = 10) -> List[ScoredChunk]:
        """
        Perform sparse keyword search using BM25Okapi.
        
        Uses the BM25 index built at startup to find relevant chunks
        based on keyword matching.
        
        Args:
            query: Search query text
            top_k: Number of top results to return
        
        Returns:
            List of ScoredChunk objects ranked by BM25 score
        """
        if self.bm25_index is None or not self.bm25_chunks:
            logger.debug("BM25 index not available, skipping sparse search")
            return []
        
        try:
            # Tokenize query
            tokenized_query = query.lower().split()
            
            # Get BM25 scores for all documents
            scores = self.bm25_index.get_scores(tokenized_query)
            
            # Get top-k indices
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
            
            # Convert to ScoredChunk objects
            scored_chunks = []
            for idx in top_indices:
                chunk = self.bm25_chunks[idx]
                score = float(scores[idx])
                
                scored_chunks.append(ScoredChunk(
                    chunk_id=chunk.id,
                    chunk_text=chunk.chunk_text,
                    score=score,
                    section_label=chunk.section_label,
                    page_number=chunk.page_number,
                    company=None,  # Not available in Chunk model directly
                    filing_type=None
                ))
            
            return scored_chunks
        
        except Exception as e:
            logger.error(f"Sparse search failed: {e}")
            return []
    
    def rrf_fusion(
        self,
        dense_results: List[ScoredChunk],
        sparse_results: List[ScoredChunk],
        k: int = 60
    ) -> List[ScoredChunk]:
        """
        Fuse dense and sparse results using Reciprocal Rank Fusion (RRF).
        
        RRF formula: score(d) = Σ 1/(k + rank(d))
        where k=60 is the RRF constant and rank is 1-indexed.
        
        Args:
            dense_results: Results from dense search
            sparse_results: Results from sparse search
            k: RRF constant (default: 60)
        
        Returns:
            Merged and ranked list of ScoredChunk objects
        """
        # Build rank maps for each retrieval method
        dense_ranks = {chunk.chunk_id: rank + 1 for rank, chunk in enumerate(dense_results)}
        sparse_ranks = {chunk.chunk_id: rank + 1 for rank, chunk in enumerate(sparse_results)}
        
        # Collect all unique chunk IDs
        all_chunk_ids = set(dense_ranks.keys()) | set(sparse_ranks.keys())
        
        # Build chunk_id to chunk object mapping
        chunk_map = {}
        for chunk in dense_results:
            chunk_map[chunk.chunk_id] = chunk
        for chunk in sparse_results:
            if chunk.chunk_id not in chunk_map:
                chunk_map[chunk.chunk_id] = chunk
        
        # Calculate RRF scores
        rrf_scores = {}
        for chunk_id in all_chunk_ids:
            score = 0.0
            
            # Add contribution from dense retrieval
            if chunk_id in dense_ranks:
                score += 1.0 / (k + dense_ranks[chunk_id])
            
            # Add contribution from sparse retrieval
            if chunk_id in sparse_ranks:
                score += 1.0 / (k + sparse_ranks[chunk_id])
            
            rrf_scores[chunk_id] = score
        
        # Sort by RRF score (descending)
        sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)
        
        # Build final result list with updated scores
        fused_results = []
        for chunk_id in sorted_chunk_ids:
            chunk = chunk_map[chunk_id]
            # Create new ScoredChunk with RRF score
            fused_chunk = ScoredChunk(
                chunk_id=chunk.chunk_id,
                chunk_text=chunk.chunk_text,
                score=rrf_scores[chunk_id],
                section_label=chunk.section_label,
                page_number=chunk.page_number,
                company=chunk.company,
                filing_type=chunk.filing_type
            )
            fused_results.append(fused_chunk)
        
        return fused_results
    
    def retrieve(self, query: str, top_k: int = 10) -> List[ScoredChunk]:
        """
        Retrieve relevant chunks using hybrid retrieval.
        
        Calls dense + sparse search, fuses via RRF, and returns top_k chunks.
        Falls back to sparse-only if ChromaDB is unavailable.
        
        Args:
            query: Search query text
            top_k: Number of top results to return (minimum 5)
        
        Returns:
            List of ScoredChunk objects ranked by RRF score
        """
        # Ensure we return at least 5 chunks as per requirements
        effective_top_k = max(top_k, 5)
        
        # Perform dense search
        dense_results = self.dense_search(query, top_k=effective_top_k)
        
        # Perform sparse search
        sparse_results = self.sparse_search(query, top_k=effective_top_k)
        
        # Fallback to sparse-only if ChromaDB unavailable
        if not dense_results and sparse_results:
            logger.info("Using sparse-only retrieval (ChromaDB unavailable)")
            return sparse_results[:effective_top_k]
        
        # Fallback to dense-only if BM25 unavailable
        if dense_results and not sparse_results:
            logger.info("Using dense-only retrieval (BM25 unavailable)")
            return dense_results[:effective_top_k]
        
        # If both failed, return empty list
        if not dense_results and not sparse_results:
            logger.warning("Both dense and sparse retrieval failed")
            return []
        
        # Fuse results using RRF
        fused_results = self.rrf_fusion(dense_results, sparse_results, k=60)
        
        # Return top_k results
        return fused_results[:effective_top_k]
