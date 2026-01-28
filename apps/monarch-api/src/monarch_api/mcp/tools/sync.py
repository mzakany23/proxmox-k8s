"""Sync MCP tools for data management."""

from mcp.server.fastmcp import FastMCP


def register_sync_tools(mcp: FastMCP, get_session):
    """Register sync tools with the MCP server."""

    @mcp.tool()
    async def trigger_sync(
        entity: str = "all",
    ) -> dict:
        """Trigger a data sync from Monarch Money API.

        Args:
            entity: Entity type to sync (all, category_groups, categories, tags,
                   accounts, transactions, recurring_transactions)
        """
        from ...config import settings

        # Check if Monarch credentials are available
        if not settings.has_token_auth and not settings.has_credential_auth:
            # Check database for stored credentials
            has_db_creds = False
            if settings.has_database:
                try:
                    from ...db.engine import AsyncSessionLocal
                    from ...db.repositories import CredentialRepository

                    async with AsyncSessionLocal() as session:
                        repo = CredentialRepository(session)
                        credential = await repo.get_active()
                        has_db_creds = credential is not None
                except Exception:
                    pass

            if not has_db_creds:
                return {
                    "success": False,
                    "error": "Monarch credentials not configured",
                    "help": (
                        "To sync data from Monarch Money, you need to authenticate first. "
                        "Options:\n"
                        "1. Run the API server and login via /auth or the web UI at /auth\n"
                        "2. Set MONARCH_TOKEN environment variable with your session token\n"
                        "3. Set MONARCH_EMAIL and MONARCH_PASSWORD environment variables\n\n"
                        "Note: MCP tools can still query cached data in PostgreSQL without "
                        "Monarch credentials. Only the sync operation requires authentication."
                    ),
                }

        try:
            from ...dependencies import MonarchClient
            from ...sync.service import SyncService

            monarch = await MonarchClient.get_client()
            service = SyncService(monarch)

            async with get_session() as session:
                if entity == "all":
                    results = await service.sync_all(session)
                else:
                    result = await service.sync_entity(entity, session)
                    results = [result]
                await session.commit()

            return {
                "success": all(r.success for r in results),
                "results": [
                    {
                        "entity_type": r.entity_type,
                        "success": r.success,
                        "records_synced": r.records_synced,
                        "error": r.error,
                        "duration_seconds": r.duration_seconds,
                    }
                    for r in results
                ],
            }
        except Exception as e:
            error_msg = str(e)
            # Provide helpful context for common errors
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                return {
                    "success": False,
                    "error": "Authentication failed",
                    "help": (
                        "Your Monarch Money session may have expired. "
                        "Please re-authenticate via the API at /auth or update your credentials."
                    ),
                }
            return {
                "success": False,
                "error": error_msg,
            }

    @mcp.tool()
    async def get_sync_status() -> dict:
        """Get the current sync status for all entity types."""
        from ...db.repositories import SyncStatusRepository

        async with get_session() as session:
            repo = SyncStatusRepository(session)
            statuses = await repo.get_all()

            entities = {}
            for status in statuses:
                entities[status.entity_type] = {
                    "status": status.status,
                    "last_sync_at": status.last_sync_at.isoformat() if status.last_sync_at else None,
                    "records_synced": status.records_synced,
                    "error_message": status.error_message,
                }

        # Try to get scheduler status if available
        scheduler_running = False
        last_sync = None
        last_error = None

        try:
            from ...sync.scheduler import scheduler
            scheduler_running = scheduler.is_running
            last_sync = scheduler.last_sync.isoformat() if scheduler.last_sync else None
            last_error = scheduler.last_error
        except Exception:
            # Scheduler may not be available in MCP context
            pass

        return {
            "scheduler_running": scheduler_running,
            "last_sync": last_sync,
            "last_error": last_error,
            "entities": entities,
        }
