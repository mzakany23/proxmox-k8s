"""S3 data sync for NC Soccer historical games.

Imports game data from the ncsh-app-data S3 bucket which contains
all games scraped via the print.aspx date-based approach.
"""

import json
import re
from datetime import datetime
from typing import Iterator, Optional

import boto3
from botocore.exceptions import ClientError

from .models import Game, RawGame

# S3 bucket configuration
S3_BUCKET = "ncsh-app-data"
S3_PREFIX = "v2/processed/json"


def detect_league_day(league_name: str) -> str:
    """Detect the day of week from a league name.

    Args:
        league_name: Full league name from S3 data

    Returns:
        Day of week (e.g., "Sunday", "Friday", "Tuesday")
    """
    league_lower = league_name.lower()

    day_patterns = [
        (r"\bsunday\b", "Sunday"),
        (r"\bfriday\b", "Friday"),
        (r"\btuesday\b", "Tuesday"),
        (r"\bmonday\b", "Monday"),
        (r"\bwednesday\b", "Wednesday"),
        (r"\bthursday\b", "Thursday"),
        (r"\bsaturday\b", "Saturday"),
    ]

    for pattern, day in day_patterns:
        if re.search(pattern, league_lower):
            return day

    return "Unknown"


def parse_score(score_str: str) -> tuple[Optional[int], Optional[int]]:
    """Parse a score string like '7 - 6' into (home, away) integers.

    Args:
        score_str: Score string from S3 data

    Returns:
        Tuple of (home_score, away_score), or (None, None) if not played
    """
    if not score_str or score_str.strip() in ("", "-", "vs"):
        return None, None

    # Handle "7 - 6" format
    match = re.match(r"(\d+)\s*-\s*(\d+)", score_str.strip())
    if match:
        return int(match.group(1)), int(match.group(2))

    return None, None


def s3_game_to_game(s3_game: dict, team_name: str = "Key West FC") -> Optional[Game]:
    """Convert an S3 game record to our Game model.

    Args:
        s3_game: Game dict from S3 JSONL file
        team_name: The team to filter for (partial match)

    Returns:
        Game object if this is a game for our team, None otherwise
    """
    home_team = s3_game.get("home_team", "")
    away_team = s3_game.get("away_team", "")

    # Check if our team is in this game
    team_lower = team_name.lower()
    is_home = team_lower in home_team.lower()
    is_away = team_lower in away_team.lower()

    if not is_home and not is_away:
        return None

    # Determine opponent
    if is_home:
        opponent = away_team
    else:
        opponent = home_team

    # Parse score
    home_score, away_score = parse_score(s3_game.get("score", ""))

    # Parse date
    game_date_str = s3_game.get("game_date", "")
    try:
        game_date = datetime.strptime(game_date_str, "%Y-%m-%d")
    except ValueError:
        return None

    # Get league info
    league_name = s3_game.get("league_name", "")
    league_day = detect_league_day(league_name)

    return Game(
        date=game_date,
        opponent=opponent,
        home_score=home_score,
        away_score=away_score,
        is_home=is_home,
        field=s3_game.get("field"),
        league_name=league_name,
        league_day=league_day,
    )


def list_s3_years() -> list[int]:
    """List available years in the S3 bucket.

    Returns:
        List of years with data (e.g., [2020, 2021, 2022, ...])
    """
    s3 = boto3.client("s3")

    try:
        result = s3.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=f"{S3_PREFIX}/",
            Delimiter="/",
        )

        years = []
        for prefix in result.get("CommonPrefixes", []):
            # Extract year from "v2/processed/json/year=2024/"
            match = re.search(r"year=(\d{4})", prefix.get("Prefix", ""))
            if match:
                years.append(int(match.group(1)))

        return sorted(years)
    except ClientError as e:
        raise RuntimeError(f"Failed to list S3 years: {e}")


def iter_s3_games(
    team_name: str = "Key West FC",
    year: Optional[int] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
) -> Iterator[tuple[Game, str]]:
    """Iterate over games from S3 for a specific team.

    Args:
        team_name: Team name to filter for (partial match)
        year: Specific year to fetch (overrides start/end_year)
        start_year: Start year for range (inclusive)
        end_year: End year for range (inclusive)

    Yields:
        Tuple of (Game, source_file) for each matching game
    """
    s3 = boto3.client("s3")

    # Determine year range
    if year:
        years = [year]
    else:
        available = list_s3_years()
        if start_year:
            available = [y for y in available if y >= start_year]
        if end_year:
            available = [y for y in available if y <= end_year]
        years = available

    for yr in years:
        prefix = f"{S3_PREFIX}/year={yr}/"

        # List all game files for this year
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if not key.endswith("_games.jsonl"):
                    continue

                # Download and parse the file
                try:
                    response = s3.get_object(Bucket=S3_BUCKET, Key=key)
                    content = response["Body"].read().decode("utf-8")

                    # Parse JSONL (it's actually a JSON array)
                    games_data = json.loads(content)

                    for game_data in games_data:
                        game = s3_game_to_game(game_data, team_name)
                        if game:
                            yield game, key
                except ClientError as e:
                    # Skip files we can't read
                    continue
                except json.JSONDecodeError:
                    continue


def count_s3_games(
    team_name: str = "Key West FC",
    year: Optional[int] = None,
) -> dict[int, int]:
    """Count games per year for a team in S3.

    Args:
        team_name: Team name to filter for
        year: Specific year to count (or None for all)

    Returns:
        Dict mapping year -> game count
    """
    counts: dict[int, int] = {}

    for game, _ in iter_s3_games(team_name=team_name, year=year):
        yr = game.date.year
        counts[yr] = counts.get(yr, 0) + 1

    return counts


def s3_game_to_raw_game(s3_game: dict) -> Optional[RawGame]:
    """Convert an S3 game record to RawGame model (no team filtering).

    Args:
        s3_game: Game dict from S3 JSONL file

    Returns:
        RawGame object, or None if invalid
    """
    home_team = s3_game.get("home_team", "")
    away_team = s3_game.get("away_team", "")

    if not home_team or not away_team:
        return None

    # Parse score
    home_score, away_score = parse_score(s3_game.get("score", ""))

    # Parse date
    game_date_str = s3_game.get("game_date", "")
    try:
        game_date = datetime.strptime(game_date_str, "%Y-%m-%d")
    except ValueError:
        return None

    return RawGame(
        date=game_date,
        home_team=home_team,
        away_team=away_team,
        home_score=home_score,
        away_score=away_score,
        league_name=s3_game.get("league_name", ""),
        field=s3_game.get("field"),
    )


def iter_all_s3_games(
    year: Optional[int] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
) -> Iterator[tuple[RawGame, str]]:
    """Iterate over ALL games from S3 (no team filtering).

    Args:
        year: Specific year to fetch (overrides start/end_year)
        start_year: Start year for range (inclusive)
        end_year: End year for range (inclusive)

    Yields:
        Tuple of (RawGame, source_file) for each game
    """
    s3 = boto3.client("s3")

    # Determine year range
    if year:
        years = [year]
    else:
        available = list_s3_years()
        if start_year:
            available = [y for y in available if y >= start_year]
        if end_year:
            available = [y for y in available if y <= end_year]
        years = available

    for yr in years:
        prefix = f"{S3_PREFIX}/year={yr}/"

        # List all game files for this year
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if not key.endswith("_games.jsonl"):
                    continue

                # Download and parse the file
                try:
                    response = s3.get_object(Bucket=S3_BUCKET, Key=key)
                    content = response["Body"].read().decode("utf-8")

                    # Parse JSONL (it's actually a JSON array)
                    games_data = json.loads(content)

                    for game_data in games_data:
                        raw_game = s3_game_to_raw_game(game_data)
                        if raw_game:
                            yield raw_game, key
                except ClientError:
                    continue
                except json.JSONDecodeError:
                    continue
