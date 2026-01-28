"""Account-related MCP tools."""

from mcp.server.fastmcp import FastMCP


def register_account_tools(mcp: FastMCP, get_session):
    """Register account tools with the MCP server."""

    @mcp.tool()
    async def get_account_balances() -> dict:
        """Get all account balances.

        Returns a summary of all accounts with their current balances,
        grouped by account type.
        """
        from ...db.repositories import AccountRepository

        async with get_session() as session:
            repo = AccountRepository(session)
            accounts = await repo.get_all(include_hidden=False)

            # Group by account type
            by_type: dict[str, list] = {}
            total_assets = 0
            total_liabilities = 0

            for acc in accounts:
                acc_type = acc.account_type
                if acc_type not in by_type:
                    by_type[acc_type] = []

                balance = float(acc.current_balance)
                by_type[acc_type].append({
                    "id": acc.id,
                    "name": acc.display_name or acc.institution_name or "Unknown",
                    "balance": balance,
                    "institution": acc.institution_name,
                })

                if acc.is_asset:
                    total_assets += balance
                else:
                    total_liabilities += balance

            return {
                "total_assets": round(total_assets, 2),
                "total_liabilities": round(total_liabilities, 2),
                "net_worth": round(total_assets - total_liabilities, 2),
                "accounts_by_type": by_type,
            }

    @mcp.tool()
    async def list_accounts(account_type: str | None = None) -> list[dict]:
        """List all accounts, optionally filtered by type.

        Args:
            account_type: Filter by account type (checking, savings, credit, brokerage, etc.)
        """
        from ...db.repositories import AccountRepository

        async with get_session() as session:
            repo = AccountRepository(session)
            accounts = await repo.get_all(include_hidden=False)

            results = []
            for acc in accounts:
                if account_type and acc.account_type != account_type:
                    continue

                results.append({
                    "id": acc.id,
                    "name": acc.display_name or acc.institution_name or "Unknown",
                    "type": acc.account_type,
                    "subtype": acc.account_subtype,
                    "balance": float(acc.current_balance),
                    "institution": acc.institution_name,
                    "is_asset": acc.is_asset,
                    "include_in_net_worth": acc.include_in_net_worth,
                })

            return results
