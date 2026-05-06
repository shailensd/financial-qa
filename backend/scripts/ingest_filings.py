#!/usr/bin/env python3
"""
SEC Filing Ingestion Script

Processes all downloaded SEC filings through the DocumentProcessor pipeline:
parse → chunk → embed → persist to PostgreSQL + ChromaDB
"""

import asyncio
import re
from pathlib import Path
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.ml.document_processor import DocumentProcessor
from app.database import Base


# Data directory
DATA_DIR = Path("data/raw")

# Company ticker to full name mapping
COMPANY_NAMES = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc.",
    "AMZN": "Amazon.com Inc.",
    "TSLA": "Tesla Inc.",
}


def parse_filename(filename: str) -> dict:
    """
    Extract metadata from filename.
    
    Expected format: {TICKER}_{FILING_TYPE}_{FILING_DATE}.{ext}
    Example: AAPL_10-K_2024-11-01.html
    
    Args:
        filename: Name of the filing file
        
    Returns:
        Dictionary with ticker, filing_type, filing_date, extension
    """
    # Remove extension
    name_without_ext = filename.rsplit('.', 1)[0]
    extension = filename.rsplit('.', 1)[1] if '.' in filename else ''
    
    # Split by underscore
    parts = name_without_ext.split('_')
    
    if len(parts) != 3:
        raise ValueError(f"Invalid filename format: {filename}")
    
    ticker, filing_type, filing_date = parts
    
    return {
        "ticker": ticker,
        "filing_type": filing_type,
        "filing_date": filing_date,
        "extension": extension
    }


async def ingest_filing(
    processor: DocumentProcessor,
    db: AsyncSession,
    file_path: Path,
    ticker: str,
    filing_type: str,
    filing_date: str
) -> int:
    """
    Ingest a single filing through the DocumentProcessor.
    
    Args:
        processor: DocumentProcessor instance
        db: Database session
        file_path: Path to filing file
        ticker: Stock ticker
        filing_type: "10-K" or "10-Q"
        filing_date: Filing date string (YYYY-MM-DD)
        
    Returns:
        Number of chunks ingested
    """
    company_name = COMPANY_NAMES.get(ticker, ticker)
    
    # Extract fiscal year from filing date
    fiscal_year = int(filing_date.split('-')[0])
    
    # Construct source URL (SEC EDGAR)
    source_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type={filing_type}&dateb=&owner=exclude&count=100"
    
    print(f"  Ingesting {file_path.name}...")
    
    try:
        num_chunks = await processor.ingest(
            file_path=str(file_path),
            db=db,
            company=company_name,
            filing_type=filing_type,
            fiscal_year=fiscal_year,
            filing_date=filing_date,
            source_url=source_url,
            metadata={"ticker": ticker, "filename": file_path.name}
        )
        
        print(f"    ✓ Ingested {num_chunks} chunks")
        return num_chunks
    
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return 0


async def ingest_all_filings():
    """
    Main function to ingest all downloaded filings.
    """
    print("=" * 80)
    print("SEC Filing Ingestion")
    print("=" * 80)
    print(f"Data directory: {DATA_DIR.absolute()}")
    print(f"Database: {settings.database_url}")
    print(f"ChromaDB: {settings.chroma_persist_dir}")
    print("=" * 80)
    print()
    
    # Initialize database engine with proper driver conversion
    database_url = settings.database_url
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(database_url, echo=False)
    
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Initialize DocumentProcessor
    processor = DocumentProcessor()
    
    # Collect all filing files
    filing_files = []
    for ticker_dir in DATA_DIR.iterdir():
        if ticker_dir.is_dir():
            for file_path in ticker_dir.iterdir():
                if file_path.is_file() and file_path.suffix in ['.html', '.htm', '.txt']:
                    filing_files.append(file_path)
    
    filing_files.sort()  # Process in consistent order
    
    print(f"Found {len(filing_files)} filing files to ingest\n")
    
    total_chunks = 0
    total_success = 0
    total_failed = 0
    
    # Process each filing
    for file_path in filing_files:
        try:
            # Parse filename to extract metadata
            metadata = parse_filename(file_path.name)
            ticker = metadata["ticker"]
            filing_type = metadata["filing_type"]
            filing_date = metadata["filing_date"]
            
            # Create new database session for each filing
            async with async_session() as db:
                num_chunks = await ingest_filing(
                    processor=processor,
                    db=db,
                    file_path=file_path,
                    ticker=ticker,
                    filing_type=filing_type,
                    filing_date=filing_date
                )
                
                if num_chunks > 0:
                    total_chunks += num_chunks
                    total_success += 1
                else:
                    total_failed += 1
        
        except Exception as e:
            print(f"  ✗ Failed to process {file_path.name}: {e}")
            total_failed += 1
    
    print(f"\n{'=' * 80}")
    print("Ingestion Summary")
    print(f"{'=' * 80}")
    print(f"Total filings processed: {len(filing_files)}")
    print(f"Successful ingestions: {total_success}")
    print(f"Failed ingestions: {total_failed}")
    print(f"Total chunks created: {total_chunks}")
    print(f"Average chunks per filing: {total_chunks / total_success if total_success > 0 else 0:.1f}")
    print("=" * 80)
    
    # Close engine
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(ingest_all_filings())
