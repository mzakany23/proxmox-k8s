"""Transaction-related MCP tools."""

from datetime import datetime, timedelta

from mcp.server.fastmcp import FastMCP


def register_transaction_tools(mcp: FastMCP, get_session):
    """Register transaction tools with the MCP server."""

    @mcp.tool()
    async def search_transactions(
        query: str | None = None,
        category: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Search transactions with flexible filters.

        Args:
            query: Search term for merchant name
            category: Filter by category name (partial match)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            min_amount: Minimum transaction amount
            max_amount: Maximum transaction amount
            limit: Maximum results to return (default 50)
        """
        from decimal import Decimal

        from sqlalchemy import select

        from ...db.models import Category, Transaction

        async with get_session() as session:
            stmt = select(Transaction).order_by(Transaction.date.desc()).limit(limit)

            if query:
                stmt = stmt.where(Transaction.merchant_name.ilike(f"%{query}%"))
            if start_date:
                stmt = stmt.where(
                    Transaction.date >= datetime.fromisoformat(start_date)
                )
            if end_date:
                stmt = stmt.where(Transaction.date <= datetime.fromisoformat(end_date))
            if min_amount is not None:
                stmt = stmt.where(Transaction.amount >= Decimal(str(min_amount)))
            if max_amount is not None:
                stmt = stmt.where(Transaction.amount <= Decimal(str(max_amount)))

            # If category filter, need to join
            if category:
                stmt = stmt.join(Category).where(Category.name.ilike(f"%{category}%"))

            result = await session.execute(stmt)
            transactions = result.scalars().all()

            return [
                {
                    "id": txn.id,
                    "date": txn.date.strftime("%Y-%m-%d"),
                    "merchant": txn.merchant_name,
                    "amount": float(txn.amount),
                    "category_id": txn.category_id,
                    "notes": txn.notes,
                    "is_recurring": txn.is_recurring,
                }
                for txn in transactions
            ]

    @mcp.tool()
    async def get_spending_by_category(
        start_date: str | None = None,
        end_date: str | None = None,
        top_n: int = 10,
    ) -> list[dict]:
        """Get spending breakdown by category.

        Args:
            start_date: Start date (YYYY-MM-DD), defaults to start of current month
            end_date: End date (YYYY-MM-DD), defaults to today
            top_n: Number of top categories to return (default 10)
        """
        from sqlalchemy import func, select

        from ...db.models import Category, CategoryGroup, Transaction

        # Default to current month
        if not start_date:
            today = datetime.now()
            start_date = today.replace(day=1).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        async with get_session() as session:
            stmt = (
                select(
                    Category.name,
                    CategoryGroup.name.label("group_name"),
                    func.sum(Transaction.amount).label("total"),
                    func.count(Transaction.id).label("count"),
                )
                .join(Category, Transaction.category_id == Category.id)
                .join(CategoryGroup, Category.group_id == CategoryGroup.id)
                .where(Transaction.date >= datetime.fromisoformat(start_date))
                .where(Transaction.date <= datetime.fromisoformat(end_date))
                .where(Transaction.amount < 0)  # Expenses only
                .group_by(Category.name, CategoryGroup.name)
                .order_by(func.sum(Transaction.amount).asc())  # Most negative first
                .limit(top_n)
            )

            result = await session.execute(stmt)
            rows = result.all()

            return [
                {
                    "category": row.name,
                    "group": row.group_name,
                    "total_spent": abs(float(row.total)),
                    "transaction_count": row.count,
                }
                for row in rows
            ]

    @mcp.tool()
    async def get_recent_transactions(days: int = 7, limit: int = 20) -> list[dict]:
        """Get recent transactions.

        Args:
            days: Number of days to look back (default 7)
            limit: Maximum results to return (default 20)
        """
        from sqlalchemy import select

        from ...db.models import Transaction

        cutoff = datetime.now() - timedelta(days=days)

        async with get_session() as session:
            stmt = (
                select(Transaction)
                .where(Transaction.date >= cutoff)
                .order_by(Transaction.date.desc())
                .limit(limit)
            )

            result = await session.execute(stmt)
            transactions = result.scalars().all()

            return [
                {
                    "id": txn.id,
                    "date": txn.date.strftime("%Y-%m-%d"),
                    "merchant": txn.merchant_name,
                    "amount": float(txn.amount),
                    "category_id": txn.category_id,
                }
                for txn in transactions
            ]
