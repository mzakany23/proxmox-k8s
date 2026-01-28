"""Analytics MCP tools for financial insights."""

from datetime import datetime, timedelta
from decimal import Decimal

from mcp.server.fastmcp import FastMCP


def register_analytics_tools(mcp: FastMCP, get_session):
    """Register analytics tools with the MCP server."""

    @mcp.tool()
    async def get_monthly_summary(year: int | None = None, month: int | None = None) -> dict:
        """Get monthly financial summary.

        Args:
            year: Year (defaults to current year)
            month: Month 1-12 (defaults to current month)
        """
        from calendar import monthrange

        from sqlalchemy import func, select

        from ...db.models import Transaction

        # Default to current month
        now = datetime.now()
        year = year or now.year
        month = month or now.month

        # Calculate date range
        start_date = datetime(year, month, 1)
        _, last_day = monthrange(year, month)
        end_date = datetime(year, month, last_day, 23, 59, 59)

        async with get_session() as session:
            # Get income (positive amounts)
            income_stmt = (
                select(func.sum(Transaction.amount))
                .where(Transaction.date >= start_date)
                .where(Transaction.date <= end_date)
                .where(Transaction.amount > 0)
                .where(Transaction.hide_from_reports == False)  # noqa: E712
            )
            income_result = await session.execute(income_stmt)
            total_income = income_result.scalar() or Decimal("0")

            # Get expenses (negative amounts)
            expense_stmt = (
                select(func.sum(Transaction.amount))
                .where(Transaction.date >= start_date)
                .where(Transaction.date <= end_date)
                .where(Transaction.amount < 0)
                .where(Transaction.hide_from_reports == False)  # noqa: E712
            )
            expense_result = await session.execute(expense_stmt)
            total_expenses = expense_result.scalar() or Decimal("0")

            # Calculate savings
            net = total_income + total_expenses  # expenses are negative
            savings_rate = (
                float(net / total_income * 100) if total_income > 0 else 0
            )

            return {
                "year": year,
                "month": month,
                "total_income": float(total_income),
                "total_expenses": abs(float(total_expenses)),
                "net_cashflow": float(net),
                "savings_rate": round(savings_rate, 1),
            }

    @mcp.tool()
    async def analyze_spending_trends(
        months: int = 6, category: str | None = None
    ) -> dict:
        """Analyze spending trends over time.

        Args:
            months: Number of months to analyze (default 6)
            category: Optional category name to filter by
        """
        from sqlalchemy import extract, func, select

        from ...db.models import Category, Transaction

        # Calculate date range
        now = datetime.now()
        start_date = datetime(now.year, now.month, 1)
        for _ in range(months - 1):
            start_date = start_date.replace(day=1) - timedelta(days=1)
            start_date = start_date.replace(day=1)

        async with get_session() as session:
            stmt = (
                select(
                    extract("year", Transaction.date).label("year"),
                    extract("month", Transaction.date).label("month"),
                    func.sum(Transaction.amount).label("total"),
                )
                .where(Transaction.date >= start_date)
                .where(Transaction.amount < 0)  # Expenses only
                .where(Transaction.hide_from_reports == False)  # noqa: E712
                .group_by(
                    extract("year", Transaction.date),
                    extract("month", Transaction.date),
                )
                .order_by(
                    extract("year", Transaction.date),
                    extract("month", Transaction.date),
                )
            )

            if category:
                stmt = stmt.join(Category).where(Category.name.ilike(f"%{category}%"))

            result = await session.execute(stmt)
            rows = result.all()

            monthly_data = [
                {
                    "year": int(row.year),
                    "month": int(row.month),
                    "spending": abs(float(row.total)),
                }
                for row in rows
            ]

            # Calculate average and trend
            if monthly_data:
                amounts = [d["spending"] for d in monthly_data]
                avg_spending = sum(amounts) / len(amounts)

                # Simple trend: compare recent half to older half
                mid = len(amounts) // 2
                if mid > 0:
                    older_avg = sum(amounts[:mid]) / mid
                    recent_avg = sum(amounts[mid:]) / (len(amounts) - mid)
                    trend_pct = (
                        ((recent_avg - older_avg) / older_avg * 100)
                        if older_avg > 0
                        else 0
                    )
                else:
                    trend_pct = 0
            else:
                avg_spending = 0
                trend_pct = 0

            return {
                "months_analyzed": months,
                "category_filter": category,
                "monthly_spending": monthly_data,
                "average_monthly_spending": round(avg_spending, 2),
                "trend_percent": round(trend_pct, 1),
                "trend_direction": "increasing" if trend_pct > 5 else "decreasing" if trend_pct < -5 else "stable",
            }

    @mcp.tool()
    async def compare_periods(
        period1_start: str,
        period1_end: str,
        period2_start: str,
        period2_end: str,
    ) -> dict:
        """Compare spending between two time periods.

        Args:
            period1_start: First period start (YYYY-MM-DD)
            period1_end: First period end (YYYY-MM-DD)
            period2_start: Second period start (YYYY-MM-DD)
            period2_end: Second period end (YYYY-MM-DD)
        """
        from sqlalchemy import func, select

        from ...db.models import Transaction

        async with get_session() as session:
            async def get_period_totals(start: str, end: str) -> dict:
                start_dt = datetime.fromisoformat(start)
                end_dt = datetime.fromisoformat(end)

                # Income
                income_stmt = (
                    select(func.sum(Transaction.amount))
                    .where(Transaction.date >= start_dt)
                    .where(Transaction.date <= end_dt)
                    .where(Transaction.amount > 0)
                )
                income = (await session.execute(income_stmt)).scalar() or Decimal("0")

                # Expenses
                expense_stmt = (
                    select(func.sum(Transaction.amount))
                    .where(Transaction.date >= start_dt)
                    .where(Transaction.date <= end_dt)
                    .where(Transaction.amount < 0)
                )
                expenses = (await session.execute(expense_stmt)).scalar() or Decimal("0")

                return {
                    "income": float(income),
                    "expenses": abs(float(expenses)),
                    "net": float(income + expenses),
                }

            period1 = await get_period_totals(period1_start, period1_end)
            period2 = await get_period_totals(period2_start, period2_end)

            # Calculate differences
            income_diff = period2["income"] - period1["income"]
            expense_diff = period2["expenses"] - period1["expenses"]

            return {
                "period1": {
                    "start": period1_start,
                    "end": period1_end,
                    **period1,
                },
                "period2": {
                    "start": period2_start,
                    "end": period2_end,
                    **period2,
                },
                "differences": {
                    "income_change": round(income_diff, 2),
                    "expense_change": round(expense_diff, 2),
                    "income_change_pct": round(
                        income_diff / period1["income"] * 100, 1
                    )
                    if period1["income"]
                    else 0,
                    "expense_change_pct": round(
                        expense_diff / period1["expenses"] * 100, 1
                    )
                    if period1["expenses"]
                    else 0,
                },
            }

    @mcp.tool()
    async def find_recurring_patterns() -> list[dict]:
        """Find recurring transaction patterns (subscriptions, bills, etc.)."""
        from ...db.repositories import RecurringTransactionRepository

        async with get_session() as session:
            repo = RecurringTransactionRepository(session)
            recurring = await repo.get_all(is_active=True)

            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "amount": float(r.amount),
                    "frequency": r.frequency,
                    "is_income": r.is_income,
                    "next_date": r.next_date.strftime("%Y-%m-%d") if r.next_date else None,
                    "last_date": r.last_date.strftime("%Y-%m-%d") if r.last_date else None,
                }
                for r in recurring
            ]
