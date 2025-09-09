"""
Database connection and session management for the Discord Task Reminder Bot.
"""

import logging
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text

from .models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, database_url: str):
        """Initialize the database manager with connection URL."""
        self.database_url = database_url
        self.engine: Optional[object] = None
        self.session_factory: Optional[async_sessionmaker] = None

        # Convert PostgreSQL URL to async version if needed
        if database_url.startswith("postgresql://"):
            self.database_url = database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        elif database_url.startswith("postgres://"):
            self.database_url = database_url.replace(
                "postgres://", "postgresql+asyncpg://", 1
            )

    async def initialize(self) -> None:
        """Initialize the database engine and create tables."""
        try:
            # Create async engine
            self.engine = create_async_engine(
                self.database_url,
                echo=False,  # Set to True for SQL debugging
                poolclass=NullPool,  # Disable connection pooling for simplicity
                pool_pre_ping=True,  # Verify connections before use
            )

            # Create session factory
            self.session_factory = async_sessionmaker(
                bind=self.engine, class_=AsyncSession, expire_on_commit=False
            )

            # Test connection
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            logger.info("Database connection established successfully")

            # Create tables
            await self.create_tables()

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def create_tables(self) -> None:
        """Create all database tables."""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise

    async def close(self) -> None:
        """Close the database connection."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session with automatic cleanup."""
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def health_check(self) -> bool:
        """Check if the database connection is healthy."""
        try:
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database manager instance
db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    if db_manager is None:
        raise RuntimeError("Database manager not initialized")
    return db_manager


def set_db_manager(manager: DatabaseManager) -> None:
    """Set the global database manager instance."""
    global db_manager
    db_manager = manager
