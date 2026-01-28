"""PostgreSQL storage layer for ALL facility games (used for transitive analysis)."""

from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, or_, text
from sqlalchemy.dialects.postgresql import insert

from .db import get_session, AllGameRecord
from .db.engine import get_db_stats
from .models import RawGame


class AllGamesStore:
    """PostgreSQL-backed storage for all facility games.

    Separate from GameStore to avoid mixing team-specific data with
    facility-wide data used for transitive analysis.

    No embeddings - uses pure SQL for queries.
    """

    def __init__(self, config=None):
        """Initialize the all-games store.

        Args:
            config: Legacy config parameter (ignored, kept for compatibility)
        """
        pass

    def add_games(self, games: list[RawGame]) -> tuple[int, int]:
        """Add or update raw games in the database.

        Returns (added_count, updated_count).
        """
        if not games:
            return 0, 0

        # Deduplicate games by ID
        seen_ids: set[str] = set()
        unique_games = []
        for game in games:
            if game.game_id not in seen_ids:
                seen_ids.add(game.game_id)
                unique_games.append(game)

        added = 0
        updated = 0

        with get_session() as session:
            for game in unique_games:
                values = {
                    "game_id": game.game_id,
                    "date": game.date,
                    "date_ts": int(game.date.timestamp()),
                    "home_team": game.home_team,
                    "away_team": game.away_team,
                    "home_score": game.home_score,
                    "away_score": game.away_score,
                    "league_name": game.league_name,
                    "field": game.field,
                    "is_played": game.is_played,
                    "document": game.to_document(),
                }

                # Check if record exists
                existing = session.execute(
                    select(AllGameRecord).where(AllGameRecord.game_id == game.game_id)
                ).scalar_one_or_none()

                stmt = insert(AllGameRecord).values(**values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["game_id"],
                    set_={
                        "date": stmt.excluded.date,
                        "date_ts": stmt.excluded.date_ts,
                        "home_team": stmt.excluded.home_team,
                        "away_team": stmt.excluded.away_team,
                        "home_score": stmt.excluded.home_score,
                        "away_score": stmt.excluded.away_score,
                        "league_name": stmt.excluded.league_name,
                        "field": stmt.excluded.field,
                        "is_played": stmt.excluded.is_played,
                        "document": stmt.excluded.document,
                    },
                )

                session.execute(stmt)

                if existing:
                    updated += 1
                else:
                    added += 1

        return added, updated

    def get_team_games(
        self,
        team_name: str,
        league_name: Optional[str] = None,
        after: Optional[str] = None,
        is_played: Optional[bool] = None,
    ) -> list[dict]:
        """Get all games for a team (as home or away).

        Args:
            team_name: Team name to search for (case-insensitive partial match)
            league_name: Optional league filter (partial match)
            after: Filter games after this date (YYYY-MM-DD)
            is_played: Filter by whether game has been played

        Returns:
            List of game dicts with id, document, metadata
        """
        team_lower = team_name.lower()

        with get_session() as session:
            stmt = select(AllGameRecord).where(
                or_(
                    func.lower(AllGameRecord.home_team).contains(team_lower),
                    func.lower(AllGameRecord.away_team).contains(team_lower),
                )
            )

            if is_played is not None:
                stmt = stmt.where(AllGameRecord.is_played == is_played)

            if after:
                after_ts = int(datetime.strptime(after, "%Y-%m-%d").timestamp())
                stmt = stmt.where(AllGameRecord.date_ts >= after_ts)

            if league_name:
                league_lower = league_name.lower()
                stmt = stmt.where(
                    func.lower(AllGameRecord.league_name).contains(league_lower)
                )

            stmt = stmt.order_by(AllGameRecord.date.desc())
            records = session.execute(stmt).scalars().all()

            return [
                {
                    "id": record.game_id,
                    "document": record.document,
                    "metadata": record.to_metadata(),
                }
                for record in records
            ]

    def get_opponents_for_team(
        self,
        team_name: str,
        league_name: Optional[str] = None,
        after: Optional[str] = None,
    ) -> list[str]:
        """Get list of all opponents a team has played against.

        Args:
            team_name: Team name to search for
            league_name: Optional league filter
            after: Filter games after this date (YYYY-MM-DD)

        Returns:
            List of unique opponent team names
        """
        games = self.get_team_games(
            team_name=team_name,
            league_name=league_name,
            after=after,
            is_played=True,
        )

        team_lower = team_name.lower()
        opponents = set()

        for game in games:
            meta = game["metadata"]
            if team_lower in meta["home_team"].lower():
                opponents.add(meta["away_team"])
            else:
                opponents.add(meta["home_team"])

        return sorted(opponents)

    def get_head_to_head(
        self,
        team1: str,
        team2: str,
        league_name: Optional[str] = None,
        after: Optional[str] = None,
    ) -> list[dict]:
        """Get all games between two teams.

        Args:
            team1: First team name
            team2: Second team name
            league_name: Optional league filter
            after: Filter games after this date

        Returns:
            List of game dicts where both teams played each other
        """
        team1_lower = team1.lower()
        team2_lower = team2.lower()

        with get_session() as session:
            # Games where team1 is home and team2 is away, or vice versa
            stmt = select(AllGameRecord).where(
                or_(
                    (func.lower(AllGameRecord.home_team).contains(team1_lower) &
                     func.lower(AllGameRecord.away_team).contains(team2_lower)),
                    (func.lower(AllGameRecord.home_team).contains(team2_lower) &
                     func.lower(AllGameRecord.away_team).contains(team1_lower)),
                )
            ).where(AllGameRecord.is_played == True)

            if after:
                after_ts = int(datetime.strptime(after, "%Y-%m-%d").timestamp())
                stmt = stmt.where(AllGameRecord.date_ts >= after_ts)

            if league_name:
                league_lower = league_name.lower()
                stmt = stmt.where(
                    func.lower(AllGameRecord.league_name).contains(league_lower)
                )

            stmt = stmt.order_by(AllGameRecord.date.desc())
            records = session.execute(stmt).scalars().all()

            return [
                {
                    "id": record.game_id,
                    "document": record.document,
                    "metadata": record.to_metadata(),
                }
                for record in records
            ]

    def get_stats(self) -> dict:
        """Get database statistics for all games collection."""
        try:
            stats = get_db_stats()
            return {
                "games_count": stats["all_games_count"],
                "teams_count": stats["teams_count"],
                "leagues_count": stats["leagues_count"],
                "earliest_game": stats["all_games_earliest"],
                "latest_game": stats["all_games_latest"],
                "db_path": "PostgreSQL",
            }
        except Exception:
            return {
                "games_count": 0,
                "teams_count": 0,
                "leagues_count": 0,
                "earliest_game": None,
                "latest_game": None,
                "db_path": "PostgreSQL (not connected)",
            }

    def clear(self) -> None:
        """Clear all data from the all_games table."""
        with get_session() as session:
            session.execute(text("TRUNCATE TABLE all_games CASCADE"))

    def metadata_to_raw_game(self, metadata: dict) -> RawGame:
        """Convert stored metadata back to a RawGame object."""
        return RawGame(
            date=datetime.strptime(metadata["date"], "%Y-%m-%d"),
            home_team=metadata["home_team"],
            away_team=metadata["away_team"],
            home_score=metadata["home_score"] if metadata["home_score"] >= 0 else None,
            away_score=metadata["away_score"] if metadata["away_score"] >= 0 else None,
            league_name=metadata["league_name"],
            field=metadata["field"] if metadata["field"] else None,
        )
