"""Data models for NC Soccer scraper."""

import hashlib
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class GameResult(str, Enum):
    """Game result enum."""

    WIN = "win"
    LOSS = "loss"
    TIE = "tie"
    PENDING = "pending"


class RawGame(BaseModel):
    """Simplified game model for all facility games (not team-specific).

    Used for storing ALL games from the facility for transitive analysis.
    """

    date: datetime
    home_team: str
    away_team: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    league_name: str = ""
    field: Optional[str] = None

    @property
    def is_played(self) -> bool:
        """Check if the game has been played."""
        return self.home_score is not None and self.away_score is not None

    @property
    def game_id(self) -> str:
        """Generate a unique ID for this game."""
        normalized_home = re.sub(r"[^a-z0-9]", "", self.home_team.lower())
        normalized_away = re.sub(r"[^a-z0-9]", "", self.away_team.lower())
        date_str = self.date.strftime("%Y%m%d")
        league_slug = re.sub(r"[^a-z0-9]", "", self.league_name.lower())
        raw_id = f"{league_slug}_{date_str}_{normalized_home}_{normalized_away}"
        return f"raw_{hashlib.md5(raw_id.encode()).hexdigest()[:12]}"

    def to_document(self) -> str:
        """Generate a human-readable document for semantic search."""
        if self.is_played:
            result_str = f"Score: {self.home_score}-{self.away_score}"
        else:
            result_str = "Game not yet played"

        return (
            f"{self.home_team} vs {self.away_team} on {self.date.strftime('%Y-%m-%d')} "
            f"in {self.league_name}. {result_str}."
        )

    def to_metadata(self) -> dict[str, Any]:
        """Generate metadata dict for ChromaDB filtering."""
        return {
            "date": self.date.strftime("%Y-%m-%d"),
            "date_ts": int(self.date.timestamp()),
            "home_team": self.home_team,
            "away_team": self.away_team,
            "league_name": self.league_name,
            "home_score": self.home_score if self.home_score is not None else -1,
            "away_score": self.away_score if self.away_score is not None else -1,
            "field": self.field or "",
            "is_played": self.is_played,
        }


class Game(BaseModel):
    """Represents a single game."""

    date: datetime
    opponent: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    is_home: bool = True
    field: Optional[str] = None
    league_name: str = ""
    league_day: str = ""

    @property
    def is_played(self) -> bool:
        """Check if the game has been played."""
        return self.home_score is not None and self.away_score is not None

    @property
    def result(self) -> GameResult:
        """Get the game result."""
        if not self.is_played:
            return GameResult.PENDING
        if self.is_home:
            if self.home_score > self.away_score:
                return GameResult.WIN
            elif self.home_score < self.away_score:
                return GameResult.LOSS
            return GameResult.TIE
        else:
            if self.away_score > self.home_score:
                return GameResult.WIN
            elif self.away_score < self.home_score:
                return GameResult.LOSS
            return GameResult.TIE

    @property
    def score_display(self) -> str:
        """Get score display string."""
        if not self.is_played:
            return "-"
        if self.is_home:
            return f"{self.home_score}-{self.away_score}"
        return f"{self.away_score}-{self.home_score}"

    @property
    def time_display(self) -> str:
        """Get time display string."""
        return self.date.strftime("%-I:%M %p")

    @property
    def date_display(self) -> str:
        """Get date display string."""
        return self.date.strftime("%a %b %-d")

    @property
    def goal_diff(self) -> Optional[int]:
        """Calculate goal difference from our perspective."""
        if not self.is_played:
            return None
        our_score = self.home_score if self.is_home else self.away_score
        their_score = self.away_score if self.is_home else self.home_score
        return our_score - their_score

    @property
    def game_id(self) -> str:
        """Generate a unique ID for this game."""
        # Normalize opponent name for consistent IDs
        normalized_opponent = re.sub(r"[^a-z0-9]", "", self.opponent.lower())
        date_str = self.date.strftime("%Y%m%d")
        league_slug = re.sub(r"[^a-z0-9]", "", self.league_name.lower())
        raw_id = f"{league_slug}_{date_str}_{normalized_opponent}"
        return f"game_{hashlib.md5(raw_id.encode()).hexdigest()[:12]}"

    def to_document(self, team_name: str = "Key West FC") -> str:
        """Generate a human-readable document for semantic search."""
        location = "Home game" if self.is_home else "Away game"
        field_str = f" at {self.field}" if self.field else ""

        if self.is_played:
            our_score = self.home_score if self.is_home else self.away_score
            their_score = self.away_score if self.is_home else self.home_score
            result_str = f"Result: {self.result.value.title()} {our_score}-{their_score}"
            margin = abs(self.goal_diff)
            if margin >= 5:
                result_str += f". Blowout win by {margin} goals" if self.result == GameResult.WIN else f". Heavy loss by {margin} goals"
            elif margin <= 2 and margin > 0:
                result_str += ". Close game"
            elif margin == 0:
                result_str += ". Draw"
        else:
            result_str = "Game not yet played"

        return (
            f"{team_name} vs {self.opponent} on {self.date_display} "
            f"in {self.league_name}. {location}{field_str}. {result_str}."
        )

    def to_metadata(self) -> dict[str, Any]:
        """Generate metadata dict for ChromaDB filtering."""
        our_score = self.home_score if self.is_home else self.away_score
        their_score = self.away_score if self.is_home else self.home_score

        return {
            "date": self.date.strftime("%Y-%m-%d"),
            "date_ts": int(self.date.timestamp()),  # For numeric comparison
            "opponent": self.opponent,
            "league_name": self.league_name,
            "league_day": self.league_day,
            "is_home": self.is_home,
            "home_score": self.home_score if self.home_score is not None else -1,
            "away_score": self.away_score if self.away_score is not None else -1,
            "our_score": our_score if our_score is not None else -1,
            "their_score": their_score if their_score is not None else -1,
            "result": self.result.value,
            "goal_diff": self.goal_diff if self.goal_diff is not None else 0,
            "field": self.field or "",
            "is_played": self.is_played,
        }


class Standing(BaseModel):
    """Represents a team's standing in a league."""

    rank: int
    team_name: str
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    ties: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0
    is_our_team: bool = False

    @property
    def goal_diff(self) -> int:
        """Calculate goal difference."""
        return self.goals_for - self.goals_against

    @property
    def goal_diff_display(self) -> str:
        """Get goal difference display string."""
        diff = self.goal_diff
        if diff > 0:
            return f"+{diff}"
        return str(diff)

    @property
    def record(self) -> str:
        """Get W-L-T record string."""
        if self.ties > 0:
            return f"{self.wins}-{self.losses}-{self.ties}"
        return f"{self.wins}-{self.losses}"

    league_name: str = ""

    def standing_id(self, snapshot_date: str) -> str:
        """Generate a unique ID for this standing snapshot."""
        normalized_team = re.sub(r"[^a-z0-9]", "", self.team_name.lower())
        league_slug = re.sub(r"[^a-z0-9]", "", self.league_name.lower())
        raw_id = f"{league_slug}_{normalized_team}_{snapshot_date}"
        return f"standing_{hashlib.md5(raw_id.encode()).hexdigest()[:12]}"

    def to_document(self) -> str:
        """Generate a human-readable document for semantic search."""
        ordinal = lambda n: f"{n}{'th' if 11 <= n <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"
        return (
            f"{self.team_name} in {self.league_name} standings: "
            f"{ordinal(self.rank)} place, {self.record}, "
            f"{self.points} points, {self.goal_diff_display} GD"
        )

    def to_metadata(self, snapshot_date: str) -> dict[str, Any]:
        """Generate metadata dict for ChromaDB filtering."""
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
            "snapshot_date": snapshot_date,
        }


def extract_year_from_league_name(name: str) -> int | None:
    """Extract year from league names like 'Mens Open B Indoor session 2 2025'.

    Args:
        name: League name string

    Returns:
        Year as integer if found, None otherwise.
    """
    match = re.search(r'\b(20\d{2})\b', name)
    return int(match.group(1)) if match else None


class League(BaseModel):
    """Represents a league configuration."""

    id: int
    name: str
    day: str
    team_id: int


class HistoricalLeague(BaseModel):
    """Represents a discovered historical league.

    Used for tracking past leagues that Key West FC has participated in.
    """

    id: int
    name: str
    day: str
    team_id: int
    year: int
    is_active: bool = False

    def to_league(self) -> League:
        """Convert to a standard League object for scraping."""
        return League(
            id=self.id,
            name=self.name,
            day=self.day,
            team_id=self.team_id,
        )


class TeamConfig(BaseModel):
    """Team configuration from config file."""

    name: str
    leagues: list[League]


class Config(BaseModel):
    """Root configuration."""

    base_url: str = "https://nc-soccer-hudson.ezleagues.ezfacility.com"
    teams: list[TeamConfig]
    db_path: str = "~/.ncsoccer/data"

    @property
    def db_path_resolved(self) -> Path:
        """Get resolved database path."""
        return Path(self.db_path).expanduser()

    @property
    def all_leagues(self) -> list[League]:
        """Get all leagues across all teams."""
        leagues = []
        for team in self.teams:
            leagues.extend(team.leagues)
        return leagues

    def get_league_by_day(self, day: str) -> Optional[League]:
        """Get league by day name (case-insensitive)."""
        day_lower = day.lower()
        for league in self.all_leagues:
            if league.day.lower() == day_lower:
                return league
        return None
