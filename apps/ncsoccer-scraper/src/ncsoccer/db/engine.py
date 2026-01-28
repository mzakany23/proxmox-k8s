"""SQLAlchemy engine and session factory for NC Soccer."""

from contextlib import contextmanager
from functools import lru_cache
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_database_settings
from .models import Base


@lru_cache
def get_engine():
    """Get cached SQLAlchemy engine."""
    settings = get_database_settings()
    return create_engine(
        settings.url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


def get_session_factory():
    """Get session factory."""
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get a database session context manager."""
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Initialize the database schema.

    Creates all tables and enables pgvector extension.
    """
    engine = get_engine()

    # Enable pgvector extension
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    # Create all tables
    Base.metadata.create_all(engine)


def check_db_connection() -> bool:
    """Check if database connection is working."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_db_stats() -> dict:
    """Get database statistics."""
    engine = get_engine()

    default_stats = {
        "games_count": 0,
        "standings_count": 0,
        "all_games_count": 0,
        "teams_count": 0,
        "leagues_count": 0,
        "earliest_game": None,
        "latest_game": None,
        "all_games_earliest": None,
        "all_games_latest": None,
    }

    try:
        with engine.connect() as conn:
            # Check if tables exist
            table_check = conn.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name IN ('games', 'standings', 'all_games')
            """)).fetchall()
            existing_tables = {row[0] for row in table_check}

            if not existing_tables:
                return default_stats

            # Get table counts
            games_count = 0
            standings_count = 0
            all_games_count = 0
            games_dates = (None, None)
            all_games_dates = (None, None)
            teams_count = 0
            leagues_count = 0

            if 'games' in existing_tables:
                games_count = conn.execute(
                    text("SELECT COUNT(*) FROM games")
                ).scalar() or 0
                games_dates = conn.execute(
                    text("SELECT MIN(date), MAX(date) FROM games")
                ).fetchone()

            if 'standings' in existing_tables:
                standings_count = conn.execute(
                    text("SELECT COUNT(*) FROM standings")
                ).scalar() or 0

            if 'all_games' in existing_tables:
                all_games_count = conn.execute(
                    text("SELECT COUNT(*) FROM all_games")
                ).scalar() or 0
                all_games_dates = conn.execute(
                    text("SELECT MIN(date), MAX(date) FROM all_games")
                ).fetchone()
                teams_count = conn.execute(
                    text("""
                        SELECT COUNT(DISTINCT team) FROM (
                            SELECT home_team AS team FROM all_games
                            UNION
                            SELECT away_team AS team FROM all_games
                        ) t
                    """)
                ).scalar() or 0
                leagues_count = conn.execute(
                    text("SELECT COUNT(DISTINCT league_name) FROM all_games WHERE league_name IS NOT NULL")
                ).scalar() or 0

            return {
                "games_count": games_count,
                "standings_count": standings_count,
                "all_games_count": all_games_count,
                "teams_count": teams_count,
                "leagues_count": leagues_count,
                "earliest_game": games_dates[0].strftime("%Y-%m-%d") if games_dates and games_dates[0] else None,
                "latest_game": games_dates[1].strftime("%Y-%m-%d") if games_dates and games_dates[1] else None,
                "all_games_earliest": all_games_dates[0].strftime("%Y-%m-%d") if all_games_dates and all_games_dates[0] else None,
                "all_games_latest": all_games_dates[1].strftime("%Y-%m-%d") if all_games_dates and all_games_dates[1] else None,
            }
    except Exception:
        return default_stats
