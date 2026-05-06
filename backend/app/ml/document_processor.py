"""
Document processor for FinDoc Intelligence.

This module handles parsing, chunking, embedding, and ingestion of SEC filings
(10-K and 10-Q documents) into the PostgreSQL database and ChromaDB vector store.
"""

import re
from typing import List, Optional
from dataclasses import dataclass
from pathlib import Path

import chromadb
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.crud import create_document, create_chunk


@dataclass
class RawSection:
    """
    Represents a parsed section from a document.
    
    Attributes:
        section_label: Section identifier (e.g., "Item 7. MD&A")
        text: Raw text content of the section
        page_number: Estimated page number
    """
    section_label: str
    text: str
    page_number: int


@dataclass
class ChunkData:
    """
    Represents a chunk with metadata before database persistence.
    
    Attributes:
        chunk_text: Text content of the chunk
        section_label: Section identifier from parent section
        chunk_index: Position within document
        page_number: Estimated page number
    """
    chunk_text: str
    section_label: str
    chunk_index: int
    page_number: int


class DocumentProcessor:
    """
    Processes SEC filings through parse → chunk → embed → ingest pipeline.
    
    The processor:
    1. Parses plain-text 10-K/10-Q files by section headers
    2. Chunks sections using sliding window (800 words, 200-word overlap)
    3. Generates embeddings using sentence-transformers all-MiniLM-L6-v2
    4. Persists chunks to PostgreSQL and embeddings to ChromaDB
    """
    
    def __init__(self):
        """Initialize the document processor with embedding model and ChromaDB client."""
        # Load sentence-transformers model for embeddings
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        
        # Get or create collection for document embeddings
        self.collection = self.chroma_client.get_or_create_collection(
            name="document_chunks",
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
    
    def parse(self, file_path: str) -> List[RawSection]:
        r"""
        Parse a SEC filing (HTML or plain-text) into sections.
        
        For HTML files, cleans HTML tags using BeautifulSoup before processing.
        Splits document by section headers matching "Item \d+" pattern.
        Estimates page numbers based on character offset (assuming ~3000 chars/page).
        
        Args:
            file_path: Path to HTML or plain-text 10-K or 10-Q file
        
        Returns:
            List of RawSection objects with section_label, text, and page_number
        
        Raises:
            FileNotFoundError: If file_path does not exist
            IOError: If file cannot be read
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")
        
        # Read entire document
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            raw_content = f.read()
        
        # Clean HTML if file is HTML format
        if file_path.lower().endswith(('.html', '.htm')):
            soup = BeautifulSoup(raw_content, 'lxml')
            # Extract text, preserving some structure with spaces
            content = soup.get_text(separator=' ', strip=True)
        else:
            content = raw_content
        
        # Split by section headers (e.g., "Item 1.", "Item 7.", "Item 1A.")
        # Pattern matches: "Item" followed by digits and optional letter, followed by period or colon
        section_pattern = re.compile(r'(Item\s+\d+[A-Za-z]?[\.:])', re.IGNORECASE)
        
        sections = []
        matches = list(section_pattern.finditer(content))
        
        if not matches:
            # No section headers found - treat entire document as one section
            sections.append(RawSection(
                section_label="Full Document",
                text=content,
                page_number=1
            ))
            return sections
        
        # Process each section
        for i, match in enumerate(matches):
            section_label = match.group(1).strip()
            start_pos = match.start()
            
            # Determine end position (start of next section or end of document)
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(content)
            
            # Extract section text
            section_text = content[start_pos:end_pos].strip()
            
            # Estimate page number (assuming ~3000 characters per page)
            page_number = (start_pos // 3000) + 1
            
            sections.append(RawSection(
                section_label=section_label,
                text=section_text,
                page_number=page_number
            ))
        
        return sections
    
    def chunk(self, sections: List[RawSection]) -> List[ChunkData]:
        """
        Chunk sections using sliding window approach.
        
        Uses 800-word chunks with 200-word overlap. Preserves section_label
        and page_number metadata for each chunk.
        
        Args:
            sections: List of RawSection objects from parse()
        
        Returns:
            List of ChunkData objects with chunk_text, section_label, chunk_index, page_number
        """
        chunks = []
        global_chunk_index = 0
        
        for section in sections:
            # Split section text into words
            words = section.text.split()
            
            if not words:
                continue
            
            # Sliding window parameters
            chunk_size = settings.chunk_size
            overlap = settings.chunk_overlap
            step = chunk_size - overlap
            
            # Generate chunks with sliding window
            start = 0
            while start < len(words):
                # Extract chunk words
                end = min(start + chunk_size, len(words))
                chunk_words = words[start:end]
                
                # Join words back into text
                chunk_text = ' '.join(chunk_words)
                
                # Create chunk data
                chunks.append(ChunkData(
                    chunk_text=chunk_text,
                    section_label=section.section_label,
                    chunk_index=global_chunk_index,
                    page_number=section.page_number
                ))
                
                global_chunk_index += 1
                
                # Move window forward
                start += step
                
                # If we've reached the end, break
                if end >= len(words):
                    break
        
        return chunks
    
    def embed(self, chunks: List[ChunkData]) -> List[List[float]]:
        """
        Generate embeddings for chunks using all-MiniLM-L6-v2.
        
        Produces 384-dimensional dense vectors for semantic search.
        
        Args:
            chunks: List of ChunkData objects
        
        Returns:
            List of embedding vectors (each is a list of 384 floats)
        """
        if not chunks:
            return []
        
        # Extract chunk texts
        chunk_texts = [chunk.chunk_text for chunk in chunks]
        
        # Generate embeddings (returns numpy array)
        embeddings = self.embedding_model.encode(
            chunk_texts,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        
        # Convert to list of lists for ChromaDB compatibility
        return embeddings.tolist()
    
    async def ingest(
        self,
        file_path: str,
        db: AsyncSession,
        company: str,
        filing_type: str,
        fiscal_year: int,
        filing_date: str,
        source_url: str,
        metadata: Optional[dict] = None
    ) -> int:
        """
        Orchestrate full ingestion pipeline: parse → chunk → embed → persist.
        
        Persists chunks to PostgreSQL and embeddings to ChromaDB with metadata.
        
        Args:
            file_path: Path to plain-text SEC filing
            db: Database session
            company: Company name
            filing_type: "10-K" or "10-Q"
            fiscal_year: Fiscal year
            filing_date: Filing date (ISO format string)
            source_url: URL to source document
            metadata: Optional additional metadata
        
        Returns:
            Number of chunks ingested
        
        Raises:
            FileNotFoundError: If file_path does not exist
            ValueError: If database operations fail
        """
        from datetime import datetime
        
        # Step 1: Parse document into sections
        sections = self.parse(file_path)
        
        # Step 2: Chunk sections
        chunks = self.chunk(sections)
        
        if not chunks:
            raise ValueError(f"No chunks generated from document: {file_path}")
        
        # Step 3: Generate embeddings
        embeddings = self.embed(chunks)
        
        # Step 4: Persist to PostgreSQL
        # Create document record
        filing_date_obj = datetime.fromisoformat(filing_date) if isinstance(filing_date, str) else filing_date
        document = await create_document(
            db=db,
            company=company,
            filing_type=filing_type,
            fiscal_year=fiscal_year,
            filing_date=filing_date_obj,
            source_url=source_url,
            metadata_json=metadata
        )
        
        # Create chunk records and collect IDs for ChromaDB
        chunk_ids = []
        for chunk_data in chunks:
            chunk_record = await create_chunk(
                db=db,
                document_id=document.id,
                chunk_text=chunk_data.chunk_text,
                chunk_index=chunk_data.chunk_index,
                section_label=chunk_data.section_label,
                page_number=chunk_data.page_number
            )
            chunk_ids.append(str(chunk_record.id))
        
        # Commit to database
        await db.commit()
        
        # Step 5: Persist embeddings to ChromaDB
        # Prepare metadata for ChromaDB
        chroma_metadatas = [
            {
                "chunk_id": chunk_id,
                "document_id": str(document.id),
                "company": company,
                "filing_type": filing_type,
                "fiscal_year": str(fiscal_year),
                "section_label": chunk.section_label,
                "page_number": str(chunk.page_number),
                "chunk_index": str(chunk.chunk_index)
            }
            for chunk_id, chunk in zip(chunk_ids, chunks)
        ]
        
        # Add to ChromaDB collection
        self.collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            metadatas=chroma_metadatas,
            documents=[chunk.chunk_text for chunk in chunks]
        )
        
        return len(chunks)
