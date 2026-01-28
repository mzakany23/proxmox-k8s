"""Spending analysis tool for MCP."""

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# Categories to EXCLUDE (not actual spending)
EXCLUDE_CATEGORIES = {
    "Credit Card Payment",
    "Transfer",
    "Dividends & Capital Gains",
    "403 Contribution",
    "Paychecks",
    "Other Income",
    "Interest",
    "Financial Fees",
    "Uncategorized",
    "Taxes",
    "Loan Repayment",
    "Coaching Expense",
}

# Categories that are FIXED costs (not variable)
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

# Map raw categories to cleaner names
CATEGORY_MAP = {
    "Restaurants & Bars": "Dining Out",
    "Coffee Shops": "Coffee",
    "Entertainment & Recreation": "Entertainment",
    "Business (Tech)": "Tech/Subscriptions",
    "Home Improvement": "Home",
    "Travel & Vacation": "Travel",
    "Taxi & Ride Shares": "Transportation",
    "Parking & Tolls": "Transportation",
    "Fitness": "Health & Fitness",
    "Personal": "Personal Care",
    "AI Subscription": "Tech/Subscriptions",
    "Rent": "Travel",  # Vacation rentals
}

# Large one-time transactions to EXCLUDE
ONE_TIME_EXCLUSIONS = [
    ("Cleveland Water", 1000),
    ("Electronic Check", 1000),
]

# Work-related reimbursable expenses
REIMBURSABLE_MERCHANTS = [
    "Bluewater Realty",
]


def _get_data_dir() -> Path:
    """Get the transactions data directory."""
    # Look relative to the mcp-server location
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


def _analyze_variable_spending(transactions: list[dict]) -> dict:
    """Analyze variable spending by category and month."""
    monthly_spending = defaultdict(lambda: defaultdict(float))
    category_totals = defaultdict(float)
    reimbursable_total = 0.0
    dates = []

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

        # Track reimbursable
        for reimb_merchant in REIMBURSABLE_MERCHANTS:
            if reimb_merchant.lower() in merchant.lower():
                reimbursable_total += abs(amount)
                break

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            dates.append(date)
            month_key = date.strftime("%Y-%m")
        except ValueError:
            continue

        clean_category = CATEGORY_MAP.get(category, category)
        spending = abs(amount)
        monthly_spending[month_key][clean_category] += spending
        category_totals[clean_category] += spending

    if dates:
        min_date = min(dates)
        max_date = max(dates)
        num_months = max(1, (max_date.year - min_date.year) * 12 + (max_date.month - min_date.month) + 1)
    else:
        num_months = 1
        min_date = max_date = datetime.now()

    return {
        "monthly_spending": dict(monthly_spending),
        "category_totals": dict(category_totals),
        "num_months": num_months,
        "date_range": {
            "start": min_date.strftime("%Y-%m-%d") if dates else "N/A",
            "end": max_date.strftime("%Y-%m-%d") if dates else "N/A",
        },
        "reimbursable_total": reimbursable_total,
    }


def _analyze_fixed_costs(transactions: list[dict]) -> dict:
    """Analyze fixed costs separately."""
    AUTO_PAYMENT_MERCHANTS = {
        "JP Morgan Chase": "Auto Payment (Tesla)",
        "Hyundai": "Auto Payment (Hyundai)",
    }

    monthly_fixed = defaultdict(lambda: defaultdict(float))

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

        if category == "Auto Payment":
            matched = False
            for merchant_pattern, label in AUTO_PAYMENT_MERCHANTS.items():
                if merchant_pattern.lower() in merchant.lower():
                    monthly_fixed[month_key][label] += abs(amount)
                    matched = True
                    break
            if not matched:
                monthly_fixed[month_key][category] += abs(amount)
        else:
            monthly_fixed[month_key][category] += abs(amount)

    return dict(monthly_fixed)


def _analyze_income(transactions: list[dict]) -> dict:
    """Analyze income (paychecks)."""
    monthly_income = defaultdict(float)

    for txn in transactions:
        category = txn.get("Category", "Unknown")
        amount = _parse_amount(txn.get("Amount", "0"))
        date_str = txn.get("Date", "")

        if category != "Paychecks":
            continue

        if amount <= 0:
            continue

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            month_key = date.strftime("%Y-%m")
        except ValueError:
            continue

        monthly_income[month_key] += amount

    return dict(monthly_income)


def get_spending_analysis(months: int = 6, category: str | None = None) -> dict[str, Any]:
    """
    Get spending analysis with monthly averages.

    Args:
        months: Number of full months to average (excluding current month)
        category: Optional filter to specific category

    Returns:
        Dictionary with categories, totals, savings_rate, and date_range
    """
    data_dir = _get_data_dir()

    if not data_dir.exists():
        return {"error": f"Data directory not found: {data_dir}"}

    transactions = _load_transactions(data_dir)

    if not transactions:
        return {"error": "No transactions found"}

    spending_data = _analyze_variable_spending(transactions)
    fixed_data = _analyze_fixed_costs(transactions)
    income_data = _analyze_income(transactions)

    # Get last N full months for averaging
    recent_months = _get_last_n_full_months(spending_data["monthly_spending"], months)
    num_months = len(recent_months) if recent_months else 1

    # Calculate category averages over the period
    category_totals = defaultdict(float)
    for month in recent_months:
        for cat, amt in spending_data["monthly_spending"].get(month, {}).items():
            category_totals[cat] += amt

    categories = []
    total_variable = 0

    for cat, total in sorted(category_totals.items(), key=lambda x: -x[1]):
        if category and category.lower() not in cat.lower():
            continue
        monthly_avg = total / num_months
        total_variable += monthly_avg
        categories.append({
            "name": cat,
            "monthly_avg": round(monthly_avg, 2),
            "total": round(total, 2),
            "percent": 0,  # Will calculate after
        })

    # Calculate percentages
    for cat in categories:
        cat["percent"] = round((cat["monthly_avg"] / total_variable * 100) if total_variable else 0, 1)

    # Calculate fixed costs (6-month average)
    fixed_months = _get_last_n_full_months(fixed_data, 6)
    fixed_category_totals = defaultdict(float)
    for month in fixed_months:
        for cat, amt in fixed_data.get(month, {}).items():
            fixed_category_totals[cat] += amt

    total_fixed = sum(fixed_category_totals.values()) / len(fixed_months) if fixed_months else 0

    # Calculate income average
    avg_income = sum(income_data.values()) / len(income_data) if income_data else 0

    # Calculate surplus and savings rate
    surplus = avg_income - total_fixed - total_variable
    savings_rate = (surplus / avg_income * 100) if avg_income > 0 else 0

    return {
        "categories": categories,
        "totals": {
            "variable": round(total_variable, 2),
            "fixed": round(total_fixed, 2),
            "income": round(avg_income, 2),
            "surplus": round(surplus, 2),
        },
        "savings_rate": round(savings_rate, 1),
        "date_range": spending_data["date_range"],
        "months_analyzed": num_months,
    }
