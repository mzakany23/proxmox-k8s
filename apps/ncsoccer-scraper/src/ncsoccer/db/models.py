"""SQLAlchemy ORM models for NC Soccer PostgreSQL database."""

import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    BigInteger,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class GameRecord(Base):
    """ORM model for Key West FC games with embeddings."""

    __tablename__ = "games"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    game_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    opponent: Mapped[str] = mapped_column(String(200), nullable=False)
    home_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    away_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_home: Mapped[bool] = mapped_column(Boolean, default=True)
    field: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    league_name: Mapped[str] = mapped_column(String(200), nullable=False)
    league_day: Mapped[str] = mapped_column(String(50), nullable=False)
    result: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    our_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    their_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    goal_diff: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_played: Mapped[bool] = mapped_column(Boolean, default=False)
    document: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(1536), nullable=True)  # OpenAI ada-002
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_games_embedding", embedding, postgresql_using="ivfflat",
              postgresql_with={"lists": 100},
              postgresql_ops={"embedding": "vector_cosine_ops"}),
        Index("ix_games_league_day", "league_day"),
        Index("ix_games_result", "result"),
        Index("ix_games_date", "date"),
    )

    def to_metadata(self) -> dict:
        """Convert to metadata dict for API responses."""
        return {
            "date": self.date.strftime("%Y-%m-%d"),
            "date_ts": int(self.date.timestamp()),
            "opponent": self.opponent,
            "league_name": self.league_name,
            "league_day": self.league_day,
            "is_home": self.is_home,
            "home_score": self.home_score if self.home_score is not None else -1,
            "away_score": self.away_score if self.away_score is not None else -1,
            "our_score": self.our_score if self.our_score is not None else -1,
            "their_score": self.their_score if self.their_score is not None else -1,
            "result": self.result or "pending",
            "goal_diff": self.goal_diff if self.goal_diff is not None else 0,
            "field": self.field or "",
            "is_played": self.is_played,
        }


class StandingRecord(Base):
    """ORM model for league standings."""

    __tablename__ = "standings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    standing_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    snapshot_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    league_name: Mapped[str] = mapped_column(String(200), nullable=False)
    team_name: Mapped[str] = mapped_column(String(200), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    games_played: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    ties: Mapped[int] = mapped_column(Integer, default=0)
    goals_for: Mapped[int] = mapped_column(Integer, default=0)
    goals_against: Mapped[int] = mapped_column(Integer, default=0)
    goal_diff: Mapped[int] = mapped_column(Integer, default=0)
    points: Mapped[int] = mapped_column(Integer, default=0)
    is_our_team: Mapped[bool] = mapped_column(Boolean, default=False)
    document: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_standings_league", "league_name"),
        Index("ix_standings_snapshot", "snapshot_date"),
    )

    def to_metadata(self) -> dict:
        """Convert to metadata dict for API responses."""
        return {
            "league_name": self.league_name,
            "team_name": self.team_name,
            "rank": self.rank,
            "games_played": self.games_played,
            "wins": self.wins,
            "losses": self.losses,
            "ties": self.ties,
            "points": self.points,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_diff": self.goal_diff,
            "is_our_team": self.is_our_team,
            "snapshot_date": self.snapshot_date.strftime("%Y-%m-%d") if self.snapshot_date else None,
        }


class AllGameRecord(Base):
    """ORM model for all facility games (no embeddings - for transitive analysis)."""

    __tablename__ = "all_games"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    game_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    date_ts: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Unix timestamp
    home_team: Mapped[str] = mapped_column(String(200), nullable=False)
    away_team: Mapped[str] = mapped_column(String(200), nullable=False)
    home_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    away_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    league_name: Mapped[str] = mapped_column(String(200), nullable=False)
    field: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_played: Mapped[bool] = mapped_column(Boolean, default=False)
    document: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_all_games_home_team_lower", func.lower(home_team)),
        Index("ix_all_games_away_team_lower", func.lower(away_team)),
        Index("ix_all_games_date_ts", "date_ts"),
        Index("ix_all_games_league", "league_name"),
    )

    def to_metadata(self) -> dict:
        """Convert to metadata dict for API responses."""
        return {
            "date": self.date.strftime("%Y-%m-%d"),
            "date_ts": self.date_ts,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "league_name": self.league_name,
            "home_score": self.home_score if self.home_score is not None else -1,
            "away_score": self.away_score if self.away_score is not None else -1,
            "field": self.field or "",
            "is_played": self.is_played,
        }
