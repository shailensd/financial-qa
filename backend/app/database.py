"""
Database configuration and session management for FinDoc Intelligence.

This module provides SQLAlchemy async engine setup, session management,
and FastAPI dependency for database access.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator

from app.config import settings


# Create async engine
# Convert postgresql:// to postgresql+asyncpg:// if needed
database_url = settings.database_url
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif database_url.startswith("sqlite"):
    # SQLite for development/testing
    pass
elif not database_url.startswith("postgresql+asyncpg://"):
    # Ensure we're using asyncpg driver for PostgreSQL
    if "://" in database_url:
        raise ValueError(
            f"Unsupported database URL scheme. Expected postgresql://, postgresql+asyncpg://, or sqlite+aiosqlite://, "
            f"got: {database_url.split('://')[0]}://"
        )

engine = create_async_engine(
    database_url,
    echo=False,  # Set to True for SQL query logging during development
    future=True,
    pool_pre_ping=True,  # Verify connections before using them
    connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
)

# Create async session factory
SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for ORM models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database session management.
    
    Yields an async database session and ensures proper cleanup.
    
    Usage:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            # Use db session here
            pass
    
    Yields:
        AsyncSession: Database session for the request
    """
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
