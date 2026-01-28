"""PostgreSQL + pgvector storage layer for NC Soccer data."""

from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, text
from sqlalchemy.dialects.postgresql import insert

from .db import get_session, GameRecord, StandingRecord, Embedder
from .db.engine import get_db_stats
from .models import Game, Standing


class GameStore:
    """PostgreSQL-backed storage for games and standings with pgvector embeddings."""

    def __init__(self, config=None):
        """Initialize the game store.

        Args:
            config: Legacy config parameter (ignored, kept for compatibility)
        """
        self._embedder: Optional[Embedder] = None

    @property
    def embedder(self) -> Optional[Embedder]:
        """Lazy-load embedder."""
        if self._embedder is None:
            self._embedder = Embedder()
            if not self._embedder.is_available():
                self._embedder = None
        return self._embedder

    def add_games(
        self, games: list[Game], team_name: str = "Key West FC"
    ) -> tuple[int, int]:
        """Add or update games in the database.

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

        # Prepare documents for embedding
        documents = [game.to_document(team_name) for game in unique_games]

        # Generate embeddings if available
        embeddings = None
        if self.embedder:
            try:
                embeddings = self.embedder.embed_batch(documents)
            except Exception:
                # Fall back to no embeddings if API fails
                embeddings = None

        added = 0
        updated = 0

        with get_session() as session:
            for i, game in enumerate(unique_games):
                metadata = game.to_metadata()

                values = {
                    "game_id": game.game_id,
                    "date": game.date,
                    "opponent": game.opponent,
                    "home_score": game.home_score,
                    "away_score": game.away_score,
                    "is_home": game.is_home,
                    "field": game.field,
                    "league_name": game.league_name,
                    "league_day": game.league_day,
                    "result": metadata["result"],
                    "our_score": game.home_score if game.is_home else game.away_score,
                    "their_score": game.away_score if game.is_home else game.home_score,
                    "goal_diff": metadata["goal_diff"],
                    "is_played": game.is_played,
                    "document": documents[i],
                }

                if embeddings and i < len(embeddings):
                    values["embedding"] = embeddings[i]

                # Use PostgreSQL upsert
                stmt = insert(GameRecord).values(**values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["game_id"],
                    set_={
                        "date": stmt.excluded.date,
                        "opponent": stmt.excluded.opponent,
                        "home_score": stmt.excluded.home_score,
                        "away_score": stmt.excluded.away_score,
                        "is_home": stmt.excluded.is_home,
                        "field": stmt.excluded.field,
                        "league_name": stmt.excluded.league_name,
                        "league_day": stmt.excluded.league_day,
                        "result": stmt.excluded.result,
                        "our_score": stmt.excluded.our_score,
                        "their_score": stmt.excluded.their_score,
                        "goal_diff": stmt.excluded.goal_diff,
                        "is_played": stmt.excluded.is_played,
                        "document": stmt.excluded.document,
                        "embedding": stmt.excluded.embedding,
                    },
                )

                # Check if record exists
                existing = session.execute(
                    select(GameRecord).where(GameRecord.game_id == game.game_id)
                ).scalar_one_or_none()

                session.execute(stmt)

                if existing:
                    updated += 1
                else:
                    added += 1

        return added, updated

    def add_standings(
        self, standings: list[Standing], league_name: str
    ) -> tuple[int, int]:
        """Add standings snapshot to the database.

        Returns (added_count, updated_count).
        """
        if not standings:
            return 0, 0

        snapshot_date = datetime.now().date()
        added = 0
        updated = 0

        with get_session() as session:
            for standing in standings:
                standing.league_name = league_name

                values = {
                    "standing_id": standing.standing_id(snapshot_date.strftime("%Y-%m-%d")),
                    "snapshot_date": snapshot_date,
                    "league_name": league_name,
                    "team_name": standing.team_name,
                    "rank": standing.rank,
                    "games_played": standing.games_played,
                    "wins": standing.wins,
                    "losses": standing.losses,
                    "ties": standing.ties,
                    "goals_for": standing.goals_for,
                    "goals_against": standing.goals_against,
                    "goal_diff": standing.goal_diff,
                    "points": standing.points,
                    "is_our_team": standing.is_our_team,
                    "document": standing.to_document(),
                }

                # Check if record exists
                existing = session.execute(
                    select(StandingRecord).where(
                        StandingRecord.standing_id == values["standing_id"]
                    )
                ).scalar_one_or_none()

                stmt = insert(StandingRecord).values(**values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["standing_id"],
                    set_={
                        "rank": stmt.excluded.rank,
                        "games_played": stmt.excluded.games_played,
                        "wins": stmt.excluded.wins,
                        "losses": stmt.excluded.losses,
                        "ties": stmt.excluded.ties,
                        "goals_for": stmt.excluded.goals_for,
                        "goals_against": stmt.excluded.goals_against,
                        "goal_diff": stmt.excluded.goal_diff,
                        "points": stmt.excluded.points,
                        "is_our_team": stmt.excluded.is_our_team,
                        "document": stmt.excluded.document,
                    },
                )

                session.execute(stmt)

                if existing:
                    updated += 1
                else:
                    added += 1

        return added, updated

    def query_games(
        self,
        query_text: Optional[str] = None,
        result: Optional[str] = None,
        league: Optional[str] = None,
        opponent: Optional[str] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        is_played: Optional[bool] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Query games with semantic search and/or filters.

        Args:
            query_text: Semantic search query (e.g., "close games", "big wins")
            result: Filter by result (win/loss/tie/pending)
            league: Filter by league day (e.g., "sunday", "friday")
            opponent: Filter by opponent name (partial match)
            after: Filter games after this date (YYYY-MM-DD)
            before: Filter games before this date (YYYY-MM-DD)
            is_played: Filter by whether game has been played
            limit: Maximum results to return

        Returns:
            List of game dicts with id, document, metadata, and optional distance.
        """
        with get_session() as session:
            # Build base query
            stmt = select(GameRecord)

            # Apply filters
            if result:
                stmt = stmt.where(GameRecord.result == result.lower())

            if league:
                stmt = stmt.where(GameRecord.league_day == league.title())

            if is_played is not None:
                stmt = stmt.where(GameRecord.is_played == is_played)

            if after:
                after_dt = datetime.strptime(after, "%Y-%m-%d")
                stmt = stmt.where(GameRecord.date >= after_dt)

            if before:
                before_dt = datetime.strptime(before, "%Y-%m-%d")
                stmt = stmt.where(GameRecord.date <= before_dt)

            if opponent:
                stmt = stmt.where(
                    func.lower(GameRecord.opponent).contains(opponent.lower())
                )

            # Semantic search with pgvector
            if query_text and self.embedder:
                try:
                    query_embedding = self.embedder.embed(query_text)
                    # Order by cosine distance (smaller is more similar)
                    stmt = stmt.order_by(
                        GameRecord.embedding.cosine_distance(query_embedding)
                    )
                except Exception:
                    # Fall back to date ordering if embedding fails
                    stmt = stmt.order_by(GameRecord.date.desc())
            else:
                # Default to date ordering
                stmt = stmt.order_by(GameRecord.date.desc())

            stmt = stmt.limit(limit)
            records = session.execute(stmt).scalars().all()

            games = []
            for record in records:
                game = {
                    "id": record.game_id,
                    "document": record.document,
                    "metadata": record.to_metadata(),
                }
                games.append(game)

            return games

    def get_all_games(
        self,
        league: Optional[str] = None,
        is_played: Optional[bool] = None,
    ) -> list[dict]:
        """Get all games, optionally filtered by league or played status."""
        with get_session() as session:
            stmt = select(GameRecord)

            if league:
                stmt = stmt.where(GameRecord.league_day == league.title())

            if is_played is not None:
                stmt = stmt.where(GameRecord.is_played == is_played)

            records = session.execute(stmt).scalars().all()

            return [
                {
                    "id": record.game_id,
                    "document": record.document,
                    "metadata": record.to_metadata(),
                }
                for record in records
            ]

    def get_latest_standings(self, league_name: Optional[str] = None) -> list[dict]:
        """Get the latest standings snapshot, optionally filtered by league."""
        with get_session() as session:
            # First, find the latest snapshot date per league
            subq = (
                select(
                    StandingRecord.league_name,
                    func.max(StandingRecord.snapshot_date).label("max_date"),
                )
                .group_by(StandingRecord.league_name)
            )

            if league_name:
                subq = subq.where(StandingRecord.league_name == league_name)

            subq = subq.subquery()

            # Join to get standings from the latest snapshot
            stmt = (
                select(StandingRecord)
                .join(
                    subq,
                    (StandingRecord.league_name == subq.c.league_name) &
                    (StandingRecord.snapshot_date == subq.c.max_date),
                )
                .order_by(StandingRecord.league_name, StandingRecord.rank)
            )

            records = session.execute(stmt).scalars().all()

            return [
                {
                    "id": record.standing_id,
                    "document": record.document,
                    "metadata": record.to_metadata(),
                }
                for record in records
            ]

    def get_stats(self) -> dict:
        """Get database statistics."""
        try:
            stats = get_db_stats()
            return {
                "games_count": stats["games_count"],
                "standings_count": stats["standings_count"],
                "earliest_game": stats["earliest_game"],
                "latest_game": stats["latest_game"],
                "last_sync": None,  # Not tracked in PostgreSQL version
                "db_path": "PostgreSQL",
            }
        except Exception:
            return {
                "games_count": 0,
                "standings_count": 0,
                "earliest_game": None,
                "latest_game": None,
                "last_sync": None,
                "db_path": "PostgreSQL (not connected)",
            }

    def clear(self) -> None:
        """Clear all data from the database."""
        with get_session() as session:
            session.execute(text("TRUNCATE TABLE games CASCADE"))
            session.execute(text("TRUNCATE TABLE standings CASCADE"))

    def metadata_to_game(self, metadata: dict) -> Game:
        """Convert stored metadata back to a Game object."""
        return Game(
            date=datetime.strptime(metadata["date"], "%Y-%m-%d"),
            opponent=metadata["opponent"],
            home_score=metadata["home_score"] if metadata["home_score"] >= 0 else None,
            away_score=metadata["away_score"] if metadata["away_score"] >= 0 else None,
            is_home=metadata["is_home"],
            field=metadata["field"] if metadata["field"] else None,
            league_name=metadata["league_name"],
            league_day=metadata["league_day"],
        )

    def metadata_to_standing(self, metadata: dict) -> Standing:
        """Convert stored metadata back to a Standing object."""
        return Standing(
            rank=metadata["rank"],
            team_name=metadata["team_name"],
            games_played=metadata["games_played"],
            wins=metadata["wins"],
            losses=metadata["losses"],
            ties=metadata["ties"],
            goals_for=metadata.get("goals_for", 0),
            goals_against=metadata.get("goals_against", 0),
            points=metadata["points"],
            is_our_team=metadata["is_our_team"],
            league_name=metadata["league_name"],
        )
