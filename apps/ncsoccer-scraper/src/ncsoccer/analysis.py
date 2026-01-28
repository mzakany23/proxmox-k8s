"""Transitive analysis engine for predicting game outcomes.

Compares how two teams perform against shared opponents to predict
the likely outcome of a matchup.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from .all_games_store import AllGamesStore
from .models import Config, RawGame


@dataclass
class TeamRecord:
    """Record of a team against a specific opponent."""

    wins: int = 0
    losses: int = 0
    ties: int = 0
    goals_for: int = 0
    goals_against: int = 0
    games: list[dict] = field(default_factory=list)

    @property
    def games_played(self) -> int:
        return self.wins + self.losses + self.ties

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def points(self) -> int:
        """Standard 3-1-0 point system."""
        return (self.wins * 3) + self.ties

    @property
    def record_str(self) -> str:
        """Return W-L-T record string."""
        return f"{self.wins}-{self.losses}-{self.ties}"

    @property
    def goal_diff_str(self) -> str:
        """Return goal diff with +/- sign."""
        diff = self.goal_diff
        if diff > 0:
            return f"+{diff}"
        return str(diff)


@dataclass
class SharedOpponentComparison:
    """Comparison of two teams against a shared opponent."""

    opponent: str
    our_record: TeamRecord
    their_record: TeamRecord
    recency_weight: float = 1.0

    @property
    def advantage_score(self) -> float:
        """Calculate advantage score based on comparisons.

        Returns a value from -1 (disadvantage) to +1 (advantage).
        Considers:
        - Win rate difference
        - Goal differential difference
        - Recency weighting
        """
        our_games = self.our_record.games_played
        their_games = self.their_record.games_played

        if our_games == 0 or their_games == 0:
            return 0.0

        # Win rate component (0-1 scale, 50% weight)
        our_win_rate = (self.our_record.wins + 0.5 * self.our_record.ties) / our_games
        their_win_rate = (self.their_record.wins + 0.5 * self.their_record.ties) / their_games
        win_diff = (our_win_rate - their_win_rate) * 0.5

        # Goal differential per game component (normalized, 50% weight)
        our_gd_per_game = self.our_record.goal_diff / our_games
        their_gd_per_game = self.their_record.goal_diff / their_games
        gd_diff = (our_gd_per_game - their_gd_per_game) / 5.0  # Normalize to ~-1 to 1
        gd_diff = max(-0.5, min(0.5, gd_diff))  # Clamp to -0.5 to 0.5

        # Combined score with recency weight
        raw_score = (win_diff + gd_diff) * self.recency_weight

        # Clamp to -1 to 1
        return max(-1.0, min(1.0, raw_score))


@dataclass
class HeadToHeadRecord:
    """Direct head-to-head record between two teams."""

    games: list[dict] = field(default_factory=list)
    wins: int = 0
    losses: int = 0
    ties: int = 0
    goals_for: int = 0
    goals_against: int = 0

    @property
    def games_played(self) -> int:
        return self.wins + self.losses + self.ties

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def record_str(self) -> str:
        return f"{self.wins}-{self.losses}-{self.ties}"

    @property
    def goal_diff_str(self) -> str:
        diff = self.goal_diff
        if diff > 0:
            return f"+{diff}"
        return str(diff)


@dataclass
class PredictionResult:
    """Result of a transitive analysis prediction."""

    our_team: str
    opponent: str
    comparisons: list[SharedOpponentComparison]
    confidence: float
    advantage_score: float
    outcome: str  # "FAVORABLE", "UNFAVORABLE", "UNCERTAIN"
    league_filter: Optional[str] = None
    time_window_days: int = 365
    head_to_head: Optional[HeadToHeadRecord] = None

    @property
    def shared_opponent_count(self) -> int:
        return len(self.comparisons)

    @property
    def advantage_bar(self) -> str:
        """Return a visual bar representing advantage."""
        # Scale -1 to 1 to 0 to 10
        filled = int((self.advantage_score + 1) * 5)
        filled = max(0, min(10, filled))
        return "█" * filled + "░" * (10 - filled)


class TransitiveAnalyzer:
    """Engine for transitive game outcome analysis."""

    def __init__(
        self,
        config: Config,
        our_team: str = "Key West FC",
        time_window_days: int = 365,
        min_shared_opponents: int = 2,
        recency_half_life_days: int = 365,
    ):
        """Initialize the analyzer.

        Args:
            config: Application config
            our_team: Name of our team
            time_window_days: Only consider games within this window
            min_shared_opponents: Minimum shared opponents needed for prediction
            recency_half_life_days: Days until a game's weight decays to 50%
        """
        self.config = config
        self.our_team = our_team
        self.time_window_days = time_window_days
        self.min_shared_opponents = min_shared_opponents
        self.recency_half_life_days = recency_half_life_days

        self.store = AllGamesStore(config)

    def _get_date_cutoff(self) -> str:
        """Get the date cutoff for analysis."""
        cutoff = datetime.now() - timedelta(days=self.time_window_days)
        return cutoff.strftime("%Y-%m-%d")

    def _calculate_recency_weight(self, game_date: str) -> float:
        """Calculate recency weight using exponential decay.

        Returns a weight from 0 to 1, where recent games are weighted more.
        """
        game_dt = datetime.strptime(game_date, "%Y-%m-%d")
        days_ago = (datetime.now() - game_dt).days

        # Exponential decay: weight = 0.5^(days / half_life)
        decay_factor = days_ago / self.recency_half_life_days
        return math.pow(0.5, decay_factor)

    def _build_team_record(
        self,
        team_name: str,
        opponent: str,
        league_name: Optional[str] = None,
    ) -> TeamRecord:
        """Build a team's record against a specific opponent.

        Args:
            team_name: The team to analyze
            opponent: The opponent they played against
            league_name: Optional league filter

        Returns:
            TeamRecord with W-L-T and goal stats
        """
        h2h_games = self.store.get_head_to_head(
            team1=team_name,
            team2=opponent,
            league_name=league_name,
            after=self._get_date_cutoff(),
        )

        record = TeamRecord()
        team_lower = team_name.lower()

        for game in h2h_games:
            meta = game["metadata"]
            if not meta["is_played"]:
                continue

            record.games.append(game)

            # Determine if team was home or away
            is_home = team_lower in meta["home_team"].lower()

            if is_home:
                our_score = meta["home_score"]
                their_score = meta["away_score"]
            else:
                our_score = meta["away_score"]
                their_score = meta["home_score"]

            record.goals_for += our_score
            record.goals_against += their_score

            if our_score > their_score:
                record.wins += 1
            elif our_score < their_score:
                record.losses += 1
            else:
                record.ties += 1

        return record

    def find_shared_opponents(
        self,
        opponent: str,
        league_name: Optional[str] = None,
    ) -> list[str]:
        """Find opponents that both teams have played.

        Args:
            opponent: The opponent to compare against
            league_name: Optional league filter

        Returns:
            List of shared opponent names
        """
        cutoff = self._get_date_cutoff()

        our_opponents = set(self.store.get_opponents_for_team(
            team_name=self.our_team,
            league_name=league_name,
            after=cutoff,
        ))

        their_opponents = set(self.store.get_opponents_for_team(
            team_name=opponent,
            league_name=league_name,
            after=cutoff,
        ))

        # Find intersection, excluding the two teams being compared
        our_lower = self.our_team.lower()
        opp_lower = opponent.lower()

        shared = []
        for opp in our_opponents & their_opponents:
            if our_lower not in opp.lower() and opp_lower not in opp.lower():
                shared.append(opp)

        return sorted(shared)

    def get_comparative_performance(
        self,
        shared_opponent: str,
        opponent: str,
        league_name: Optional[str] = None,
    ) -> SharedOpponentComparison:
        """Compare performance against a shared opponent.

        Args:
            shared_opponent: The common opponent both teams played
            opponent: The team we're comparing against
            league_name: Optional league filter

        Returns:
            SharedOpponentComparison with both teams' records
        """
        our_record = self._build_team_record(
            team_name=self.our_team,
            opponent=shared_opponent,
            league_name=league_name,
        )

        their_record = self._build_team_record(
            team_name=opponent,
            opponent=shared_opponent,
            league_name=league_name,
        )

        # Calculate recency weight based on most recent game from either team
        all_games = our_record.games + their_record.games
        if all_games:
            dates = [g["metadata"]["date"] for g in all_games]
            most_recent = max(dates)
            recency_weight = self._calculate_recency_weight(most_recent)
        else:
            recency_weight = 0.5

        return SharedOpponentComparison(
            opponent=shared_opponent,
            our_record=our_record,
            their_record=their_record,
            recency_weight=recency_weight,
        )

    def get_head_to_head_record(
        self,
        opponent: str,
        league_name: Optional[str] = None,
    ) -> HeadToHeadRecord:
        """Get direct head-to-head record against an opponent.

        Args:
            opponent: The opponent team name
            league_name: Optional league filter

        Returns:
            HeadToHeadRecord with games and stats
        """
        h2h_games = self.store.get_head_to_head(
            team1=self.our_team,
            team2=opponent,
            league_name=league_name,
            after=self._get_date_cutoff(),
        )

        record = HeadToHeadRecord()
        our_lower = self.our_team.lower()

        for game in h2h_games:
            meta = game["metadata"]
            if not meta["is_played"]:
                continue

            record.games.append(game)

            # Determine if we were home or away
            is_home = our_lower in meta["home_team"].lower()

            if is_home:
                our_score = meta["home_score"]
                their_score = meta["away_score"]
            else:
                our_score = meta["away_score"]
                their_score = meta["home_score"]

            record.goals_for += our_score
            record.goals_against += their_score

            if our_score > their_score:
                record.wins += 1
            elif our_score < their_score:
                record.losses += 1
            else:
                record.ties += 1

        return record

    def predict_outcome(
        self,
        opponent: str,
        league_name: Optional[str] = None,
    ) -> PredictionResult:
        """Predict the outcome of a matchup using transitive analysis.

        Args:
            opponent: The team to predict against
            league_name: Optional league filter (uses same league for fairer comparison)

        Returns:
            PredictionResult with confidence and analysis
        """
        shared_opponents = self.find_shared_opponents(
            opponent=opponent,
            league_name=league_name,
        )

        comparisons = []
        for shared_opp in shared_opponents:
            comparison = self.get_comparative_performance(
                shared_opponent=shared_opp,
                opponent=opponent,
                league_name=league_name,
            )
            # Only include comparisons where both teams have played
            if (comparison.our_record.games_played > 0 and
                comparison.their_record.games_played > 0):
                comparisons.append(comparison)

        # Get head-to-head record
        h2h = self.get_head_to_head_record(opponent, league_name)

        # Calculate aggregate advantage score
        if not comparisons:
            return PredictionResult(
                our_team=self.our_team,
                opponent=opponent,
                comparisons=[],
                confidence=0.0,
                advantage_score=0.0,
                outcome="UNCERTAIN",
                league_filter=league_name,
                time_window_days=self.time_window_days,
                head_to_head=h2h if h2h.games_played > 0 else None,
            )

        # Weight by recency and number of games
        total_weight = 0.0
        weighted_advantage = 0.0

        for comp in comparisons:
            # Weight by number of games played (more data = more weight)
            games_weight = min(comp.our_record.games_played + comp.their_record.games_played, 6) / 6.0
            weight = comp.recency_weight * games_weight

            weighted_advantage += comp.advantage_score * weight
            total_weight += weight

        if total_weight > 0:
            advantage_score = weighted_advantage / total_weight
        else:
            advantage_score = 0.0

        # Calculate confidence (0-100%)
        # Based on number of shared opponents and consistency of advantage
        base_confidence = min(len(comparisons) / 4.0, 1.0)  # Max at 4+ shared opponents

        # Adjust for consistency
        if len(comparisons) >= 2:
            scores = [c.advantage_score for c in comparisons]
            variance = sum((s - advantage_score) ** 2 for s in scores) / len(scores)
            consistency_factor = max(0.5, 1.0 - variance)
        else:
            consistency_factor = 0.7

        confidence = base_confidence * consistency_factor * 100

        # Determine outcome
        if abs(advantage_score) < 0.15:
            outcome = "UNCERTAIN"
        elif advantage_score > 0:
            outcome = "FAVORABLE"
        else:
            outcome = "UNFAVORABLE"

        # Require minimum shared opponents
        if len(comparisons) < self.min_shared_opponents:
            confidence = min(confidence, 30.0)
            if outcome != "UNCERTAIN":
                outcome = "UNCERTAIN"

        return PredictionResult(
            our_team=self.our_team,
            opponent=opponent,
            comparisons=comparisons,
            confidence=round(confidence, 0),
            advantage_score=round(advantage_score, 2),
            outcome=outcome,
            league_filter=league_name,
            time_window_days=self.time_window_days,
            head_to_head=h2h if h2h.games_played > 0 else None,
        )

    def predict_upcoming(
        self,
        league_name: Optional[str] = None,
    ) -> list[PredictionResult]:
        """Generate predictions for all upcoming opponents.

        Args:
            league_name: Optional league filter

        Returns:
            List of PredictionResult for each upcoming opponent
        """
        # Get our upcoming opponents from Key West's games
        from .storage import GameStore

        game_store = GameStore(self.config)
        upcoming_games = game_store.get_all_games(
            league=league_name.title() if league_name else None,
            is_played=False,
        )

        # Get unique opponents from upcoming games
        seen_opponents = set()
        predictions = []

        for game in upcoming_games:
            opponent = game["metadata"]["opponent"]
            if opponent.lower() in seen_opponents:
                continue
            seen_opponents.add(opponent.lower())

            game_league = game["metadata"]["league_name"]
            prediction = self.predict_outcome(
                opponent=opponent,
                league_name=game_league if league_name else None,
            )
            predictions.append(prediction)

        return predictions
