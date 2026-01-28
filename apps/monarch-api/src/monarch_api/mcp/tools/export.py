"""CSV export MCP tools using PostgreSQL data."""

import csv
from datetime import datetime, timedelta
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select, func

from ...db.models import (
    Account,
    Category,
    CategoryGroup,
    RecurringTransaction,
    Tag,
    Transaction,
    TransactionTag,
)


def register_export_tools(mcp: FastMCP, get_session):
    """Register export tools with the MCP server."""

    @mcp.tool()
    async def export_financial_data(
        output_dir: str | None = None,
        entities: list[str] | None = None,
    ) -> dict:
        """Export financial data to CSV files for analysis.

        Creates CSV files containing financial data that can be used for
        detailed analysis, reporting, or data processing.

        Args:
            output_dir: Directory path for CSV files. Defaults to
                        ~/monarch_export_YYYYMMDD_HHMMSS/
            entities: List of entities to export. Options: accounts,
                      transactions, categories, tags, recurring, cashflow.
                      Defaults to all entities.

        Returns:
            Dict with output_dir path and list of exported files with record counts.

        Example:
            export_financial_data()  # Export all to default location
            export_financial_data(output_dir="/tmp/export", entities=["accounts", "transactions"])
        """
        # Default entities
        all_entities = ["accounts", "transactions", "categories", "tags", "recurring", "cashflow"]
        if entities is None:
            entities = all_entities
        else:
            # Validate entities
            invalid = set(entities) - set(all_entities)
            if invalid:
                return {
                    "error": f"Invalid entities: {invalid}. Valid options: {all_entities}"
                }

        # Setup output directory
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path.home() / f"monarch_export_{timestamp}"
        else:
            output_path = Path(output_dir).expanduser()

        output_path.mkdir(parents=True, exist_ok=True)

        files = []
        async with get_session() as session:
            for entity in entities:
                if entity == "accounts":
                    count = await _export_accounts(session, output_path)
                    files.append({
                        "entity": "accounts",
                        "filename": "accounts.csv",
                        "path": str(output_path / "accounts.csv"),
                        "records": count,
                    })
                elif entity == "transactions":
                    count = await _export_transactions(session, output_path)
                    files.append({
                        "entity": "transactions",
                        "filename": "transactions.csv",
                        "path": str(output_path / "transactions.csv"),
                        "records": count,
                    })
                elif entity == "categories":
                    count = await _export_categories(session, output_path)
                    files.append({
                        "entity": "categories",
                        "filename": "categories.csv",
                        "path": str(output_path / "categories.csv"),
                        "records": count,
                    })
                elif entity == "tags":
                    count = await _export_tags(session, output_path)
                    files.append({
                        "entity": "tags",
                        "filename": "tags.csv",
                        "path": str(output_path / "tags.csv"),
                        "records": count,
                    })
                elif entity == "recurring":
                    count = await _export_recurring(session, output_path)
                    files.append({
                        "entity": "recurring",
                        "filename": "recurring_transactions.csv",
                        "path": str(output_path / "recurring_transactions.csv"),
                        "records": count,
                    })
                elif entity == "cashflow":
                    count = await _export_cashflow(session, output_path)
                    files.append({
                        "entity": "cashflow",
                        "filename": "cashflow_summary.csv",
                        "path": str(output_path / "cashflow_summary.csv"),
                        "records": count,
                    })

        return {
            "output_dir": str(output_path),
            "files": files,
            "total_records": sum(f["records"] for f in files),
        }


async def _export_accounts(session, output_path: Path) -> int:
    """Export accounts to CSV."""
    result = await session.execute(
        select(Account).where(Account.is_hidden == False)  # noqa: E712
    )
    accounts = result.scalars().all()

    filepath = output_path / "accounts.csv"
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "display_name", "account_type", "account_subtype",
            "current_balance", "display_balance", "include_in_net_worth",
            "is_asset", "institution_name", "data_provider"
        ])
        for account in accounts:
            writer.writerow([
                account.id,
                account.display_name,
                account.account_type,
                account.account_subtype,
                account.current_balance,
                account.display_balance,
                account.include_in_net_worth,
                account.is_asset,
                account.institution_name,
                account.data_provider,
            ])

    return len(accounts)


async def _export_transactions(session, output_path: Path) -> int:
    """Export transactions to CSV."""
    # Get transactions with category info
    result = await session.execute(
        select(Transaction, Category.name.label("category_name"), Account.display_name.label("account_name"))
        .outerjoin(Category, Transaction.category_id == Category.id)
        .join(Account, Transaction.account_id == Account.id)
        .order_by(Transaction.date.desc())
    )
    rows = result.all()

    # Get transaction tags
    tag_result = await session.execute(
        select(TransactionTag.transaction_id, Tag.name)
        .join(Tag, TransactionTag.tag_id == Tag.id)
    )
    tag_map: dict[str, list[str]] = {}
    for txn_id, tag_name in tag_result.all():
        if txn_id not in tag_map:
            tag_map[txn_id] = []
        tag_map[txn_id].append(tag_name)

    filepath = output_path / "transactions.csv"
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "date", "amount", "merchant_name", "category_name",
            "account_name", "notes", "pending", "is_recurring", "tags"
        ])
        for txn, category_name, account_name in rows:
            tags = tag_map.get(txn.id, [])
            writer.writerow([
                txn.id,
                txn.date.strftime("%Y-%m-%d") if txn.date else "",
                txn.amount,
                txn.merchant_name,
                category_name,
                account_name,
                txn.notes,
                txn.pending,
                txn.is_recurring,
                "|".join(tags) if tags else "",
            ])

    return len(rows)


async def _export_categories(session, output_path: Path) -> int:
    """Export categories to CSV."""
    result = await session.execute(
        select(Category, CategoryGroup.name.label("group_name"))
        .outerjoin(CategoryGroup, Category.group_id == CategoryGroup.id)
        .where(Category.is_hidden == False)  # noqa: E712
    )
    rows = result.all()

    filepath = output_path / "categories.csv"
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "icon", "group_name", "is_system"])
        for category, group_name in rows:
            writer.writerow([
                category.id,
                category.name,
                category.icon,
                group_name,
                category.is_system,
            ])

    return len(rows)


async def _export_tags(session, output_path: Path) -> int:
    """Export tags to CSV."""
    result = await session.execute(select(Tag).order_by(Tag.order))
    tags = result.scalars().all()

    filepath = output_path / "tags.csv"
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "color", "order"])
        for tag in tags:
            writer.writerow([
                tag.id,
                tag.name,
                tag.color,
                tag.order,
            ])

    return len(tags)


async def _export_recurring(session, output_path: Path) -> int:
    """Export recurring transactions to CSV."""
    result = await session.execute(
        select(RecurringTransaction, Category.name.label("category_name"), Account.display_name.label("account_name"))
        .outerjoin(Category, RecurringTransaction.category_id == Category.id)
        .outerjoin(Account, RecurringTransaction.account_id == Account.id)
    )
    rows = result.all()

    filepath = output_path / "recurring_transactions.csv"
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "name", "amount", "frequency", "next_date", "last_date",
            "is_income", "is_active", "category_name", "account_name"
        ])
        for recurring, category_name, account_name in rows:
            writer.writerow([
                recurring.id,
                recurring.name,
                recurring.amount,
                recurring.frequency,
                recurring.next_date.strftime("%Y-%m-%d") if recurring.next_date else "",
                recurring.last_date.strftime("%Y-%m-%d") if recurring.last_date else "",
                recurring.is_income,
                recurring.is_active,
                category_name,
                account_name,
            ])

    return len(rows)


async def _export_cashflow(session, output_path: Path) -> int:
    """Export monthly cashflow summary to CSV."""
    # Get last 12 months of data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    # Aggregate by month
    result = await session.execute(
        select(
            func.date_trunc("month", Transaction.date).label("month"),
            CategoryGroup.type.label("group_type"),
            func.sum(Transaction.amount).label("total")
        )
        .join(Category, Transaction.category_id == Category.id)
        .join(CategoryGroup, Category.group_id == CategoryGroup.id)
        .where(Transaction.date >= start_date)
        .where(Transaction.date <= end_date)
        .where(Transaction.hide_from_reports == False)  # noqa: E712
        .group_by("month", CategoryGroup.type)
        .order_by("month")
    )
    rows = result.all()

    # Organize by month
    monthly_data: dict[str, dict[str, float]] = {}
    for month, group_type, total in rows:
        month_str = month.strftime("%Y-%m")
        if month_str not in monthly_data:
            monthly_data[month_str] = {"income": 0, "expense": 0, "transfer": 0}
        monthly_data[month_str][group_type] = float(total or 0)

    filepath = output_path / "cashflow_summary.csv"
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["month", "income", "expense", "net", "savings_rate"])
        for month, data in sorted(monthly_data.items()):
            income = abs(data.get("income", 0))
            expense = abs(data.get("expense", 0))
            net = income - expense
            savings_rate = (net / income * 100) if income > 0 else 0
            writer.writerow([
                month,
                f"{income:.2f}",
                f"{expense:.2f}",
                f"{net:.2f}",
                f"{savings_rate:.1f}%",
            ])

    return len(monthly_data)
