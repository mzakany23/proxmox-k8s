"""MCP resources for financial data access."""

from datetime import datetime

from mcp.server.fastmcp import FastMCP


def register_resources(mcp: FastMCP, get_session):
    """Register MCP resources."""

    @mcp.resource("finance://accounts")
    async def get_accounts_resource() -> str:
        """Current account balances and net worth summary."""
        from ...db.repositories import AccountRepository

        async with get_session() as session:
            repo = AccountRepository(session)
            accounts = await repo.get_all(include_hidden=False)

            total_assets = 0
            total_liabilities = 0
            lines = ["# Account Balances\n"]

            # Group by type
            by_type: dict[str, list] = {}
            for acc in accounts:
                acc_type = acc.account_type
                if acc_type not in by_type:
                    by_type[acc_type] = []
                by_type[acc_type].append(acc)

                balance = float(acc.current_balance)
                if acc.is_asset:
                    total_assets += balance
                else:
                    total_liabilities += balance

            for acc_type, accs in sorted(by_type.items()):
                lines.append(f"\n## {acc_type.title()}")
                for acc in accs:
                    name = acc.display_name or acc.institution_name or "Unknown"
                    balance = float(acc.current_balance)
                    lines.append(f"- {name}: ${balance:,.2f}")

            lines.append(f"\n## Summary")
            lines.append(f"- Total Assets: ${total_assets:,.2f}")
            lines.append(f"- Total Liabilities: ${total_liabilities:,.2f}")
            lines.append(f"- Net Worth: ${total_assets - total_liabilities:,.2f}")

            return "\n".join(lines)

    @mcp.resource("finance://categories")
    async def get_categories_resource() -> str:
        """Available transaction categories."""
        from ...db.repositories import CategoryGroupRepository, CategoryRepository

        async with get_session() as session:
            group_repo = CategoryGroupRepository(session)
            cat_repo = CategoryRepository(session)

            groups = await group_repo.get_all()
            categories = await cat_repo.get_all(include_hidden=False)

            # Group categories
            by_group: dict[str, list] = {}
            group_names = {g.id: g.name for g in groups}

            for cat in categories:
                group_name = group_names.get(cat.group_id, "Uncategorized")
                if group_name not in by_group:
                    by_group[group_name] = []
                by_group[group_name].append(cat)

            lines = ["# Transaction Categories\n"]
            for group_name, cats in sorted(by_group.items()):
                lines.append(f"\n## {group_name}")
                for cat in sorted(cats, key=lambda c: c.name):
                    icon = cat.icon or ""
                    lines.append(f"- {icon} {cat.name}")

            return "\n".join(lines)

    @mcp.resource("finance://summary")
    async def get_summary_resource() -> str:
        """Current month financial summary."""
        from calendar import monthrange
        from decimal import Decimal

        from sqlalchemy import func, select

        from ...db.models import Transaction

        now = datetime.now()
        start_date = datetime(now.year, now.month, 1)
        _, last_day = monthrange(now.year, now.month)
        end_date = datetime(now.year, now.month, last_day, 23, 59, 59)

        async with get_session() as session:
            # Income
            income_stmt = (
                select(func.sum(Transaction.amount))
                .where(Transaction.date >= start_date)
                .where(Transaction.date <= end_date)
                .where(Transaction.amount > 0)
            )
            income = (await session.execute(income_stmt)).scalar() or Decimal("0")

            # Expenses
            expense_stmt = (
                select(func.sum(Transaction.amount))
                .where(Transaction.date >= start_date)
                .where(Transaction.date <= end_date)
                .where(Transaction.amount < 0)
            )
            expenses = (await session.execute(expense_stmt)).scalar() or Decimal("0")

            # Transaction count
            count_stmt = (
                select(func.count(Transaction.id))
                .where(Transaction.date >= start_date)
                .where(Transaction.date <= end_date)
            )
            count = (await session.execute(count_stmt)).scalar() or 0

            net = income + expenses
            savings_rate = float(net / income * 100) if income > 0 else 0

            lines = [
                f"# Financial Summary - {now.strftime('%B %Y')}\n",
                f"## Income & Expenses",
                f"- Total Income: ${float(income):,.2f}",
                f"- Total Expenses: ${abs(float(expenses)):,.2f}",
                f"- Net Cashflow: ${float(net):,.2f}",
                f"- Savings Rate: {savings_rate:.1f}%",
                f"\n## Activity",
                f"- Transactions: {count}",
                f"- Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            ]

            return "\n".join(lines)
