"""League discovery for finding historical Key West FC leagues."""

import re
from pathlib import Path
from typing import Optional

import yaml

from .models import HistoricalLeague, extract_year_from_league_name
from .scraper import Scraper


class LeagueDiscovery:
    """Discovers historical leagues where Key West FC has participated."""

    def __init__(self, scraper: Scraper, target_team: str = "Key West"):
        """Initialize the discovery service.

        Args:
            scraper: Configured Scraper instance
            target_team: Team name to search for (partial match)
        """
        self.scraper = scraper
        self.target_team = target_team

    def discover_leagues(self, progress_callback=None) -> list[HistoricalLeague]:
        """Discover all leagues where the target team has participated.

        Args:
            progress_callback: Optional callback(league_name, found_team_id)
                               to report progress

        Returns:
            List of HistoricalLeague objects.
        """
        discovered = []

        # Fetch all leagues from the index
        leagues = self.scraper.fetch_league_index()

        for league_info in leagues:
            league_id = league_info["id"]
            league_name = league_info["name"]
            league_url = league_info["url"]

            # Try to find our team in this league
            team_id = self.scraper.find_team_in_league(
                league_id, league_url, self.target_team
            )

            if progress_callback:
                progress_callback(league_name, team_id)

            if team_id:
                # Extract year and day from league name
                year = extract_year_from_league_name(league_name)
                day = self.scraper.detect_league_day(league_name)

                if year:  # Only include if we can determine the year
                    historical = HistoricalLeague(
                        id=league_id,
                        name=league_name,
                        day=day,
                        team_id=team_id,
                        year=year,
                        is_active=False,
                    )
                    discovered.append(historical)

        # Sort by year (descending) then by day
        day_order = {
            "Sunday": 0, "Monday": 1, "Tuesday": 2, "Wednesday": 3,
            "Thursday": 4, "Friday": 5, "Saturday": 6, "Unknown": 7
        }
        discovered.sort(
            key=lambda l: (-l.year, day_order.get(l.day, 7), l.name)
        )

        return discovered


def get_historical_leagues_path() -> Path:
    """Get the path to the historical leagues file."""
    return Path.home() / ".ncsoccer" / "historical_leagues.yaml"


def load_historical_leagues() -> list[HistoricalLeague]:
    """Load historical leagues from the saved YAML file.

    Returns:
        List of HistoricalLeague objects, or empty list if file doesn't exist.
    """
    path = get_historical_leagues_path()
    if not path.exists():
        return []

    try:
        with open(path) as f:
            data = yaml.safe_load(f)

        if not data or "leagues" not in data:
            return []

        return [HistoricalLeague(**league) for league in data["leagues"]]
    except Exception:
        return []


def save_historical_leagues(leagues: list[HistoricalLeague]) -> Path:
    """Save historical leagues to YAML file.

    Args:
        leagues: List of HistoricalLeague objects to save

    Returns:
        Path to the saved file.
    """
    path = get_historical_leagues_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "leagues": [league.model_dump() for league in leagues]
    }

    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    return path


def merge_historical_leagues(
    existing: list[HistoricalLeague],
    discovered: list[HistoricalLeague]
) -> list[HistoricalLeague]:
    """Merge discovered leagues with existing ones, avoiding duplicates.

    Args:
        existing: Previously saved leagues
        discovered: Newly discovered leagues

    Returns:
        Merged list with no duplicates (by league ID).
    """
    # Create a dict keyed by league ID
    merged = {league.id: league for league in existing}

    # Add or update with discovered leagues
    for league in discovered:
        merged[league.id] = league

    # Sort and return
    day_order = {
        "Sunday": 0, "Monday": 1, "Tuesday": 2, "Wednesday": 3,
        "Thursday": 4, "Friday": 5, "Saturday": 6, "Unknown": 7
    }
    result = list(merged.values())
    result.sort(key=lambda l: (-l.year, day_order.get(l.day, 7), l.name))

    return result
