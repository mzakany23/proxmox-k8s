"""Web scraping logic for NC Soccer Hudson."""

import re
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from .models import Config, Game, League, Standing, extract_year_from_league_name


class Scraper:
    """Scraper for NC Soccer Hudson EZFacility site."""

    def __init__(self, config: Config):
        self.config = config
        self.client = httpx.Client(
            base_url=config.base_url,
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
        )

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def fetch_team_schedule(self, league: League) -> list[Game]:
        """Fetch schedule and results for a team."""
        url = f"/teams/{league.team_id}/team.aspx"
        response = self.client.get(url)
        response.raise_for_status()
        # Extract year from league name for proper date parsing
        year = extract_year_from_league_name(league.name)
        return self._parse_team_schedule(
            response.text, league.name, league.day, league.team_id, year
        )

    def fetch_league_standings(self, league: League) -> list[Standing]:
        """Fetch standings for a league."""
        # Standings are embedded in the team page
        url = f"/teams/{league.team_id}/team.aspx"
        response = self.client.get(url)
        response.raise_for_status()
        return self._parse_standings(response.text, league.team_id)

    def _parse_team_schedule(
        self, html: str, league_name: str, league_day: str, team_id: int, year: int | None = None
    ) -> list[Game]:
        """Parse team schedule HTML into Game objects."""
        soup = BeautifulSoup(html, "lxml")
        games = []

        # Find the schedule table - it's in div#pnlSchedule
        schedule_div = soup.find("div", id="pnlSchedule")
        if not schedule_div:
            return games

        # Find the schedule table (has columns: Date, Home, score, Away, Time/Status, Venue)
        table = schedule_div.find("table", id=re.compile(r"Schedule.*GridView"))
        if not table:
            # Try finding any table in the schedule section
            table = schedule_div.find("table", class_="ezl-base-table")
        if not table:
            return games

        rows = table.find_all("tr")[1:]  # Skip header row

        for row in rows:
            game = self._parse_schedule_row(row, league_name, league_day, team_id, year)
            if game:
                games.append(game)

        return games

    def _parse_schedule_row(
        self, row, league_name: str, league_day: str, team_id: int, year: int | None = None
    ) -> Optional[Game]:
        """Parse a schedule table row into a Game object."""
        try:
            cells = row.find_all("td")
            if len(cells) < 6:
                return None

            # Column 0: Date (e.g., "Sun-Jan 4")
            date_cell = cells[0]
            date_link = date_cell.find("a")
            date_text = date_link.get_text(strip=True) if date_link else date_cell.get_text(strip=True)
            game_date = self._parse_schedule_date(date_text, year)
            if not game_date:
                return None

            # Column 1: Home team
            home_cell = cells[1]
            home_link = home_cell.find("a")
            home_team = home_link.get_text(strip=True) if home_link else ""
            is_home_bold = home_cell.find("b") is not None

            # Column 2: Score (e.g., "17 - 4" or "v")
            score_cell = cells[2]
            score_text = score_cell.get_text(strip=True)
            home_score, away_score = self._parse_score(score_text)

            # Column 3: Away team
            away_cell = cells[3]
            away_link = away_cell.find("a")
            away_team = away_link.get_text(strip=True) if away_link else ""
            is_away_bold = away_cell.find("b") is not None

            # Column 4: Time/Status (e.g., "Complete", "1:00 PM", "Result Pending")
            time_cell = cells[4]
            time_link = time_cell.find("a")
            time_text = time_link.get_text(strip=True) if time_link else time_cell.get_text(strip=True)

            # Add time if it's a time format (not "Complete" or "Result Pending")
            if re.match(r"\d{1,2}:\d{2}\s*(AM|PM|am|pm)", time_text):
                game_date = self._add_time_to_date(game_date, time_text)

            # Column 5: Venue/Field
            venue_cell = cells[5] if len(cells) > 5 else None
            field = None
            if venue_cell:
                venue_link = venue_cell.find("a")
                field = venue_link.get_text(strip=True) if venue_link else venue_cell.get_text(strip=True)

            # Determine if we're home or away based on bold formatting
            # Bold team is our team
            if is_home_bold:
                is_home = True
                opponent = away_team
            elif is_away_bold:
                is_home = False
                opponent = home_team
            else:
                # Fallback: check team names
                if "key west" in home_team.lower():
                    is_home = True
                    opponent = away_team
                else:
                    is_home = False
                    opponent = home_team

            if not opponent:
                return None

            return Game(
                date=game_date,
                opponent=opponent,
                home_score=home_score,
                away_score=away_score,
                is_home=is_home,
                field=field,
                league_name=league_name,
                league_day=league_day,
            )
        except Exception:
            return None

    def _parse_schedule_date(self, text: str, year: int | None = None) -> Optional[datetime]:
        """Parse schedule date like 'Sun-Jan 4' or 'Sun-Jan 11'.

        Args:
            text: Date text to parse
            year: Year to use for the date. If None, uses current year.
        """
        # Format: "Day-Mon D" or "Day-Mon DD"
        # Need to add year
        text = text.strip()

        # Try various formats
        patterns = [
            (r"(\w+)-(\w+)\s+(\d+)", "%a-%b %d"),  # Sun-Jan 4
            (r"(\w+)\s+(\d+)", "%b %d"),  # Jan 4
        ]

        target_year = year or datetime.now().year

        for pattern, fmt in patterns:
            match = re.match(pattern, text)
            if match:
                try:
                    # Add year to the date string
                    date_str = f"{text} {target_year}"
                    # Adjust format to include year
                    full_fmt = fmt + " %Y"
                    return datetime.strptime(date_str, full_fmt)
                except ValueError:
                    continue

        return None

    def _parse_score(self, text: str) -> tuple[Optional[int], Optional[int]]:
        """Parse score text like '17 - 4' into (home_score, away_score)."""
        text = text.strip()

        # Match score pattern: digit(s) - digit(s)
        match = re.search(r"(\d+)\s*[-–]\s*(\d+)", text)
        if match:
            return int(match.group(1)), int(match.group(2))

        # No score (game not played yet)
        return None, None

    def _parse_standings(self, html: str, our_team_id: int) -> list[Standing]:
        """Parse standings HTML into Standing objects."""
        soup = BeautifulSoup(html, "lxml")
        standings = []

        # Find standings table - it has id "gvStandings"
        table = soup.find("table", id="gvStandings")
        if not table:
            # Try finding in pnlStandings div
            standings_div = soup.find("div", id="pnlStandings")
            if standings_div:
                table = standings_div.find("table", class_="ezl-base-table")

        if not table:
            return standings

        rows = table.find_all("tr")[1:]  # Skip header row

        for rank, row in enumerate(rows, 1):
            standing = self._parse_standing_row(row, rank, our_team_id)
            if standing:
                standings.append(standing)

        return standings

    def _parse_standing_row(
        self, row, rank: int, our_team_id: int
    ) -> Optional[Standing]:
        """Parse a standing row using data-th attributes."""
        try:
            cells = row.find_all("td")
            if len(cells) < 8:
                return None

            def get_cell_value(data_th: str) -> str:
                """Get cell value by data-th attribute."""
                for cell in cells:
                    if cell.get("data-th") == data_th:
                        return cell.get_text(strip=True)
                return ""

            def get_int(data_th: str, default: int = 0) -> int:
                """Get integer value from cell."""
                val = get_cell_value(data_th)
                try:
                    return int(val)
                except (ValueError, TypeError):
                    return default

            # First cell is team name (data-th="Team")
            team_cell = cells[0]
            team_link = team_cell.find("a")
            team_name = team_link.get_text(strip=True) if team_link else team_cell.get_text(strip=True)

            if not team_name:
                return None

            # Check if this is our team
            # Our team row has bgcolor="#E3FFF7" or contains bold tags
            is_our_team = False
            if row.get("bgcolor") == "#E3FFF7":
                is_our_team = True
            elif team_cell.find("b"):
                is_our_team = True
            elif team_link and str(our_team_id) in team_link.get("href", ""):
                is_our_team = True
            elif "key west" in team_name.lower():
                is_our_team = True

            return Standing(
                rank=rank,
                team_name=team_name,
                games_played=get_int("GP"),
                wins=get_int("W"),
                losses=get_int("L"),
                ties=get_int("T"),
                goals_for=get_int("GF"),
                goals_against=get_int("GA"),
                points=get_int("PTS"),
                is_our_team=is_our_team,
            )
        except Exception:
            return None

    def _add_time_to_date(self, date: datetime, time_str: str) -> datetime:
        """Add time to a date."""
        try:
            # Parse time like "7:00 PM"
            time_match = re.search(r"(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)", time_str)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                ampm = time_match.group(3).upper()

                if ampm == "PM" and hour != 12:
                    hour += 12
                elif ampm == "AM" and hour == 12:
                    hour = 0

                return date.replace(hour=hour, minute=minute)
        except Exception:
            pass

        return date

    # ============================================================
    # League Discovery Methods
    # ============================================================

    def fetch_league_index(self) -> list[dict]:
        """Fetch the league index page and extract all leagues.

        Returns:
            List of dicts with 'id', 'name', 'url' for each league.
        """
        url = "/leagues.aspx"
        response = self.client.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        leagues = []

        # The leagues are in anchor tags with href like leagues/{id}/{name}.aspx
        # (note: may or may not have leading slash)
        for link in soup.find_all("a", href=re.compile(r"leagues/\d+/")):
            href = link.get("href", "")
            name = link.get_text(strip=True)

            # Extract league ID from URL like leagues/471403/MensOpenB.aspx
            match = re.search(r"leagues/(\d+)/", href)
            if match and name:
                league_id = int(match.group(1))
                leagues.append({
                    "id": league_id,
                    "name": name,
                    "url": href,
                })

        return leagues

    def fetch_league_teams(self, league_id: int, league_url: str) -> list[dict]:
        """Fetch teams from a league page.

        Args:
            league_id: The league ID
            league_url: The league URL path (e.g., 'leagues/466726/...')

        Returns:
            List of dicts with 'id', 'name', 'url' for each team.
        """
        # Ensure URL starts with /
        if not league_url.startswith("/"):
            league_url = "/" + league_url

        try:
            response = self.client.get(league_url)
            response.raise_for_status()
        except Exception:
            return []

        soup = BeautifulSoup(response.text, "lxml")
        teams = []
        seen_ids = set()

        # Teams are in links with href like ../../teams/{team_id}/Team-Name.aspx
        for link in soup.find_all("a", href=re.compile(r"teams/\d+/")):
            href = link.get("href", "")
            name = link.get_text(strip=True)

            match = re.search(r"teams/(\d+)/", href)
            if match and name:
                team_id = int(match.group(1))
                # Avoid duplicates (same team appears multiple times on page)
                if team_id not in seen_ids:
                    seen_ids.add(team_id)
                    teams.append({
                        "id": team_id,
                        "name": name,
                        "url": href,
                    })

        return teams

    def find_team_in_league(
        self, league_id: int, league_url: str, target_team: str = "Key West"
    ) -> int | None:
        """Find a team's ID in a league by name (partial match).

        Args:
            league_id: The league ID
            league_url: The league URL path
            target_team: Team name to search for (partial match, case-insensitive)

        Returns:
            Team ID if found, None otherwise.
        """
        teams = self.fetch_league_teams(league_id, league_url)
        target_lower = target_team.lower()

        for team in teams:
            if target_lower in team["name"].lower():
                return team["id"]

        return None

    def detect_league_day(self, league_name: str) -> str:
        """Detect the day of week from a league name.

        Args:
            league_name: League name like "Mens Open B Tuesday Winter 2025"

        Returns:
            Day name (e.g., "Tuesday") or "Unknown"
        """
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        name_lower = league_name.lower()

        for day in days:
            if day.lower() in name_lower:
                return day

        # Try common abbreviations
        day_abbrevs = {
            "mon": "Monday",
            "tue": "Tuesday",
            "wed": "Wednesday",
            "thu": "Thursday",
            "fri": "Friday",
            "sat": "Saturday",
            "sun": "Sunday",
        }
        for abbrev, day in day_abbrevs.items():
            if abbrev in name_lower:
                return day

        return "Unknown"
