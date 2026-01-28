"""MCP Server for NC Soccer - exposes soccer prediction and analysis tools."""

import os
from datetime import datetime
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Lazy initialization for K8s deployment
_mcp_server: Optional[FastMCP] = None


def get_config():
    """Load config - imported lazily to avoid circular imports."""
    from .cli import load_config
    return load_config()


def get_mcp_server() -> FastMCP:
    """Get or create the MCP server instance."""
    global _mcp_server
    if _mcp_server is not None:
        return _mcp_server

    host = os.getenv("FASTMCP_HOST", "127.0.0.1")
    port = int(os.getenv("FASTMCP_PORT", "8000"))

    _mcp_server = FastMCP(
        name="ncsoccer",
        host=host,
        port=port,
    )

    # Register all tools
    _register_tools(_mcp_server)

    return _mcp_server


def _register_tools(mcp: FastMCP):
    """Register all MCP tools."""

    @mcp.tool()
    def predict(
        opponent: str,
        league: Optional[str] = None,
        window: int = 365,
    ) -> dict:
        """Predict game outcome against an opponent using transitive analysis.

        Compares how Key West FC and the opponent perform against shared opponents
        to predict the likely outcome of a matchup.

        Args:
            opponent: Name of the opponent team (e.g., "Purple Crew", "BDE")
            league: Optional league filter (tuesday, friday, sunday)
            window: Time window in days for analysis (default: 365)

        Returns:
            Prediction result with outcome, confidence, advantage score,
            head-to-head history, and shared opponent analysis.
        """
        from .analysis import TransitiveAnalyzer
        from .all_games_store import AllGamesStore

        config = get_config()
        team_name = config.teams[0].name if config.teams else "Key West FC"

        # Check if we have data
        all_store = AllGamesStore(config)
        stats = all_store.get_stats()

        if stats["games_count"] == 0:
            return {
                "error": "No facility games in database for transitive analysis.",
                "hint": "Run 'soccer sync --all-games --from-s3 --year 2025' first.",
            }

        analyzer = TransitiveAnalyzer(
            config=config,
            our_team=team_name,
            time_window_days=window,
        )

        prediction = analyzer.predict_outcome(
            opponent=opponent,
            league_name=league,
        )

        # Format head-to-head games
        h2h_games = []
        if prediction.head_to_head and prediction.head_to_head.games:
            our_lower = prediction.our_team.lower()
            for game in prediction.head_to_head.games:
                meta = game["metadata"]
                is_home = our_lower in meta["home_team"].lower()
                our_score = meta["home_score"] if is_home else meta["away_score"]
                their_score = meta["away_score"] if is_home else meta["home_score"]
                h2h_games.append({
                    "date": meta["date"],
                    "our_score": our_score,
                    "their_score": their_score,
                    "result": "W" if our_score > their_score else ("L" if our_score < their_score else "T"),
                    "league": meta["league_name"],
                })

        # Format shared opponent comparisons
        comparisons = []
        for comp in prediction.comparisons:
            comparisons.append({
                "opponent": comp.opponent,
                "our_record": comp.our_record.record_str,
                "our_goal_diff": comp.our_record.goal_diff_str,
                "their_record": comp.their_record.record_str,
                "their_goal_diff": comp.their_record.goal_diff_str,
                "advantage": round(comp.advantage_score, 2),
            })

        return {
            "our_team": prediction.our_team,
            "opponent": prediction.opponent,
            "outcome": prediction.outcome,
            "confidence": prediction.confidence,
            "advantage_score": prediction.advantage_score,
            "advantage_bar": prediction.advantage_bar,
            "shared_opponents_count": prediction.shared_opponent_count,
            "league_filter": prediction.league_filter,
            "time_window_days": prediction.time_window_days,
            "head_to_head": {
                "record": prediction.head_to_head.record_str if prediction.head_to_head else None,
                "goal_diff": prediction.head_to_head.goal_diff_str if prediction.head_to_head else None,
                "games": h2h_games,
            } if prediction.head_to_head and prediction.head_to_head.games_played > 0 else None,
            "shared_opponent_analysis": comparisons,
        }

    @mcp.tool()
    def predict_upcoming(
        league: Optional[str] = None,
    ) -> dict:
        """Get predictions for all upcoming games.

        Args:
            league: Optional league filter (tuesday, friday, sunday)

        Returns:
            List of predictions for each upcoming opponent.
        """
        from .analysis import TransitiveAnalyzer
        from .all_games_store import AllGamesStore

        config = get_config()
        team_name = config.teams[0].name if config.teams else "Key West FC"

        all_store = AllGamesStore(config)
        stats = all_store.get_stats()

        if stats["games_count"] == 0:
            return {
                "error": "No facility games in database.",
                "hint": "Run 'soccer sync --all-games --from-s3 --year 2025' first.",
            }

        analyzer = TransitiveAnalyzer(
            config=config,
            our_team=team_name,
        )

        predictions = analyzer.predict_upcoming(league_name=league)

        results = []
        for pred in predictions:
            results.append({
                "opponent": pred.opponent,
                "outcome": pred.outcome,
                "confidence": pred.confidence,
                "advantage_score": pred.advantage_score,
                "shared_opponents": pred.shared_opponent_count,
            })

        return {
            "team": team_name,
            "league_filter": league,
            "predictions": results,
        }

    @mcp.tool()
    def upcoming_games() -> dict:
        """Get upcoming games across all leagues.

        Returns:
            List of upcoming games with date, opponent, time, field, and league.
        """
        from .storage import GameStore

        config = get_config()
        team_name = config.teams[0].name if config.teams else "Key West FC"
        store = GameStore(config)

        games_data = store.get_all_games(is_played=False)
        now = datetime.now()

        upcoming = []
        for g in games_data:
            meta = g["metadata"]
            game_date = datetime.strptime(meta["date"], "%Y-%m-%d")
            if game_date > now:
                upcoming.append({
                    "date": meta["date"],
                    "opponent": meta["opponent"],
                    "is_home": meta["is_home"],
                    "league": meta["league_day"],
                    "league_name": meta["league_name"],
                    "field": meta["field"] if meta["field"] else None,
                })

        # Sort by date
        upcoming.sort(key=lambda x: x["date"])

        return {
            "team": team_name,
            "upcoming_games": upcoming,
            "count": len(upcoming),
        }

    @mcp.tool()
    def recent_results(limit: int = 10) -> dict:
        """Get recent game results.

        Args:
            limit: Maximum number of results to return (default: 10)

        Returns:
            List of recent game results with scores and outcomes.
        """
        from .storage import GameStore

        config = get_config()
        team_name = config.teams[0].name if config.teams else "Key West FC"
        store = GameStore(config)

        games_data = store.get_all_games(is_played=True)

        results = []
        for g in games_data:
            meta = g["metadata"]
            results.append({
                "date": meta["date"],
                "opponent": meta["opponent"],
                "is_home": meta["is_home"],
                "our_score": meta["our_score"],
                "their_score": meta["their_score"],
                "result": meta["result"],
                "goal_diff": meta["goal_diff"],
                "league": meta["league_day"],
            })

        # Sort by date descending and limit
        results.sort(key=lambda x: x["date"], reverse=True)
        results = results[:limit]

        return {
            "team": team_name,
            "results": results,
            "count": len(results),
        }

    @mcp.tool()
    def query_games(
        query_text: Optional[str] = None,
        result: Optional[str] = None,
        league: Optional[str] = None,
        opponent: Optional[str] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        limit: int = 10,
    ) -> dict:
        """Search games with semantic query and/or filters.

        Args:
            query_text: Semantic search query (e.g., "close games", "big wins")
            result: Filter by result (win, loss, tie, pending)
            league: Filter by league day (tuesday, friday, sunday)
            opponent: Filter by opponent name (partial match)
            after: Filter games after date (YYYY-MM-DD)
            before: Filter games before date (YYYY-MM-DD)
            limit: Maximum results (default: 10)

        Returns:
            List of matching games with metadata.
        """
        from .storage import GameStore

        config = get_config()
        store = GameStore(config)

        stats = store.get_stats()
        if stats["games_count"] == 0:
            return {
                "error": "No games in database.",
                "hint": "Run 'soccer sync' first.",
            }

        results = store.query_games(
            query_text=query_text,
            result=result,
            league=league,
            opponent=opponent,
            after=after,
            before=before,
            limit=limit,
        )

        games = []
        for r in results:
            meta = r["metadata"]
            game = {
                "date": meta["date"],
                "opponent": meta["opponent"],
                "is_home": meta["is_home"],
                "result": meta["result"],
                "our_score": meta["our_score"] if meta["our_score"] >= 0 else None,
                "their_score": meta["their_score"] if meta["their_score"] >= 0 else None,
                "league": meta["league_day"],
            }
            if "distance" in r:
                game["relevance"] = round(max(0, 100 - (r["distance"] * 50)), 1)
            games.append(game)

        return {
            "query": query_text,
            "filters": {
                "result": result,
                "league": league,
                "opponent": opponent,
                "after": after,
                "before": before,
            },
            "games": games,
            "count": len(games),
        }

    @mcp.tool()
    def standings(league: Optional[str] = None) -> dict:
        """Get league standings.

        Args:
            league: League day filter (tuesday, friday, sunday) or None for all

        Returns:
            Standings for each league with team rankings.
        """
        from .storage import GameStore

        config = get_config()
        store = GameStore(config)

        stats = store.get_stats()
        if stats["standings_count"] == 0:
            return {
                "error": "No standings in database.",
                "hint": "Run 'soccer sync' first.",
            }

        if league:
            league_names = []
            for lg in config.all_leagues:
                if lg.day.lower() == league.lower():
                    league_names.append(lg.name)
        else:
            league_names = [lg.name for lg in config.all_leagues]

        all_standings = {}
        for league_name in league_names:
            standings_data = store.get_latest_standings(league_name)
            if standings_data:
                teams = []
                for s in standings_data:
                    meta = s["metadata"]
                    teams.append({
                        "rank": meta["rank"],
                        "team": meta["team_name"],
                        "games_played": meta["games_played"],
                        "wins": meta["wins"],
                        "losses": meta["losses"],
                        "ties": meta["ties"],
                        "goal_diff": meta["goal_diff"],
                        "points": meta["points"],
                        "is_our_team": meta["is_our_team"],
                    })
                all_standings[league_name] = teams

        return {
            "standings": all_standings,
            "leagues_count": len(all_standings),
        }

    @mcp.tool()
    def database_status() -> dict:
        """Get database statistics.

        Returns:
            Stats about stored games, standings, and all-games collection.
        """
        from .storage import GameStore
        from .all_games_store import AllGamesStore

        config = get_config()
        store = GameStore(config)
        stats = store.get_stats()

        all_store = AllGamesStore(config)
        all_stats = all_store.get_stats()

        return {
            "key_west_games": {
                "games_count": stats["games_count"],
                "standings_count": stats["standings_count"],
                "earliest_game": stats["earliest_game"],
                "latest_game": stats["latest_game"],
                "last_sync": stats["last_sync"],
            },
            "all_facility_games": {
                "games_count": all_stats["games_count"],
                "teams_count": all_stats["teams_count"],
                "leagues_count": all_stats["leagues_count"],
                "earliest_game": all_stats["earliest_game"],
                "latest_game": all_stats["latest_game"],
            },
            "db_path": stats["db_path"],
        }

    @mcp.tool()
    def sync_from_s3(
        year: Optional[int] = None,
        all_games: bool = False,
    ) -> dict:
        """Sync games from S3 bucket.

        Args:
            year: Specific year to sync (e.g., 2025). If None, syncs recent year.
            all_games: If True, syncs ALL facility games for predictions.
                      If False, syncs only Key West FC games.

        Returns:
            Sync results with counts of added/updated games.
        """
        from .s3_sync import iter_s3_games, iter_all_s3_games, list_s3_years
        from .storage import GameStore
        from .all_games_store import AllGamesStore

        config = get_config()
        team_name = config.teams[0].name if config.teams else "Key West FC"

        # Get available years
        try:
            available_years = list_s3_years()
        except Exception as e:
            return {"error": f"Failed to connect to S3: {e}"}

        if not available_years:
            return {"error": "No data found in S3 bucket"}

        # Default to most recent year
        sync_year = year or max(available_years)

        if sync_year not in available_years:
            return {
                "error": f"Year {sync_year} not available",
                "available_years": available_years,
            }

        if all_games:
            # Sync all facility games
            store = AllGamesStore(config)
            games_by_year = {}
            teams_seen = set()

            for game, _ in iter_all_s3_games(year=sync_year):
                yr = game.date.year
                if yr not in games_by_year:
                    games_by_year[yr] = []
                games_by_year[yr].append(game)
                teams_seen.add(game.home_team)
                teams_seen.add(game.away_team)

            total_added = 0
            total_updated = 0
            for yr, games in games_by_year.items():
                added, updated = store.add_games(games)
                total_added += added
                total_updated += updated

            return {
                "mode": "all_games",
                "year": sync_year,
                "games_added": total_added,
                "games_updated": total_updated,
                "total_games": total_added + total_updated,
                "teams_found": len(teams_seen),
            }
        else:
            # Sync Key West games only
            store = GameStore(config)
            games_by_year = {}

            for game, _ in iter_s3_games(team_name=team_name, year=sync_year):
                yr = game.date.year
                if yr not in games_by_year:
                    games_by_year[yr] = []
                games_by_year[yr].append(game)

            total_added = 0
            total_updated = 0
            for yr, games in games_by_year.items():
                added, updated = store.add_games(games, team_name)
                total_added += added
                total_updated += updated

            return {
                "mode": "team_games",
                "team": team_name,
                "year": sync_year,
                "games_added": total_added,
                "games_updated": total_updated,
                "total_games": total_added + total_updated,
            }


def main():
    """Entry point for the MCP server."""
    mcp_server = get_mcp_server()
    transport = os.getenv("MCP_TRANSPORT", "stdio")

    if transport in ("streamable-http", "http"):
        mcp_server.run(transport="streamable-http")
    else:
        mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
