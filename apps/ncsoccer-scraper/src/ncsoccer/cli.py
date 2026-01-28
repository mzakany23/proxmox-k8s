"""CLI commands for NC Soccer scraper."""

from datetime import datetime
from pathlib import Path

import click
import yaml

from .config import get_database_settings
from .discovery import (
    LeagueDiscovery,
    load_historical_leagues,
    merge_historical_leagues,
    save_historical_leagues,
)
from .all_games_store import AllGamesStore
from .analysis import TransitiveAnalyzer
from .display import (
    console,
    display_all_games_sync_summary,
    display_discovered_leagues,
    display_error,
    display_historical_sync_summary,
    display_info,
    display_prediction,
    display_results,
    display_schedule,
    display_standings,
    display_success,
    display_upcoming_games,
    display_upcoming_predictions,
    display_query_results,
    display_s3_sync_progress,
    display_s3_sync_summary,
)
from .models import Config, Game, HistoricalLeague, League, RawGame, Standing
from .s3_sync import iter_all_s3_games, iter_s3_games, list_s3_years
from .scraper import Scraper
from .storage import GameStore


def load_config() -> Config:
    """Load configuration from config.yaml."""
    import os

    config_paths = [
        Path("config.yaml"),
        Path("config.yml"),
        Path.home() / ".config" / "ncsoccer" / "config.yaml",
    ]

    for path in config_paths:
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f)
                config = Config(**data)
                # Override db_path from environment if set
                env_db_path = os.getenv("NCSOCCER_DB_PATH")
                if env_db_path:
                    config.db_path = env_db_path
                return config

    # Default config if no file found
    db_path = os.getenv("NCSOCCER_DB_PATH", "~/.ncsoccer/data")
    return Config(
        base_url="https://nc-soccer-hudson.ezleagues.ezfacility.com",
        db_path=db_path,
        teams=[
            {
                "name": "Key West FC",
                "leagues": [
                    {"id": 471403, "name": "Mens Open B", "day": "Tuesday", "team_id": 3190980},
                    {"id": 471402, "name": "Mens 40+ Friday", "day": "Friday", "team_id": 3188350},
                    {"id": 471401, "name": "Mens 30+ Sunday", "day": "Sunday", "team_id": 3189947},
                ],
            }
        ],
    )


def get_all_games(scraper: Scraper, leagues: list[League]) -> list[Game]:
    """Fetch all games from all leagues."""
    all_games = []
    for league in leagues:
        try:
            games = scraper.fetch_team_schedule(league)
            all_games.extend(games)
        except Exception as e:
            display_error(f"Failed to fetch {league.name}: {e}")
    return all_games


def get_games_from_db_or_scrape(
    config: Config, league_filter: str | None = None
) -> tuple[list[Game], bool]:
    """
    Get games from DB if available, otherwise scrape live.

    Returns (games, from_db) tuple.
    """
    store = GameStore(config)
    stats = store.get_stats()

    # Determine which leagues to use
    if league_filter and league_filter != "all":
        leagues = [config.get_league_by_day(league_filter)]
        leagues = [l for l in leagues if l is not None]
    else:
        leagues = config.all_leagues

    # Try to get from DB first
    if stats["games_count"] > 0:
        games = []
        for league in leagues:
            league_games = store.get_all_games(league=league.day)
            for g in league_games:
                games.append(store.metadata_to_game(g["metadata"]))
        if games:
            return games, True

    # Fall back to live scrape
    with console.status("[cyan]Fetching from website...[/cyan]"):
        with Scraper(config) as scraper:
            games = get_all_games(scraper, leagues)

    return games, False


@click.group()
@click.version_option(version="0.1.0", prog_name="soccer")
def cli():
    """NC Soccer Hudson CLI - Track Key West FC across all leagues."""
    pass


def _sync_all_games_from_s3(
    store: AllGamesStore,
    year: int | None,
    start_year: int | None,
    end_year: int | None,
) -> None:
    """Import ALL games from S3 bucket (for transitive analysis)."""
    # Show available years
    try:
        available_years = list_s3_years()
    except Exception as e:
        display_error(f"Failed to connect to S3: {e}")
        return

    if not available_years:
        display_error("No data found in S3 bucket")
        return

    # Determine year range
    if year:
        if year not in available_years:
            display_error(f"Year {year} not available. Available: {min(available_years)}-{max(available_years)}")
            return
        display_info(f"Importing ALL games from S3 for {year}...")
        years_to_sync = [year]
    else:
        effective_start = start_year or min(available_years)
        effective_end = end_year or max(available_years)
        years_to_sync = [y for y in available_years if effective_start <= y <= effective_end]
        display_info(f"Importing ALL games from S3 for {effective_start}-{effective_end}...")

    total_added = 0
    total_updated = 0
    games_by_year: dict[int, list[RawGame]] = {}
    teams_seen: set[str] = set()

    with console.status("[cyan]Downloading ALL games from S3...[/cyan]") as status:
        game_count = 0
        for game, source in iter_all_s3_games(
            year=year,
            start_year=start_year,
            end_year=end_year,
        ):
            yr = game.date.year
            if yr not in games_by_year:
                games_by_year[yr] = []
            games_by_year[yr].append(game)
            teams_seen.add(game.home_team)
            teams_seen.add(game.away_team)
            game_count += 1

            if game_count % 200 == 0:
                status.update(f"[cyan]Found {game_count} games, {len(teams_seen)} teams...[/cyan]")

    if not games_by_year:
        display_info("No games found in S3")
        return

    # Import games year by year
    for yr in sorted(games_by_year.keys()):
        games = games_by_year[yr]
        added, updated = store.add_games(games)
        total_added += added
        total_updated += updated
        display_success(f"  {yr}: {len(games)} games ({added} new, {updated} updated)")

    console.print()
    display_all_games_sync_summary(total_added, total_updated, len(games_by_year), len(teams_seen))


def _sync_from_s3(
    store: GameStore,
    team_name: str,
    year: int | None,
    start_year: int | None,
    end_year: int | None,
) -> None:
    """Import games from S3 bucket."""
    # Show available years
    try:
        available_years = list_s3_years()
    except Exception as e:
        display_error(f"Failed to connect to S3: {e}")
        return

    if not available_years:
        display_error("No data found in S3 bucket")
        return

    # Determine year range
    if year:
        if year not in available_years:
            display_error(f"Year {year} not available. Available: {min(available_years)}-{max(available_years)}")
            return
        display_info(f"Importing {team_name} games from S3 for {year}...")
        years_to_sync = [year]
    else:
        effective_start = start_year or min(available_years)
        effective_end = end_year or max(available_years)
        years_to_sync = [y for y in available_years if effective_start <= y <= effective_end]
        display_info(f"Importing {team_name} games from S3 for {effective_start}-{effective_end}...")

    total_added = 0
    total_updated = 0
    games_by_year: dict[int, list[Game]] = {}

    with console.status("[cyan]Downloading from S3...[/cyan]") as status:
        game_count = 0
        for game, source in iter_s3_games(
            team_name=team_name,
            year=year,
            start_year=start_year,
            end_year=end_year,
        ):
            yr = game.date.year
            if yr not in games_by_year:
                games_by_year[yr] = []
            games_by_year[yr].append(game)
            game_count += 1

            if game_count % 50 == 0:
                status.update(f"[cyan]Found {game_count} games...[/cyan]")

    if not games_by_year:
        display_info(f"No {team_name} games found in S3")
        return

    # Import games year by year
    for yr in sorted(games_by_year.keys()):
        games = games_by_year[yr]
        added, updated = store.add_games(games, team_name)
        total_added += added
        total_updated += updated
        display_success(f"  {yr}: {len(games)} games ({added} new, {updated} updated)")

    console.print()
    display_s3_sync_summary(total_added, total_updated, len(games_by_year))


@cli.command()
@click.option(
    "--league",
    "-l",
    type=click.Choice(["tuesday", "friday", "sunday", "all"], case_sensitive=False),
    default="all",
    help="League to sync",
)
@click.option(
    "--historical",
    is_flag=True,
    help="Sync all discovered historical leagues",
)
@click.option(
    "--from-s3",
    is_flag=True,
    help="Import historical data from S3 bucket (ncsh-app-data)",
)
@click.option(
    "--all-games",
    is_flag=True,
    help="Sync ALL facility games (not just Key West) for transitive analysis",
)
@click.option(
    "--year",
    "-y",
    type=int,
    help="Filter sync to a specific year",
)
@click.option(
    "--start-year",
    type=int,
    help="Start year for S3 range sync (inclusive)",
)
@click.option(
    "--end-year",
    type=int,
    help="End year for S3 range sync (inclusive)",
)
def sync(league: str, historical: bool, from_s3: bool, all_games: bool, year: int | None, start_year: int | None, end_year: int | None):
    """Sync data from NC Soccer Hudson to local database.

    Supports multiple modes:
    - Default: Sync current leagues from config
    - --historical: Sync discovered historical leagues
    - --from-s3: Import Key West historical data from S3 bucket
    - --all-games --from-s3: Import ALL facility games for transitive analysis
    """
    config = load_config()
    team_name = config.teams[0].name if config.teams else "Key West FC"

    if all_games and from_s3:
        # Import ALL games from S3 for transitive analysis
        all_store = AllGamesStore(config)
        _sync_all_games_from_s3(all_store, year, start_year, end_year)
        return

    store = GameStore(config)

    if from_s3:
        # Import Key West games from S3 bucket
        _sync_from_s3(store, team_name, year, start_year, end_year)
        return

    if historical:
        # Sync historical leagues
        historical_leagues = load_historical_leagues()
        if not historical_leagues:
            display_error("No historical leagues found. Run 'soccer discover' first.")
            return

        # Filter by year if specified
        if year:
            historical_leagues = [l for l in historical_leagues if l.year == year]
            if not historical_leagues:
                display_error(f"No historical leagues found for year {year}")
                return

        display_info(f"Syncing {len(historical_leagues)} historical leagues...")

        results = []
        with console.status("[cyan]Fetching historical data...[/cyan]"):
            with Scraper(config) as scraper:
                for hist_league in historical_leagues:
                    result = {"league": hist_league}
                    try:
                        lg = hist_league.to_league()
                        games = scraper.fetch_team_schedule(lg)
                        added, updated = store.add_games(games, team_name)
                        result["games_added"] = added
                        result["games_updated"] = updated
                    except Exception as e:
                        result["error"] = str(e)
                    results.append(result)

        display_historical_sync_summary(results)
        return

    # Normal sync (current leagues from config)
    if league == "all":
        leagues_to_sync = config.all_leagues
    else:
        found = config.get_league_by_day(league)
        if not found:
            display_error(f"No league found for {league}")
            return
        leagues_to_sync = [found]

    display_info("Syncing data to PostgreSQL...")

    total_games_added = 0
    total_games_updated = 0
    total_standings_added = 0

    with console.status("[cyan]Fetching data...[/cyan]"):
        with Scraper(config) as scraper:
            for lg in leagues_to_sync:
                try:
                    # Fetch games
                    games = scraper.fetch_team_schedule(lg)
                    added, updated = store.add_games(games, team_name)
                    total_games_added += added
                    total_games_updated += updated

                    # Fetch standings
                    standings = scraper.fetch_league_standings(lg)
                    s_added, s_updated = store.add_standings(standings, lg.name)
                    total_standings_added += s_added

                    display_success(
                        f"  {lg.name}: {len(games)} games, {len(standings)} standings"
                    )
                except Exception as e:
                    display_error(f"  {lg.name}: {e}")

    console.print()
    display_success(
        f"Sync complete: {total_games_added} new games, "
        f"{total_games_updated} updated, {total_standings_added} standings"
    )


@cli.command()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview discovered leagues without saving",
)
def discover(dry_run: bool):
    """Discover historical leagues where Key West FC has participated.

    Searches NC Soccer Hudson for past leagues and saves them
    to ~/.ncsoccer/historical_leagues.yaml for use with 'sync --historical'.
    """
    config = load_config()
    team_name = config.teams[0].name if config.teams else "Key West FC"

    # Extract team search term from config (e.g., "Key West" from "Key West FC")
    target_team = team_name.split()[0] + " " + team_name.split()[1] if len(team_name.split()) > 1 else team_name

    display_info(f"Searching for {team_name} in historical leagues...")

    discovered = []
    with console.status("[cyan]Scanning leagues...[/cyan]") as status:
        with Scraper(config) as scraper:
            discovery = LeagueDiscovery(scraper, target_team)

            def progress_callback(league_name: str, team_id: int | None):
                if team_id:
                    status.update(f"[cyan]Found in: {league_name}[/cyan]")
                else:
                    status.update(f"[dim]Scanning: {league_name[:40]}...[/dim]")

            discovered = discovery.discover_leagues(progress_callback)

    if not discovered:
        display_info("No historical leagues found.")
        return

    display_discovered_leagues(discovered)

    if dry_run:
        display_info("(dry run - not saving)")
        return

    # Merge with existing and save
    existing = load_historical_leagues()
    merged = merge_historical_leagues(existing, discovered)
    path = save_historical_leagues(merged)

    new_count = len(discovered)
    total_count = len(merged)
    display_success(f"Saved {new_count} discovered leagues ({total_count} total) to {path}")


@cli.command()
@click.argument("query_text", required=False)
@click.option(
    "--result",
    "-r",
    type=click.Choice(["win", "loss", "tie", "pending"], case_sensitive=False),
    help="Filter by result",
)
@click.option(
    "--league",
    "-l",
    type=click.Choice(["tuesday", "friday", "sunday"], case_sensitive=False),
    help="Filter by league",
)
@click.option("--opponent", "-o", help="Filter by opponent name (partial match)")
@click.option("--after", help="Filter games after date (YYYY-MM-DD)")
@click.option("--before", help="Filter games before date (YYYY-MM-DD)")
@click.option("--limit", "-n", default=10, help="Maximum results to return")
def query(
    query_text: str | None,
    result: str | None,
    league: str | None,
    opponent: str | None,
    after: str | None,
    before: str | None,
    limit: int,
):
    """Search games with semantic query and/or filters.

    Examples:
        soccer query "close games"
        soccer query "big wins" --league sunday
        soccer query --result win --limit 5
        soccer query --opponent "Purple Crew"
    """
    config = load_config()
    store = GameStore(config)

    stats = store.get_stats()
    if stats["games_count"] == 0:
        display_error("No games in database. Run 'soccer sync' first.")
        return

    results = store.query_games(
        query_text=query_text,
        result=result,
        league=league,
        opponent=opponent,
        after=after,
        before=before,
        limit=limit,
    )

    if not results:
        display_info("No games found matching your query.")
        return

    display_query_results(results, query_text)


@cli.command()
@click.argument("opponent", required=False)
@click.option(
    "--league",
    "-l",
    type=click.Choice(["tuesday", "friday", "sunday"], case_sensitive=False),
    help="Filter to a specific league",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed breakdown by shared opponent",
)
@click.option(
    "--upcoming",
    is_flag=True,
    help="Analyze all upcoming games",
)
@click.option(
    "--window",
    "-w",
    type=int,
    default=365,
    help="Time window in days for analysis (default: 365)",
)
def predict(opponent: str | None, league: str | None, verbose: bool, upcoming: bool, window: int):
    """Predict game outcomes using transitive analysis.

    Compares how Key West FC and an opponent perform against shared opponents
    to predict the likely outcome of a matchup.

    Examples:
        soccer predict "Purple Crew"
        soccer predict "BDE" --league sunday --verbose
        soccer predict --upcoming
    """
    config = load_config()
    team_name = config.teams[0].name if config.teams else "Key West FC"

    # Check if we have all-games data
    all_store = AllGamesStore(config)
    stats = all_store.get_stats()

    if stats["games_count"] == 0:
        display_error("No facility games in database for transitive analysis.")
        display_info("Run 'soccer sync --all-games --from-s3 --year 2025' first.")
        return

    analyzer = TransitiveAnalyzer(
        config=config,
        our_team=team_name,
        time_window_days=window,
    )

    if upcoming:
        # Analyze all upcoming games
        predictions = analyzer.predict_upcoming(league_name=league)
        display_upcoming_predictions(predictions)
        return

    if not opponent:
        display_error("Please specify an opponent or use --upcoming flag.")
        display_info("Example: soccer predict 'Purple Crew'")
        return

    # Predict against specific opponent
    prediction = analyzer.predict_outcome(
        opponent=opponent,
        league_name=league,
    )

    display_prediction(prediction, verbose=verbose)


@cli.group()
def db():
    """Database management commands."""
    pass


@db.command(name="init")
def db_init():
    """Initialize the PostgreSQL database schema.

    Creates all tables and enables the pgvector extension.
    Must be run before using other commands.
    """
    from .db import init_db
    from .db.engine import check_db_connection

    db_settings = get_database_settings()
    display_info(f"Connecting to PostgreSQL at {db_settings.host}:{db_settings.port}/{db_settings.name}...")

    if not check_db_connection():
        display_error("Failed to connect to database. Check your connection settings.")
        display_info("Environment variables:")
        display_info(f"  NCSOCCER_DATABASE_HOST={db_settings.host}")
        display_info(f"  NCSOCCER_DATABASE_PORT={db_settings.port}")
        display_info(f"  NCSOCCER_DATABASE_NAME={db_settings.name}")
        display_info(f"  NCSOCCER_DATABASE_USER={db_settings.user}")
        return

    try:
        init_db()
        display_success("Database schema initialized successfully!")
        display_info("Tables created: games, standings, all_games")
    except Exception as e:
        display_error(f"Failed to initialize database: {e}")


@db.command()
def status():
    """Show database statistics."""
    from .db.engine import check_db_connection

    db_settings = get_database_settings()

    console.print()
    console.print("[bold cyan]Database Status[/bold cyan]")
    console.print(f"  Host: {db_settings.host}:{db_settings.port}")
    console.print(f"  Database: {db_settings.name}")
    console.print(f"  User: {db_settings.user}")

    if not check_db_connection():
        console.print()
        console.print("[red]  Status: Not connected[/red]")
        console.print("[dim]  Run 'soccer db init' to initialize the database[/dim]")
        console.print()
        return

    console.print("[green]  Status: Connected[/green]")
    console.print()

    config = load_config()
    store = GameStore(config)
    stats = store.get_stats()

    console.print("[bold]Key West FC Games:[/bold]")
    console.print(f"  Games: {stats['games_count']}")
    console.print(f"  Standings: {stats['standings_count']}")

    if stats["earliest_game"]:
        console.print(f"  Date range: {stats['earliest_game']} to {stats['latest_game']}")

    # All games store stats
    all_store = AllGamesStore(config)
    all_stats = all_store.get_stats()

    console.print()
    console.print("[bold]All Facility Games (for predictions):[/bold]")
    console.print(f"  Games: {all_stats['games_count']}")
    console.print(f"  Teams: {all_stats['teams_count']}")
    console.print(f"  Leagues: {all_stats['leagues_count']}")

    if all_stats["earliest_game"]:
        console.print(f"  Date range: {all_stats['earliest_game']} to {all_stats['latest_game']}")

    if all_stats["games_count"] == 0:
        console.print("[dim]  (Run 'soccer sync --all-games --from-s3' to populate)[/dim]")

    console.print()


@db.command()
@click.option(
    "--all-games",
    is_flag=True,
    help="Clear only the all-games collection (preserves Key West data)",
)
@click.confirmation_option(prompt="Are you sure you want to clear data?")
def clear(all_games: bool):
    """Clear data from the database."""
    config = load_config()

    if all_games:
        all_store = AllGamesStore(config)
        all_store.clear()
        display_success("All-games collection cleared.")
    else:
        store = GameStore(config)
        store.clear()
        all_store = AllGamesStore(config)
        all_store.clear()
        display_success("All database collections cleared.")


@db.command()
def history():
    """Show discovered historical leagues."""
    historical = load_historical_leagues()

    if not historical:
        display_info("No historical leagues discovered yet.")
        display_info("Run 'soccer discover' to find past leagues.")
        return

    display_discovered_leagues(historical, title="Saved Historical Leagues")

    # Show sync status hint
    console.print("[dim]Use 'soccer sync --historical' to sync all historical data[/dim]")
    console.print("[dim]Use 'soccer sync --historical --year 2025' to sync a specific year[/dim]")
    console.print()


@cli.command()
def upcoming():
    """Show upcoming games across all leagues."""
    config = load_config()
    team_name = config.teams[0].name if config.teams else "Key West FC"

    games, from_db = get_games_from_db_or_scrape(config)

    if from_db:
        display_info("(from database)")

    if games:
        display_upcoming_games(games, team_name)
    else:
        display_info("No games found. Try running 'soccer sync' first.")


@cli.command()
def results():
    """Show recent game results."""
    config = load_config()
    team_name = config.teams[0].name if config.teams else "Key West FC"

    games, from_db = get_games_from_db_or_scrape(config)

    if from_db:
        display_info("(from database)")

    if games:
        display_results(games, team_name)
    else:
        display_info("No results found. Try running 'soccer sync' first.")


@cli.command()
@click.option(
    "--league",
    "-l",
    type=click.Choice(["tuesday", "friday", "sunday", "all"], case_sensitive=False),
    default="all",
    help="League to show standings for",
)
def standings(league: str):
    """Show league standings."""
    config = load_config()
    store = GameStore(config)
    stats = store.get_stats()

    # Try DB first
    if stats["standings_count"] > 0:
        display_info("(from database)")

        if league == "all":
            league_names = [lg.name for lg in config.all_leagues]
        else:
            found = config.get_league_by_day(league)
            if not found:
                display_error(f"No league found for {league}")
                return
            league_names = [found.name]

        for league_name in league_names:
            standings_data = store.get_latest_standings(league_name)
            if standings_data:
                standings_list = [
                    store.metadata_to_standing(s["metadata"]) for s in standings_data
                ]
                # Get league day from config
                lg = next(
                    (l for l in config.all_leagues if l.name == league_name), None
                )
                league_day = lg.day if lg else ""
                display_standings(standings_list, league_name, league_day)
        return

    # Fall back to live scrape
    if league == "all":
        leagues_to_show = config.all_leagues
    else:
        found = config.get_league_by_day(league)
        if not found:
            display_error(f"No league found for {league}")
            return
        leagues_to_show = [found]

    with console.status("[cyan]Fetching standings...[/cyan]"):
        with Scraper(config) as scraper:
            for lg in leagues_to_show:
                try:
                    standings_data = scraper.fetch_league_standings(lg)
                    display_standings(standings_data, lg.name, lg.day)
                except Exception as e:
                    display_error(f"Failed to fetch standings for {lg.name}: {e}")


@cli.command()
@click.option(
    "--league",
    "-l",
    type=click.Choice(["tuesday", "friday", "sunday"], case_sensitive=False),
    required=True,
    help="League to show schedule for",
)
def schedule(league: str):
    """Show full schedule for a specific league."""
    config = load_config()
    team_name = config.teams[0].name if config.teams else "Key West FC"

    found = config.get_league_by_day(league)
    if not found:
        display_error(f"No league found for {league}")
        return

    games, from_db = get_games_from_db_or_scrape(config, league)

    if from_db:
        display_info("(from database)")
        display_schedule(games, found.name, found.day, team_name)
    else:
        with console.status("[cyan]Fetching schedule...[/cyan]"):
            with Scraper(config) as scraper:
                try:
                    games = scraper.fetch_team_schedule(found)
                    display_schedule(games, found.name, found.day, team_name)
                except Exception as e:
                    display_error(f"Failed to fetch schedule: {e}")


@cli.command()
def refresh():
    """Refresh data from NC Soccer Hudson (deprecated, use 'sync')."""
    display_info("Note: 'refresh' is deprecated. Use 'soccer sync' instead.")
    console.print()

    # Call sync logic
    config = load_config()

    display_info("Refreshing data from NC Soccer Hudson...")

    with console.status("[cyan]Fetching all data...[/cyan]"):
        with Scraper(config) as scraper:
            total_games = 0
            for league in config.all_leagues:
                try:
                    games = scraper.fetch_team_schedule(league)
                    standings = scraper.fetch_league_standings(league)
                    total_games += len(games)
                    display_success(
                        f"  {league.name}: {len(games)} games, {len(standings)} teams"
                    )
                except Exception as e:
                    display_error(f"  {league.name}: {e}")

    display_success(f"\nRefreshed {total_games} total games across all leagues.")


@cli.command()
def info():
    """Show configuration info."""
    config = load_config()

    console.print()
    console.print("[bold cyan]NC Soccer Configuration[/bold cyan]")
    console.print(f"Base URL: {config.base_url}")
    console.print(f"Database: {config.db_path_resolved}")
    console.print()

    for team in config.teams:
        console.print(f"[bold]{team.name}[/bold]")
        for league in team.leagues:
            console.print(f"  {league.name} ({league.day})")
            console.print(f"    League ID: {league.id}, Team ID: {league.team_id}")
    console.print()


if __name__ == "__main__":
    cli()
