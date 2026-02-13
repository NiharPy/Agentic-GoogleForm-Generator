# app/core/database.py
"""
Database configuration with proper connection pooling for async operations

FIXED: Handles long-running LLM calls without connection timeouts
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.settings import settings
import logging

logger = logging.getLogger(__name__)

# Create async engine with proper pooling settings
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    
    # Connection pool settings
    pool_size=10,  # Number of connections to maintain
    max_overflow=20,  # Additional connections beyond pool_size
    pool_timeout=30,  # Timeout for getting a connection from pool
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_pre_ping=True,  # Test connections before using them (CRITICAL FIX!)
    
    # Async settings
    connect_args={
        "server_settings": {
            "application_name": "FormsGen",
            "jit": "off"  # Disable JIT for better connection stability
        },
        # Connection timeout settings
        "timeout": 60,  # Connection timeout (60 seconds)
        "command_timeout": 300,  # Command timeout (5 minutes for long LLM calls)
    }
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db():
    """
    Dependency for FastAPI routes
    Provides a database session with automatic cleanup
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database initialized")


async def close_db():
    """Close database connections (call on shutdown)"""
    await engine.dispose()
    logger.info("✅ Database connections closed")