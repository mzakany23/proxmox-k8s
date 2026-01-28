"""Spending period comparison tool for MCP."""

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .spending import (
    EXCLUDE_CATEGORIES,
    FIXED_CATEGORIES,
    CATEGORY_MAP,
    ONE_TIME_EXCLUSIONS,
)


def _get_data_dir() -> Path:
    """Get the transactions data directory."""
    mcp_server_dir = Path(__file__).parent.parent.parent.parent
    project_root = mcp_server_dir.parent
    return project_root / "data" / "transactions"


def _load_transactions(data_dir: Path) -> list[dict]:
    """Load all transaction CSVs from the data directory."""
    transactions = []

    for csv_file in data_dir.glob("transactions-*.csv"):
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Date"):
                    transactions.append(row)

    return transactions


def _parse_amount(amount_str: str) -> float:
    """Parse amount string to float."""
    try:
        return float(amount_str.replace(",", "").replace("$", ""))
    except (ValueError, TypeError):
        return 0.0


def _get_spending_for_period(
    transactions: list[dict],
    start_month: str,
    end_month: str
) -> dict[str, Any]:
    """Calculate spending for a specific time period."""
    category_totals = defaultdict(float)
    total = 0
    months_seen = set()

    for txn in transactions:
        category = txn.get("Category", "Unknown")
        amount = _parse_amount(txn.get("Amount", "0"))
        date_str = txn.get("Date", "")
        merchant = txn.get("Merchant", "")

        if category in EXCLUDE_CATEGORIES:
            continue

        if amount >= 0:
            continue

        if category in FIXED_CATEGORIES:
            continue

        # Skip large one-time transactions
        skip = False
        for merchant_pattern, min_amt in ONE_TIME_EXCLUSIONS:
            if merchant_pattern.lower() in merchant.lower() and abs(amount) >= min_amt:
                skip = True
                break
        if skip:
            continue

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            month_key = date.strftime("%Y-%m")
        except ValueError:
            continue

        # Check if in period
        if month_key < start_month or month_key > end_month:
            continue

        months_seen.add(month_key)
        clean_category = CATEGORY_MAP.get(category, category)
        spending = abs(amount)
        category_totals[clean_category] += spending
        total += spending

    num_months = len(months_seen) if months_seen else 1

    return {
        "total": round(total, 2),
        "monthly_avg": round(total / num_months, 2),
        "by_category": {k: round(v, 2) for k, v in sorted(category_totals.items(), key=lambda x: -x[1])},
        "by_category_monthly": {k: round(v / num_months, 2) for k, v in category_totals.items()},
        "months": num_months,
    }


def compare_spending_periods(
    period1: dict[str, str],
    period2: dict[str, str]
) -> dict[str, Any]:
    """
    Compare spending between two time periods.

    Args:
        period1: Dict with 'start' and 'end' keys (YYYY-MM format)
        period2: Dict with 'start' and 'end' keys (YYYY-MM format)

    Returns:
        Dictionary with period1, period2 data and changes comparison
    """
    data_dir = _get_data_dir()

    if not data_dir.exists():
        return {"error": f"Data directory not found: {data_dir}"}

    transactions = _load_transactions(data_dir)

    if not transactions:
        return {"error": "No transactions found"}

    # Validate periods
    try:
        p1_start = period1.get("start", "")
        p1_end = period1.get("end", "")
        p2_start = period2.get("start", "")
        p2_end = period2.get("end", "")

        # Validate format
        for p in [p1_start, p1_end, p2_start, p2_end]:
            datetime.strptime(p + "-01", "%Y-%m-%d")
    except (ValueError, AttributeError) as e:
        return {"error": f"Invalid period format. Use YYYY-MM format. Error: {e}"}

    # Get spending for each period
    period1_data = _get_spending_for_period(transactions, p1_start, p1_end)
    period2_data = _get_spending_for_period(transactions, p2_start, p2_end)

    # Calculate changes (comparing monthly averages)
    all_categories = set(period1_data["by_category_monthly"].keys()) | set(period2_data["by_category_monthly"].keys())

    changes = []
    for cat in all_categories:
        p1_amt = period1_data["by_category_monthly"].get(cat, 0)
        p2_amt = period2_data["by_category_monthly"].get(cat, 0)
        diff = p2_amt - p1_amt
        pct_change = ((p2_amt - p1_amt) / p1_amt * 100) if p1_amt else (100 if p2_amt else 0)

        changes.append({
            "category": cat,
            "period1_avg": round(p1_amt, 2),
            "period2_avg": round(p2_amt, 2),
            "diff": round(diff, 2),
            "percent_change": round(pct_change, 1),
        })

    # Sort by absolute difference
    changes.sort(key=lambda x: abs(x["diff"]), reverse=True)

    # Total change
    total_diff = period2_data["monthly_avg"] - period1_data["monthly_avg"]
    total_pct = ((total_diff / period1_data["monthly_avg"]) * 100) if period1_data["monthly_avg"] else 0

    return {
        "period1": {
            "range": f"{p1_start} to {p1_end}",
            "total": period1_data["total"],
            "monthly_avg": period1_data["monthly_avg"],
            "months": period1_data["months"],
            "by_category": period1_data["by_category"],
        },
        "period2": {
            "range": f"{p2_start} to {p2_end}",
            "total": period2_data["total"],
            "monthly_avg": period2_data["monthly_avg"],
            "months": period2_data["months"],
            "by_category": period2_data["by_category"],
        },
        "changes": changes,
        "summary": {
            "total_diff": round(total_diff, 2),
            "percent_change": round(total_pct, 1),
            "direction": "increased" if total_diff > 0 else "decreased" if total_diff < 0 else "unchanged",
        },
    }
