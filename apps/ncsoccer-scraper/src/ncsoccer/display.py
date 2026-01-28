"""Rich display formatting for NC Soccer CLI."""

from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .models import Game, GameResult, HistoricalLeague, Standing

# Import for type hints only, to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .analysis import PredictionResult, SharedOpponentComparison

console = Console()


def display_upcoming_games(games: list[Game], team_name: str = "Key West FC"):
    """Display upcoming games in a rich table."""
    # Filter to upcoming games only
    now = datetime.now()
    upcoming = [g for g in games if g.date > now]
    upcoming.sort(key=lambda g: g.date)

    if not upcoming:
        console.print(f"[yellow]No upcoming games found for {team_name}[/yellow]")
        return

    console.print()
    console.print(
        Panel(f"[bold cyan]{team_name} - Upcoming Games[/bold cyan]", expand=False)
    )
    console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Date", style="cyan")
    table.add_column("League", style="dim")
    table.add_column("Opponent")
    table.add_column("Time", style="green")
    table.add_column("Field", style="dim")

    for game in upcoming:
        opponent = f"vs {game.opponent}" if game.is_home else f"@ {game.opponent}"
        table.add_row(
            game.date_display,
            game.league_day,
            opponent,
            game.time_display,
            game.field or "-",
        )

    console.print(table)
    console.print()


def display_results(games: list[Game], team_name: str = "Key West FC", limit: int = 10):
    """Display recent game results."""
    # Filter to played games only
    played = [g for g in games if g.is_played]
    played.sort(key=lambda g: g.date, reverse=True)
    played = played[:limit]

    if not played:
        console.print(f"[yellow]No results found for {team_name}[/yellow]")
        return

    console.print()
    console.print(
        Panel(f"[bold cyan]{team_name} - Recent Results[/bold cyan]", expand=False)
    )
    console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Date", style="cyan")
    table.add_column("League", style="dim")
    table.add_column("Opponent")
    table.add_column("Result", justify="center")
    table.add_column("Score", justify="center")

    for game in played:
        opponent = f"vs {game.opponent}" if game.is_home else f"@ {game.opponent}"

        result = game.result
        if result == GameResult.WIN:
            result_text = Text("W", style="bold green")
            score_style = "green"
        elif result == GameResult.LOSS:
            result_text = Text("L", style="bold red")
            score_style = "red"
        else:
            result_text = Text("T", style="bold yellow")
            score_style = "yellow"

        table.add_row(
            game.date_display,
            game.league_day,
            opponent,
            result_text,
            Text(game.score_display, style=score_style),
        )

    console.print(table)
    console.print()


def display_standings(
    standings: list[Standing], league_name: str, league_day: str
):
    """Display league standings in a rich table."""
    if not standings:
        console.print(f"[yellow]No standings found for {league_name}[/yellow]")
        return

    console.print()
    console.print(
        Panel(f"[bold cyan]{league_name} ({league_day}) - Standings[/bold cyan]", expand=False)
    )
    console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("#", justify="right", style="dim", width=3)
    table.add_column("Team", min_width=20)
    table.add_column("GP", justify="center", width=4)
    table.add_column("W", justify="center", width=4)
    table.add_column("L", justify="center", width=4)
    table.add_column("T", justify="center", width=4)
    table.add_column("GD", justify="center", width=5)
    table.add_column("PTS", justify="center", width=5, style="bold")

    for standing in standings:
        # Highlight our team
        if standing.is_our_team:
            team_text = Text(f"⭐ {standing.team_name}", style="bold cyan")
            row_style = "on grey23"
        else:
            team_text = Text(standing.team_name)
            row_style = None

        # Color goal difference
        gd = standing.goal_diff
        if gd > 0:
            gd_text = Text(f"+{gd}", style="green")
        elif gd < 0:
            gd_text = Text(str(gd), style="red")
        else:
            gd_text = Text("0")

        table.add_row(
            str(standing.rank),
            team_text,
            str(standing.games_played),
            str(standing.wins),
            str(standing.losses),
            str(standing.ties),
            gd_text,
            str(standing.points),
            style=row_style,
        )

    console.print(table)
    console.print()


def display_schedule(
    games: list[Game], league_name: str, league_day: str, team_name: str = "Key West FC"
):
    """Display full schedule for a league."""
    if not games:
        console.print(f"[yellow]No schedule found for {league_name}[/yellow]")
        return

    games.sort(key=lambda g: g.date)

    console.print()
    console.print(
        Panel(
            f"[bold cyan]{team_name} - {league_name} ({league_day}) Schedule[/bold cyan]",
            expand=False,
        )
    )
    console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Date", style="cyan")
    table.add_column("Time", style="dim")
    table.add_column("Opponent")
    table.add_column("Result", justify="center")
    table.add_column("Score", justify="center")
    table.add_column("Field", style="dim")

    now = datetime.now()

    for game in games:
        opponent = f"vs {game.opponent}" if game.is_home else f"@ {game.opponent}"

        if game.is_played:
            result = game.result
            if result == GameResult.WIN:
                result_text = Text("W", style="bold green")
                score_style = "green"
            elif result == GameResult.LOSS:
                result_text = Text("L", style="bold red")
                score_style = "red"
            else:
                result_text = Text("T", style="bold yellow")
                score_style = "yellow"
            score_text = Text(game.score_display, style=score_style)
        else:
            if game.date > now:
                result_text = Text("-", style="dim")
            else:
                result_text = Text("?", style="yellow")
            score_text = Text("-", style="dim")

        table.add_row(
            game.date_display,
            game.time_display,
            opponent,
            result_text,
            score_text,
            game.field or "-",
        )

    console.print(table)
    console.print()


def display_error(message: str):
    """Display an error message."""
    console.print(f"[bold red]Error:[/bold red] {message}")


def display_info(message: str):
    """Display an info message."""
    console.print(f"[cyan]{message}[/cyan]")


def display_success(message: str):
    """Display a success message."""
    console.print(f"[green]{message}[/green]")


def display_query_results(results: list[dict], query_text: str | None = None):
    """Display semantic search query results."""
    if not results:
        console.print("[yellow]No results found[/yellow]")
        return

    console.print()
    title = f"Query Results"
    if query_text:
        title += f' for "{query_text}"'
    console.print(Panel(f"[bold cyan]{title}[/bold cyan]", expand=False))
    console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Date", style="cyan", width=12)
    table.add_column("League", style="dim", width=8)
    table.add_column("Opponent", min_width=15)
    table.add_column("Result", justify="center", width=6)
    table.add_column("Score", justify="center", width=6)
    if query_text:
        table.add_column("Relevance", justify="right", width=9)

    for r in results:
        meta = r["metadata"]
        opponent = f"vs {meta['opponent']}" if meta["is_home"] else f"@ {meta['opponent']}"

        result_val = meta["result"]
        if result_val == "win":
            result_text = Text("W", style="bold green")
            score_style = "green"
        elif result_val == "loss":
            result_text = Text("L", style="bold red")
            score_style = "red"
        elif result_val == "tie":
            result_text = Text("T", style="bold yellow")
            score_style = "yellow"
        else:
            result_text = Text("-", style="dim")
            score_style = "dim"

        if meta["our_score"] >= 0:
            score = f"{meta['our_score']}-{meta['their_score']}"
        else:
            score = "-"

        row = [
            meta["date"],
            meta["league_day"],
            opponent,
            result_text,
            Text(score, style=score_style),
        ]

        if query_text and "distance" in r:
            # Convert distance to relevance percentage (lower distance = higher relevance)
            # ChromaDB uses L2 distance, typically 0-2 range
            relevance = max(0, 100 - (r["distance"] * 50))
            row.append(f"{relevance:.0f}%")

        table.add_row(*row)

    console.print(table)
    console.print()


def display_discovered_leagues(leagues: list[HistoricalLeague], title: str = "Discovered Historical Leagues"):
    """Display discovered historical leagues in a table."""
    if not leagues:
        console.print("[yellow]No historical leagues found[/yellow]")
        return

    console.print()
    console.print(Panel(f"[bold cyan]{title}[/bold cyan]", expand=False))
    console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Year", style="cyan", width=6)
    table.add_column("Day", width=10)
    table.add_column("League Name", min_width=30)
    table.add_column("Team ID", style="dim", width=10)
    table.add_column("League ID", style="dim", width=10)

    current_year = None
    for league in leagues:
        # Add separator between years
        if current_year is not None and league.year != current_year:
            table.add_row("", "", "", "", "", style="dim")
        current_year = league.year

        day_style = {
            "Sunday": "yellow",
            "Tuesday": "green",
            "Friday": "magenta",
        }.get(league.day, "white")

        table.add_row(
            str(league.year),
            Text(league.day, style=day_style),
            league.name,
            str(league.team_id),
            str(league.id),
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(leagues)} leagues found[/dim]")
    console.print()


def display_historical_sync_summary(results: list[dict]):
    """Display summary after syncing historical leagues.

    Args:
        results: List of dicts with 'league', 'games_added', 'games_updated', 'error'
    """
    if not results:
        console.print("[yellow]No leagues synced[/yellow]")
        return

    console.print()
    console.print(Panel("[bold cyan]Historical Sync Summary[/bold cyan]", expand=False))
    console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Year", style="cyan", width=6)
    table.add_column("Day", width=10)
    table.add_column("League", min_width=25)
    table.add_column("Games", justify="right", width=8)
    table.add_column("Status", width=12)

    total_games = 0
    success_count = 0
    error_count = 0

    for r in results:
        league = r["league"]
        error = r.get("error")

        if error:
            status = Text("Error", style="red")
            games_text = "-"
            error_count += 1
        else:
            added = r.get("games_added", 0)
            updated = r.get("games_updated", 0)
            total = added + updated
            total_games += total
            games_text = str(total)
            if added > 0:
                status = Text(f"+{added} new", style="green")
            else:
                status = Text("Up to date", style="dim")
            success_count += 1

        day_style = {
            "Sunday": "yellow",
            "Tuesday": "green",
            "Friday": "magenta",
        }.get(league.day, "white")

        table.add_row(
            str(league.year),
            Text(league.day, style=day_style),
            league.name[:25] + "..." if len(league.name) > 25 else league.name,
            games_text,
            status,
        )

    console.print(table)
    console.print()

    # Summary line
    if error_count > 0:
        console.print(f"[green]Synced {success_count} leagues[/green], [red]{error_count} errors[/red]")
    else:
        console.print(f"[green]Synced {success_count} leagues successfully[/green]")
    console.print(f"[dim]Total games: {total_games}[/dim]")
    console.print()


def display_s3_sync_progress(year: int, games_found: int):
    """Display progress during S3 sync."""
    console.print(f"  [cyan]{year}[/cyan]: {games_found} games found")


def display_s3_sync_summary(added: int, updated: int, years_count: int):
    """Display summary after S3 sync.

    Args:
        added: Number of games added
        updated: Number of games updated
        years_count: Number of years synced
    """
    console.print(Panel("[bold cyan]S3 Sync Summary[/bold cyan]", expand=False))
    console.print()
    console.print(f"[green]Sync complete:[/green] {added + updated} total games")
    console.print(f"  [green]{added} new games added[/green]")
    console.print(f"  [dim]{updated} games updated[/dim]")
    console.print(f"  [dim]Across {years_count} years[/dim]")
    console.print()


def display_head_to_head(prediction: "PredictionResult"):
    """Display head-to-head history between the two teams.

    Args:
        prediction: PredictionResult with head_to_head data
    """
    h2h = prediction.head_to_head
    if not h2h or h2h.games_played == 0:
        console.print("[dim]No direct head-to-head games found[/dim]")
        return

    console.print(f"[bold]Direct History vs {prediction.opponent}:[/bold]")

    # Summary line
    if h2h.wins > h2h.losses:
        style = "green"
    elif h2h.wins < h2h.losses:
        style = "red"
    else:
        style = "yellow"

    console.print(f"  Record: [{style}]{h2h.record_str}[/{style}] ({h2h.goal_diff_str} GD)")

    # Individual games table
    if h2h.games:
        table = Table(show_header=True, header_style="bold", box=None)
        table.add_column("Date", style="cyan", width=12)
        table.add_column("Result", width=8, justify="center")
        table.add_column("Score", width=8, justify="center")
        table.add_column("League", style="dim")

        our_lower = prediction.our_team.lower()

        for game in sorted(h2h.games, key=lambda g: g["metadata"]["date"], reverse=True):
            meta = game["metadata"]
            is_home = our_lower in meta["home_team"].lower()

            if is_home:
                our_score = meta["home_score"]
                their_score = meta["away_score"]
            else:
                our_score = meta["away_score"]
                their_score = meta["home_score"]

            if our_score > their_score:
                result_text = Text("W", style="bold green")
                score_style = "green"
            elif our_score < their_score:
                result_text = Text("L", style="bold red")
                score_style = "red"
            else:
                result_text = Text("T", style="bold yellow")
                score_style = "yellow"

            table.add_row(
                meta["date"],
                result_text,
                Text(f"{our_score}-{their_score}", style=score_style),
                meta["league_name"][:30] if meta["league_name"] else "-",
            )

        console.print(table)


def display_prediction(prediction: "PredictionResult", verbose: bool = False):
    """Display a prediction result with optional details.

    Args:
        prediction: PredictionResult from TransitiveAnalyzer
        verbose: Show detailed shared opponent breakdown
    """
    console.print()
    title = f"Prediction: {prediction.our_team} vs {prediction.opponent}"
    console.print(Panel(f"[bold cyan]{title}[/bold cyan]", expand=False))
    console.print("═" * 40)
    console.print()

    # Head-to-head history first
    if prediction.head_to_head and prediction.head_to_head.games_played > 0:
        display_head_to_head(prediction)
        console.print()

    # Outcome with color
    outcome_colors = {
        "FAVORABLE": "green",
        "UNFAVORABLE": "red",
        "UNCERTAIN": "yellow",
    }
    outcome_color = outcome_colors.get(prediction.outcome, "white")
    console.print(f"[bold]Transitive Analysis:[/bold]")
    console.print(f"Outcome: [bold {outcome_color}]{prediction.outcome}[/bold {outcome_color}] for {prediction.our_team}")

    # Confidence
    confidence = prediction.confidence
    if confidence >= 70:
        conf_style = "green"
    elif confidence >= 40:
        conf_style = "yellow"
    else:
        conf_style = "dim"
    console.print(f"Confidence: [{conf_style}]{confidence:.0f}%[/{conf_style}]")

    # Advantage score with bar
    adv = prediction.advantage_score
    if adv > 0:
        adv_style = "green"
        adv_str = f"+{adv:.2f}"
    elif adv < 0:
        adv_style = "red"
        adv_str = f"{adv:.2f}"
    else:
        adv_style = "dim"
        adv_str = "0.00"

    console.print(f"Advantage: [{adv_style}]{adv_str}[/{adv_style}] [{adv_style}]{prediction.advantage_bar}[/{adv_style}]")
    console.print()

    if prediction.shared_opponent_count == 0:
        console.print("[yellow]No shared opponents found for analysis.[/yellow]")
        console.print("[dim]Try syncing more historical data: soccer sync --all-games --from-s3[/dim]")
    else:
        console.print(f"[dim]Based on {prediction.shared_opponent_count} shared opponent(s)[/dim]")

        if prediction.league_filter:
            console.print(f"[dim]League filter: {prediction.league_filter}[/dim]")
        console.print(f"[dim]Time window: {prediction.time_window_days} days[/dim]")

    if verbose and prediction.comparisons:
        console.print()
        display_shared_opponent_table(prediction)

    console.print()


def display_shared_opponent_table(prediction: "PredictionResult"):
    """Display detailed breakdown by shared opponent.

    Args:
        prediction: PredictionResult with comparisons
    """
    if not prediction.comparisons:
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Shared Opponent", min_width=18)
    table.add_column(prediction.our_team, min_width=12, justify="center")
    table.add_column(prediction.opponent, min_width=12, justify="center")
    table.add_column("Adv", width=6, justify="right")

    for comp in prediction.comparisons:
        our_rec = comp.our_record
        their_rec = comp.their_record

        # Format records
        our_str = f"{our_rec.record_str} ({our_rec.goal_diff_str})"
        their_str = f"{their_rec.record_str} ({their_rec.goal_diff_str})"

        # Color based on comparison
        if our_rec.goal_diff > their_rec.goal_diff:
            our_style = "green"
            their_style = "red"
        elif our_rec.goal_diff < their_rec.goal_diff:
            our_style = "red"
            their_style = "green"
        else:
            our_style = "white"
            their_style = "white"

        # Advantage score
        adv = comp.advantage_score
        if adv > 0:
            adv_str = f"[green]+{adv:.2f}[/green]"
        elif adv < 0:
            adv_str = f"[red]{adv:.2f}[/red]"
        else:
            adv_str = "[dim]0.00[/dim]"

        table.add_row(
            comp.opponent,
            Text(our_str, style=our_style),
            Text(their_str, style=their_style),
            adv_str,
        )

    console.print(table)


def display_upcoming_predictions(predictions: list["PredictionResult"]):
    """Display predictions for all upcoming games.

    Args:
        predictions: List of PredictionResult objects
    """
    if not predictions:
        console.print("[yellow]No upcoming games found for prediction.[/yellow]")
        return

    console.print()
    console.print(Panel("[bold cyan]Upcoming Game Predictions[/bold cyan]", expand=False))
    console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Opponent", min_width=20)
    table.add_column("Outcome", width=12, justify="center")
    table.add_column("Confidence", width=10, justify="center")
    table.add_column("Advantage", width=20)
    table.add_column("Shared", width=8, justify="center")

    for pred in predictions:
        # Outcome with color
        outcome_colors = {
            "FAVORABLE": "green",
            "UNFAVORABLE": "red",
            "UNCERTAIN": "yellow",
        }
        outcome_color = outcome_colors.get(pred.outcome, "white")
        outcome_text = Text(pred.outcome, style=f"bold {outcome_color}")

        # Confidence
        conf = pred.confidence
        if conf >= 70:
            conf_style = "green"
        elif conf >= 40:
            conf_style = "yellow"
        else:
            conf_style = "dim"
        conf_text = Text(f"{conf:.0f}%", style=conf_style)

        # Advantage with bar
        adv = pred.advantage_score
        if adv > 0:
            adv_style = "green"
            adv_str = f"+{adv:.2f}"
        elif adv < 0:
            adv_style = "red"
            adv_str = f"{adv:.2f}"
        else:
            adv_style = "dim"
            adv_str = "0.00"
        adv_text = f"[{adv_style}]{adv_str} {pred.advantage_bar}[/{adv_style}]"

        table.add_row(
            pred.opponent,
            outcome_text,
            conf_text,
            adv_text,
            str(pred.shared_opponent_count),
        )

    console.print(table)
    console.print()
    console.print("[dim]Use 'soccer predict OPPONENT --verbose' for detailed breakdown[/dim]")
    console.print()


def display_all_games_sync_summary(added: int, updated: int, years_count: int, teams_count: int):
    """Display summary after syncing all games.

    Args:
        added: Number of games added
        updated: Number of games updated
        years_count: Number of years synced
        teams_count: Number of unique teams
    """
    console.print(Panel("[bold cyan]All Games Sync Summary[/bold cyan]", expand=False))
    console.print()
    console.print(f"[green]Sync complete:[/green] {added + updated} total games")
    console.print(f"  [green]{added} new games added[/green]")
    console.print(f"  [dim]{updated} games updated[/dim]")
    console.print(f"  [dim]Across {years_count} years[/dim]")
    console.print(f"  [dim]{teams_count} unique teams[/dim]")
    console.print()
