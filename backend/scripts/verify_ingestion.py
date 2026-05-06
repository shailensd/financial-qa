#!/usr/bin/env python3
"""
Verify SEC Filing Ingestion

Queries the database to verify successful ingestion of all filings.
"""

import asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models import Document, Chunk


async def verify_ingestion():
    """
    Verify ingestion by querying database for chunk counts per company and filing type.
    """
    print("=" * 80)
    print("SEC Filing Ingestion Verification")
    print("=" * 80)
    print(f"Database: {settings.database_url}")
    print("=" * 80)
    print()
    
    # Initialize database engine with proper driver conversion
    database_url = settings.database_url
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(database_url, echo=False)
    
    # Create session factory
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as db:
        # Query total documents
        result = await db.execute(select(func.count(Document.id)))
        total_documents = result.scalar()
        
        # Query total chunks
        result = await db.execute(select(func.count(Chunk.id)))
        total_chunks = result.scalar()
        
        print(f"Total Documents: {total_documents}")
        print(f"Total Chunks: {total_chunks}")
        print()
        
        # Query chunks per company
        print("Chunks per Company:")
        print("-" * 80)
        result = await db.execute(
            select(Document.company, func.count(Chunk.id))
            .join(Chunk, Document.id == Chunk.document_id)
            .group_by(Document.company)
            .order_by(Document.company)
        )
        
        for company, count in result:
            print(f"  {company:30s}: {count:5d} chunks")
        
        print()
        
        # Query chunks per filing type
        print("Chunks per Filing Type:")
        print("-" * 80)
        result = await db.execute(
            select(Document.filing_type, func.count(Chunk.id))
            .join(Chunk, Document.id == Chunk.document_id)
            .group_by(Document.filing_type)
            .order_by(Document.filing_type)
        )
        
        for filing_type, count in result:
            print(f"  {filing_type:10s}: {count:5d} chunks")
        
        print()
        
        # Query chunks per company and filing type
        print("Chunks per Company and Filing Type:")
        print("-" * 80)
        result = await db.execute(
            select(Document.company, Document.filing_type, func.count(Chunk.id))
            .join(Chunk, Document.id == Chunk.document_id)
            .group_by(Document.company, Document.filing_type)
            .order_by(Document.company, Document.filing_type)
        )
        
        for company, filing_type, count in result:
            print(f"  {company:30s} {filing_type:10s}: {count:5d} chunks")
        
        print()
        
        # Query chunks per fiscal year
        print("Chunks per Fiscal Year:")
        print("-" * 80)
        result = await db.execute(
            select(Document.fiscal_year, func.count(Chunk.id))
            .join(Chunk, Document.id == Chunk.document_id)
            .group_by(Document.fiscal_year)
            .order_by(Document.fiscal_year)
        )
        
        for fiscal_year, count in result:
            print(f"  {fiscal_year}: {count:5d} chunks")
        
        print()
        
        # Verify all 5 companies have data
        result = await db.execute(
            select(func.count(func.distinct(Document.company)))
        )
        unique_companies = result.scalar()
        
        print("=" * 80)
        print("Verification Summary")
        print("=" * 80)
        print(f"✓ Total documents ingested: {total_documents}")
        print(f"✓ Total chunks created: {total_chunks}")
        print(f"✓ Unique companies: {unique_companies}")
        
        if unique_companies == 5:
            print("✓ All 5 companies have data")
        else:
            print(f"✗ Expected 5 companies, found {unique_companies}")
        
        if total_chunks >= 3000:
            print(f"✓ Chunk count meets target (>= 3000)")
        else:
            print(f"⚠ Chunk count below target: {total_chunks} < 3000")
        
        print("=" * 80)
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(verify_ingestion())
