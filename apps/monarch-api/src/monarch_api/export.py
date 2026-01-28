"""Export Monarch Money data to CSV files."""

import asyncio
import csv
from datetime import datetime
from pathlib import Path

from monarchmoney import MonarchMoney
from monarchmoney.monarchmoney import MonarchMoneyEndpoints

from .config import settings

# Patch the base URL
MonarchMoneyEndpoints.BASE_URL = "https://api.monarch.com"


async def get_client() -> MonarchMoney:
    """Get authenticated MonarchMoney client."""
    if settings.has_token_auth:
        return MonarchMoney(token=settings.monarch_token)
    elif settings.has_credential_auth:
        client = MonarchMoney()
        await client.login(
            email=settings.monarch_email,
            password=settings.monarch_password,
            use_saved_session=True,
        )
        return client
    else:
        raise RuntimeError("No authentication configured. Set MONARCH_TOKEN or MONARCH_EMAIL/MONARCH_PASSWORD.")


async def export_accounts(client: MonarchMoney, output_dir: Path) -> int:
    """Export accounts to CSV."""
    result = await client.get_accounts()
    accounts = result.get("accounts", [])

    if not accounts:
        print("No accounts found")
        return 0

    filepath = output_dir / "accounts.csv"
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "display_name", "type", "subtype", "current_balance",
            "is_manual", "is_hidden", "include_in_net_worth",
            "institution_name", "data_provider", "created_at", "updated_at"
        ])

        for acc in accounts:
            type_info = acc.get("type", {}) or {}
            credential = acc.get("credential", {}) or {}
            institution = credential.get("institution", {}) or {}

            writer.writerow([
                acc.get("id"),
                acc.get("displayName"),
                type_info.get("name"),
                acc.get("subtype", {}).get("name") if acc.get("subtype") else None,
                acc.get("currentBalance"),
                acc.get("isManual", False),
                acc.get("isHidden", False),
                acc.get("includeInNetWorth", True),
                institution.get("name"),
                credential.get("dataProvider"),
                acc.get("createdAt"),
                acc.get("updatedAt"),
            ])

    print(f"Exported {len(accounts)} accounts to {filepath}")
    return len(accounts)


async def export_transactions(client: MonarchMoney, output_dir: Path, batch_size: int = 500) -> int:
    """Export all transactions to CSV."""
    filepath = output_dir / "transactions.csv"
    total = 0
    offset = 0

    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "date", "amount", "merchant_name", "plaid_name",
            "category_id", "category_name", "category_group",
            "account_id", "account_name", "notes", "tags",
            "pending", "is_recurring", "hide_from_reports", "needs_review",
            "is_split", "created_at", "updated_at"
        ])

        while True:
            result = await client.get_transactions(limit=batch_size, offset=offset)
            transactions = result.get("allTransactions", {}).get("results", [])

            if not transactions:
                break

            for t in transactions:
                category = t.get("category", {}) or {}
                account = t.get("account", {}) or {}
                tags = t.get("tags", []) or []
                merchant = t.get("merchant", {}) or {}
                category_group = category.get("group", {}) or {}

                writer.writerow([
                    t.get("id"),
                    t.get("date"),
                    t.get("amount"),
                    merchant.get("name") if merchant else t.get("plaidName"),
                    t.get("plaidName"),
                    category.get("id"),
                    category.get("name"),
                    category_group.get("name"),
                    account.get("id"),
                    account.get("displayName"),
                    t.get("notes"),
                    "|".join(tag.get("name", "") for tag in tags),
                    t.get("pending", False),
                    t.get("isRecurring", False),
                    t.get("hideFromReports", False),
                    t.get("needsReview", False),
                    t.get("isSplitTransaction", False),
                    t.get("createdAt"),
                    t.get("updatedAt"),
                ])

            total += len(transactions)
            offset += batch_size
            print(f"  Fetched {total} transactions...")

            if len(transactions) < batch_size:
                break

    print(f"Exported {total} transactions to {filepath}")
    return total


async def export_categories(client: MonarchMoney, output_dir: Path) -> int:
    """Export categories to CSV."""
    result = await client.get_transaction_categories()
    categories = result.get("categories", [])

    if not categories:
        print("No categories found")
        return 0

    filepath = output_dir / "categories.csv"
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "name", "icon", "is_system", "is_hidden",
            "group_id", "group_name", "group_type"
        ])

        for cat in categories:
            group = cat.get("group", {}) or {}
            writer.writerow([
                cat.get("id"),
                cat.get("name"),
                cat.get("icon"),
                cat.get("isSystemCategory", False),
                cat.get("isHidden", False),
                group.get("id"),
                group.get("name"),
                group.get("type"),
            ])

    print(f"Exported {len(categories)} categories to {filepath}")
    return len(categories)


async def export_tags(client: MonarchMoney, output_dir: Path) -> int:
    """Export tags to CSV."""
    result = await client.get_transaction_tags()
    tags = result.get("householdTransactionTags", [])

    if not tags:
        print("No tags found")
        return 0

    filepath = output_dir / "tags.csv"
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "color", "order"])

        for tag in tags:
            writer.writerow([
                tag.get("id"),
                tag.get("name"),
                tag.get("color"),
                tag.get("order", 0),
            ])

    print(f"Exported {len(tags)} tags to {filepath}")
    return len(tags)


async def export_recurring(client: MonarchMoney, output_dir: Path) -> int:
    """Export recurring transactions to CSV."""
    result = await client.get_recurring_transactions()
    recurring = result.get("recurringTransactionStreams", [])

    if not recurring:
        print("No recurring transactions found")
        return 0

    filepath = output_dir / "recurring_transactions.csv"
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "name", "frequency", "amount", "is_active", "is_expense",
            "category_id", "category_name", "merchant_name",
            "account_id", "account_name", "next_expected_date"
        ])

        for r in recurring:
            category = r.get("category", {}) or {}
            merchant = r.get("merchant", {}) or {}
            account = r.get("account", {}) or {}

            writer.writerow([
                r.get("id"),
                r.get("name"),
                r.get("frequency"),
                r.get("amount"),
                r.get("isActive", True),
                r.get("isExpense", True),
                category.get("id"),
                category.get("name"),
                merchant.get("name"),
                account.get("id"),
                account.get("displayName"),
                r.get("nextExpectedDate"),
            ])

    print(f"Exported {len(recurring)} recurring transactions to {filepath}")
    return len(recurring)


async def export_cashflow_summary(client: MonarchMoney, output_dir: Path) -> int:
    """Export monthly cashflow summary to CSV."""
    result = await client.get_cashflow_summary()
    summary = result.get("summary", []) or result.get("monthlySummary", [])

    if not summary:
        print("No cashflow summary found")
        return 0

    filepath = output_dir / "cashflow_summary.csv"
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["month", "income", "expenses", "savings", "savings_rate"])

        for m in summary:
            income = m.get("sumIncome", 0) or 0
            expenses = abs(m.get("sumExpense", 0) or 0)
            savings = income - expenses
            savings_rate = (savings / income * 100) if income > 0 else 0

            writer.writerow([
                m.get("month"),
                income,
                expenses,
                savings,
                f"{savings_rate:.1f}%",
            ])

    print(f"Exported {len(summary)} months of cashflow data to {filepath}")
    return len(summary)


async def export_all(output_dir: str | Path | None = None) -> dict:
    """Export all Monarch Money data to CSV files.

    Args:
        output_dir: Directory to save CSV files. Defaults to ./monarch_export_YYYYMMDD_HHMMSS/

    Returns:
        Dict with counts of exported records by type
    """
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"monarch_export_{timestamp}")
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Exporting Monarch Money data to {output_dir}/\n")

    client = await get_client()

    results = {
        "accounts": await export_accounts(client, output_dir),
        "transactions": await export_transactions(client, output_dir),
        "categories": await export_categories(client, output_dir),
        "tags": await export_tags(client, output_dir),
        "recurring": await export_recurring(client, output_dir),
        "cashflow": await export_cashflow_summary(client, output_dir),
    }

    print(f"\nExport complete! Files saved to {output_dir}/")
    return results


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Export Monarch Money data to CSV files")
    parser.add_argument(
        "-o", "--output",
        help="Output directory (default: monarch_export_TIMESTAMP/)",
        default=None,
    )
    args = parser.parse_args()

    asyncio.run(export_all(args.output))


if __name__ == "__main__":
    main()
