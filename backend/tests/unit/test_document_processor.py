"""
Unit tests for DocumentProcessor.

Tests verify:
- Parsing of SEC filings by section headers
- Chunking with correct size and overlap
- Metadata preservation (section_label, page_number)
- Embedding generation
- Full ingestion pipeline
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.ml.document_processor import DocumentProcessor, RawSection, ChunkData
from app.config import settings


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_document_text():
    """Sample SEC filing text with section headers."""
    return """
UNITED STATES SECURITIES AND EXCHANGE COMMISSION
Form 10-K Annual Report

Item 1. Business

Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, 
wearables, and accessories worldwide. The Company sells and delivers digital content and 
applications through the iTunes Store, App Store, Mac App Store, TV App Store, and iBooks Store.

Item 1A. Risk Factors

The Company's business, reputation, results of operations, financial condition, and stock price 
can be affected by a number of factors, whether currently known or unknown, including those 
described below. When any one or more of these risks materialize, it can have a material adverse 
effect on the Company's business.

Item 7. Management's Discussion and Analysis

Net sales increased during 2023 compared to 2022 due primarily to higher net sales of iPhone 
and Services. The weakness in foreign currencies relative to the U.S. dollar had an unfavorable 
impact on net sales during 2023.
"""


@pytest.fixture
def temp_document_file(sample_document_text):
    """Create a temporary file with sample document text."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(sample_document_text)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def mock_embedding_model():
    """Mock SentenceTransformer model."""
    with patch('app.ml.document_processor.SentenceTransformer') as mock:
        model_instance = Mock()
        # Return 384-dim embeddings (all-MiniLM-L6-v2 dimension)
        model_instance.encode.return_value = Mock(tolist=lambda: [[0.1] * 384, [0.2] * 384])
        mock.return_value = model_instance
        yield model_instance


@pytest.fixture
def mock_chroma_client():
    """Mock ChromaDB client."""
    with patch('app.ml.document_processor.chromadb.PersistentClient') as mock:
        client_instance = Mock()
        collection_mock = Mock()
        client_instance.get_or_create_collection.return_value = collection_mock
        mock.return_value = client_instance
        yield client_instance, collection_mock


@pytest.fixture
def processor(mock_embedding_model, mock_chroma_client):
    """Create DocumentProcessor instance with mocked dependencies."""
    return DocumentProcessor()


# ============================================================================
# Test parse() method
# ============================================================================

def test_parse_extracts_sections(processor, temp_document_file):
    """Test that parse() correctly identifies and extracts sections."""
    sections = processor.parse(temp_document_file)
    
    # Should find 3 sections: Item 1, Item 1A, Item 7
    assert len(sections) == 3
    
    # Verify section labels
    assert sections[0].section_label == "Item 1."
    assert sections[1].section_label == "Item 1A."
    assert sections[2].section_label == "Item 7."
    
    # Verify text content is extracted
    assert "Apple Inc. designs" in sections[0].text
    assert "Risk Factors" in sections[1].text
    assert "Net sales increased" in sections[2].text


def test_parse_assigns_page_numbers(processor, temp_document_file):
    """Test that parse() estimates page numbers correctly."""
    sections = processor.parse(temp_document_file)
    
    # All sections should have page numbers
    for section in sections:
        assert section.page_number >= 1
        assert isinstance(section.page_number, int)


def test_parse_handles_no_sections(processor):
    """Test that parse() handles documents without section headers."""
    # Create document without Item headers
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("This is a document without section headers.")
        temp_path = f.name
    
    try:
        sections = processor.parse(temp_path)
        
        # Should return one section with full document
        assert len(sections) == 1
        assert sections[0].section_label == "Full Document"
        assert "without section headers" in sections[0].text
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_parse_raises_on_missing_file(processor):
    """Test that parse() raises FileNotFoundError for non-existent files."""
    with pytest.raises(FileNotFoundError):
        processor.parse("/nonexistent/file.txt")


# ============================================================================
# Test chunk() method
# ============================================================================

def test_chunk_creates_correct_size_chunks(processor):
    """Test that chunk() creates chunks of approximately 800 words."""
    # Create a section with exactly 1000 words
    words = ["word"] * 1000
    text = " ".join(words)
    
    sections = [RawSection(
        section_label="Item 1.",
        text=text,
        page_number=1
    )]
    
    chunks = processor.chunk(sections)
    
    # Should create multiple chunks
    assert len(chunks) > 1
    
    # First chunk should have exactly 800 words
    first_chunk_words = chunks[0].chunk_text.split()
    assert len(first_chunk_words) == 800


def test_chunk_applies_overlap(processor):
    """Test that chunk() applies 200-word overlap between chunks."""
    # Create a section with 1200 words
    words = [f"word{i}" for i in range(1200)]
    text = " ".join(words)
    
    sections = [RawSection(
        section_label="Item 1.",
        text=text,
        page_number=1
    )]
    
    chunks = processor.chunk(sections)
    
    # Should have at least 2 chunks
    assert len(chunks) >= 2
    
    # Extract words from first two chunks
    chunk1_words = chunks[0].chunk_text.split()
    chunk2_words = chunks[1].chunk_text.split()
    
    # Verify overlap: last 200 words of chunk1 should match first 200 words of chunk2
    # (accounting for sliding window: chunk2 starts at position 600 = 800 - 200)
    # So chunk1[600:800] should equal chunk2[0:200]
    assert chunk1_words[600:800] == chunk2_words[0:200]


def test_chunk_preserves_metadata(processor):
    """Test that chunk() preserves section_label and page_number."""
    sections = [
        RawSection(
            section_label="Item 7. MD&A",
            text=" ".join(["word"] * 1000),
            page_number=42
        )
    ]
    
    chunks = processor.chunk(sections)
    
    # All chunks should preserve metadata
    for chunk in chunks:
        assert chunk.section_label == "Item 7. MD&A"
        assert chunk.page_number == 42


def test_chunk_assigns_sequential_indices(processor):
    """Test that chunk() assigns sequential chunk_index values."""
    sections = [
        RawSection(
            section_label="Item 1.",
            text=" ".join(["word"] * 1000),
            page_number=1
        ),
        RawSection(
            section_label="Item 2.",
            text=" ".join(["word"] * 1000),
            page_number=5
        )
    ]
    
    chunks = processor.chunk(sections)
    
    # Verify indices are sequential
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i


def test_chunk_handles_empty_sections(processor):
    """Test that chunk() handles empty sections gracefully."""
    sections = [
        RawSection(section_label="Item 1.", text="", page_number=1),
        RawSection(section_label="Item 2.", text="   ", page_number=2),
    ]
    
    chunks = processor.chunk(sections)
    
    # Should return empty list for empty sections
    assert len(chunks) == 0


# ============================================================================
# Test embed() method
# ============================================================================

def test_embed_generates_correct_dimensions(processor, mock_embedding_model):
    """Test that embed() generates 384-dimensional embeddings."""
    chunks = [
        ChunkData(
            chunk_text="Sample text",
            section_label="Item 1.",
            chunk_index=0,
            page_number=1
        )
    ]
    
    # Mock to return proper shape
    mock_embedding_model.encode.return_value = Mock(
        tolist=lambda: [[0.1] * 384]
    )
    
    embeddings = processor.embed(chunks)
    
    # Should return one embedding
    assert len(embeddings) == 1
    
    # Embedding should be 384-dimensional
    assert len(embeddings[0]) == 384


def test_embed_handles_multiple_chunks(processor, mock_embedding_model):
    """Test that embed() processes multiple chunks."""
    chunks = [
        ChunkData(f"Text {i}", "Item 1.", i, 1)
        for i in range(5)
    ]
    
    # Mock to return proper shape
    mock_embedding_model.encode.return_value = Mock(
        tolist=lambda: [[0.1] * 384] * 5
    )
    
    embeddings = processor.embed(chunks)
    
    # Should return 5 embeddings
    assert len(embeddings) == 5
    
    # Verify encode was called with correct texts
    call_args = mock_embedding_model.encode.call_args
    assert len(call_args[0][0]) == 5


def test_embed_handles_empty_list(processor):
    """Test that embed() handles empty chunk list."""
    embeddings = processor.embed([])
    
    assert embeddings == []


# ============================================================================
# Test ingest() method
# ============================================================================

@pytest.mark.asyncio
async def test_ingest_full_pipeline(processor, temp_document_file, mock_chroma_client):
    """Test that ingest() orchestrates full pipeline correctly."""
    # Mock database session with async methods
    mock_db = MagicMock()
    mock_db.commit = MagicMock(return_value=None)
    # Make commit awaitable
    mock_db.commit = lambda: __import__('asyncio').sleep(0)
    
    # Mock document creation
    mock_document = Mock()
    mock_document.id = 123
    
    # Mock chunk creation
    mock_chunks = []
    for i in range(3):
        mock_chunk = Mock()
        mock_chunk.id = 1000 + i
        mock_chunks.append(mock_chunk)
    
    # Create async mock functions
    async def mock_create_document(*args, **kwargs):
        return mock_document
    
    async def mock_create_chunk(*args, **kwargs):
        return mock_chunks.pop(0) if mock_chunks else Mock(id=9999)
    
    with patch('app.ml.document_processor.create_document', side_effect=mock_create_document):
        with patch('app.ml.document_processor.create_chunk', side_effect=mock_create_chunk):
            num_chunks = await processor.ingest(
                file_path=temp_document_file,
                db=mock_db,
                company="Apple Inc.",
                filing_type="10-K",
                fiscal_year=2023,
                filing_date="2023-10-27",
                source_url="https://example.com/filing.txt"
            )
    
    # Should return number of chunks created
    assert num_chunks > 0
    
    # Verify ChromaDB collection.add was called
    _, collection_mock = mock_chroma_client
    collection_mock.add.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_preserves_metadata_in_chromadb(processor, temp_document_file, mock_chroma_client):
    """Test that ingest() includes correct metadata in ChromaDB."""
    # Mock database session with async methods
    mock_db = MagicMock()
    mock_db.commit = lambda: __import__('asyncio').sleep(0)
    
    mock_document = Mock()
    mock_document.id = 456
    
    mock_chunk = Mock()
    mock_chunk.id = 789
    
    # Create async mock functions
    async def mock_create_document(*args, **kwargs):
        return mock_document
    
    async def mock_create_chunk(*args, **kwargs):
        return mock_chunk
    
    with patch('app.ml.document_processor.create_document', side_effect=mock_create_document):
        with patch('app.ml.document_processor.create_chunk', side_effect=mock_create_chunk):
            await processor.ingest(
                file_path=temp_document_file,
                db=mock_db,
                company="Tesla Inc.",
                filing_type="10-Q",
                fiscal_year=2024,
                filing_date="2024-01-15",
                source_url="https://example.com/tesla.txt"
            )
    
    # Get ChromaDB add call arguments
    _, collection_mock = mock_chroma_client
    call_args = collection_mock.add.call_args
    
    # Verify metadata includes required fields
    metadatas = call_args[1]['metadatas']
    assert len(metadatas) > 0
    
    first_metadata = metadatas[0]
    assert first_metadata['company'] == "Tesla Inc."
    assert first_metadata['filing_type'] == "10-Q"
    assert first_metadata['fiscal_year'] == "2024"
    assert 'section_label' in first_metadata
    assert 'page_number' in first_metadata


@pytest.mark.asyncio
async def test_ingest_raises_on_empty_document(processor):
    """Test that ingest() raises ValueError for documents with no chunks."""
    # Create empty document
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("")
        temp_path = f.name
    
    try:
        mock_db = MagicMock()
        
        with pytest.raises(ValueError, match="No chunks generated"):
            await processor.ingest(
                file_path=temp_path,
                db=mock_db,
                company="Test",
                filing_type="10-K",
                fiscal_year=2023,
                filing_date="2023-01-01",
                source_url="https://example.com"
            )
    finally:
        Path(temp_path).unlink(missing_ok=True)


# ============================================================================
# Integration test: parse → chunk → embed
# ============================================================================

def test_full_processing_chain(processor, temp_document_file, mock_embedding_model):
    """Test complete processing chain: parse → chunk → embed."""
    # Parse
    sections = processor.parse(temp_document_file)
    assert len(sections) > 0
    
    # Chunk
    chunks = processor.chunk(sections)
    assert len(chunks) > 0
    
    # Verify chunk size constraints
    for chunk in chunks:
        word_count = len(chunk.chunk_text.split())
        # Should be <= 800 words (last chunk might be smaller)
        assert word_count <= 800
    
    # Mock embeddings
    mock_embedding_model.encode.return_value = Mock(
        tolist=lambda: [[0.1] * 384] * len(chunks)
    )
    
    # Embed
    embeddings = processor.embed(chunks)
    assert len(embeddings) == len(chunks)
    
    # Verify all embeddings are 384-dimensional
    for embedding in embeddings:
        assert len(embedding) == 384
