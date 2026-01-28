"""Budget scenario modeling tool for MCP."""

from typing import Any

from .spending import get_spending_analysis
from .fixed_costs import get_fixed_costs


def model_budget_scenario(
    income: float | None = None,
    cuts: dict[str, float] | None = None,
    scenario_name: str | None = None
) -> dict[str, Any]:
    """
    Model a budget scenario with income changes and spending cuts.

    Args:
        income: New monthly income (default: use current)
        cuts: Dict mapping category names to dollar amount reductions
        scenario_name: Optional name for this scenario

    Returns:
        Dictionary with current state, projected state, changes, and feasibility
    """
    # Get current spending analysis
    spending = get_spending_analysis(months=6)
    if "error" in spending:
        return spending

    fixed = get_fixed_costs()
    if "error" in fixed:
        return fixed

    # Current state
    current_income = spending["totals"]["income"]
    current_variable = spending["totals"]["variable"]
    current_fixed = fixed["total_monthly"]
    current_expenses = current_variable + current_fixed
    current_surplus = current_income - current_expenses

    # Apply changes for projection
    projected_income = income if income is not None else current_income

    # Apply cuts to variable spending
    projected_variable = current_variable
    changes = []

    if cuts:
        for cat_name, cut_amount in cuts.items():
            # Find matching category
            for cat in spending["categories"]:
                if cat_name.lower() in cat["name"].lower():
                    original = cat["monthly_avg"]
                    new_amount = max(0, original - cut_amount)
                    actual_cut = original - new_amount
                    projected_variable -= actual_cut
                    changes.append({
                        "category": cat["name"],
                        "from": round(original, 2),
                        "to": round(new_amount, 2),
                        "savings": round(actual_cut, 2),
                    })
                    break

    projected_expenses = projected_variable + current_fixed
    projected_surplus = projected_income - projected_expenses

    # Calculate feasibility
    is_sustainable = projected_surplus >= 0

    # Calculate runway if not sustainable (months until depleted)
    # Assuming ~$100k liquid assets available
    liquid_assets = 100000
    if projected_surplus < 0:
        runway_months = int(liquid_assets / abs(projected_surplus))
    else:
        runway_months = None  # Sustainable, no runway needed

    # Income change impact
    income_change = projected_income - current_income
    total_savings_from_cuts = sum(c["savings"] for c in changes)

    return {
        "scenario_name": scenario_name or "Custom Scenario",
        "current": {
            "income": round(current_income, 2),
            "fixed_costs": round(current_fixed, 2),
            "variable_spending": round(current_variable, 2),
            "expenses": round(current_expenses, 2),
            "surplus": round(current_surplus, 2),
            "savings_rate": round((current_surplus / current_income * 100) if current_income else 0, 1),
        },
        "projected": {
            "income": round(projected_income, 2),
            "fixed_costs": round(current_fixed, 2),
            "variable_spending": round(projected_variable, 2),
            "expenses": round(projected_expenses, 2),
            "surplus": round(projected_surplus, 2),
            "savings_rate": round((projected_surplus / projected_income * 100) if projected_income else 0, 1),
        },
        "changes": {
            "income_change": round(income_change, 2),
            "spending_cuts": changes,
            "total_cuts": round(total_savings_from_cuts, 2),
            "net_impact": round(income_change + total_savings_from_cuts, 2),
        },
        "feasibility": {
            "is_sustainable": is_sustainable,
            "monthly_shortfall": round(abs(projected_surplus), 2) if not is_sustainable else 0,
            "runway_months": runway_months,
            "required_cuts": round(abs(projected_surplus), 2) if not is_sustainable else 0,
        },
    }
