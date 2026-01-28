"""Financial analysis tools."""

from .spending import get_spending_analysis
from .fixed_costs import get_fixed_costs
from .budget import model_budget_scenario
from .compare import compare_spending_periods
from .report import generate_report

__all__ = [
    "get_spending_analysis",
    "get_fixed_costs",
    "model_budget_scenario",
    "compare_spending_periods",
    "generate_report",
]
