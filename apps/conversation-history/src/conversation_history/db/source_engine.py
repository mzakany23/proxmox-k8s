"""Lazy-loaded database engine for source database (agent-progress)."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config import settings

# Module-level engine, lazily initialized
_source_engine = None
_source_session_factory = None


def get_source_engine():
    """Get or create source database engine.

    Returns:
        AsyncEngine for the source database.

    Raises:
        ValueError: If source database is not configured.
    """
    global _source_engine
    if _source_engine is None:
        if not settings.has_source_database:
            raise ValueError(
                "Source database not configured. "
                "Set SOURCE_DATABASE_URL or SOURCE_DATABASE_PASSWORD."
            )
        _source_engine = create_async_engine(
            settings.async_source_database_url,
            pool_size=2,  # Small pool for read-only imports
            max_overflow=3,
            pool_pre_ping=True,
        )
    return _source_engine


def get_source_session_factory():
    """Get or create source session factory.

    Returns:
        async_sessionmaker for the source database.
    """
    global _source_session_factory
    if _source_session_factory is None:
        engine = get_source_engine()
        _source_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _source_session_factory


async def dispose_source_engine():
    """Clean up source engine connections.

    Call this when shutting down the application.
    """
    global _source_engine, _source_session_factory
    if _source_engine:
        await _source_engine.dispose()
        _source_engine = None
        _source_session_factory = None
