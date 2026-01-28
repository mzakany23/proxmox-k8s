"""Fixed costs analysis tool for MCP."""

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# Categories that are FIXED costs
FIXED_CATEGORIES = {
    "Mortgage",
    "Insurance",
    "Auto Payment",
    "Student Loans",
    "Phone",
    "Internet & Cable",
    "Gas & Electric",
    "Water",
}

# Auto payment merchants to track separately
AUTO_PAYMENT_MERCHANTS = {
    "JP Morgan Chase": "Auto Payment (Tesla)",
    "Hyundai": "Auto Payment (Hyundai)",
}


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


def _get_last_n_full_months(data_by_month: dict, n: int = 6) -> list[str]:
    """Get the last N full months, excluding current month."""
    current_month = datetime.now().strftime("%Y-%m")
    all_months = sorted(data_by_month.keys(), reverse=True)
    full_months = [m for m in all_months if m != current_month][:n]
    return full_months


def get_fixed_costs() -> dict[str, Any]:
    """
    Get fixed costs breakdown with monthly averages.

    Returns:
        Dictionary with costs array, total_monthly, and total_annual
    """
    data_dir = _get_data_dir()

    if not data_dir.exists():
        return {"error": f"Data directory not found: {data_dir}"}

    transactions = _load_transactions(data_dir)

    if not transactions:
        return {"error": "No transactions found"}

    # Group by month and category
    monthly_fixed = defaultdict(lambda: defaultdict(float))
    category_merchants = defaultdict(set)

    for txn in transactions:
        category = txn.get("Category", "Unknown")
        amount = _parse_amount(txn.get("Amount", "0"))
        date_str = txn.get("Date", "")
        merchant = txn.get("Merchant", "")

        if category not in FIXED_CATEGORIES:
            continue

        if amount >= 0:
            continue

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            month_key = date.strftime("%Y-%m")
        except ValueError:
            continue

        # For auto payments, break out by merchant
        if category == "Auto Payment":
            matched = False
            for merchant_pattern, label in AUTO_PAYMENT_MERCHANTS.items():
                if merchant_pattern.lower() in merchant.lower():
                    monthly_fixed[month_key][label] += abs(amount)
                    category_merchants[label].add(merchant)
                    matched = True
                    break
            if not matched:
                monthly_fixed[month_key][category] += abs(amount)
                category_merchants[category].add(merchant)
        else:
            monthly_fixed[month_key][category] += abs(amount)
            category_merchants[category].add(merchant)

    # Get last 6 full months for averaging
    recent_months = _get_last_n_full_months(monthly_fixed, 6)
    num_months = len(recent_months) if recent_months else 1

    # Calculate averages
    category_totals = defaultdict(float)
    for month in recent_months:
        for cat, amt in monthly_fixed.get(month, {}).items():
            category_totals[cat] += amt

    costs = []
    total_monthly = 0

    for cat, total in sorted(category_totals.items(), key=lambda x: -x[1]):
        monthly_avg = total / num_months
        total_monthly += monthly_avg
        # Get most common merchant for this category
        merchants = list(category_merchants.get(cat, set()))
        primary_merchant = merchants[0] if merchants else "N/A"

        costs.append({
            "category": cat,
            "amount": round(monthly_avg, 2),
            "merchant": primary_merchant,
        })

    return {
        "costs": costs,
        "total_monthly": round(total_monthly, 2),
        "total_annual": round(total_monthly * 12, 2),
        "months_analyzed": num_months,
        "period": f"{recent_months[-1]} to {recent_months[0]}" if recent_months else "N/A",
    }
