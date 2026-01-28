"""Sync service orchestrating all sync handlers."""

import logging
from dataclasses import dataclass
from datetime import datetime

from monarchmoney import MonarchMoney
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import AsyncSessionLocal
from ..db.repositories import SyncStatusRepository
from .handlers import (
    AccountSyncHandler,
    CategoryGroupSyncHandler,
    CategorySyncHandler,
    RecurringTransactionSyncHandler,
    TagSyncHandler,
    TransactionSyncHandler,
)

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a sync operation."""

    entity_type: str
    success: bool
    records_synced: int
    error: str | None = None
    duration_seconds: float = 0.0


class SyncService:
    """Service for orchestrating data sync from Monarch Money API."""

    def __init__(self, monarch: MonarchMoney):
        self.monarch = monarch

    async def sync_all(self, session: AsyncSession | None = None) -> list[SyncResult]:
        """Sync all entities in the correct order.

        Order: category_groups -> categories -> tags -> accounts -> transactions -> recurring
        """
        results = []

        # Use provided session or create new one
        if session:
            results = await self._sync_all_with_session(session)
        else:
            async with AsyncSessionLocal() as session:
                results = await self._sync_all_with_session(session)
                await session.commit()

        return results

    async def _sync_all_with_session(self, session: AsyncSession) -> list[SyncResult]:
        """Run all sync handlers with the given session."""
        results = []

        # Fetch category data once to share between category_groups and categories handlers
        # This avoids the 401 cold-start auth issue where the first API call fails
        logger.info("Pre-fetching category data for shared use")
        try:
            category_data = await self.monarch.get_transaction_categories()
        except Exception as e:
            logger.exception("Failed to fetch category data")
            results.append(SyncResult(
                entity_type="category_groups",
                success=False,
                records_synced=0,
                error=str(e),
            ))
            return results

        # Run category_groups and categories with shared data
        category_group_handler = CategoryGroupSyncHandler(session, self.monarch)
        result = await self._run_handler(category_group_handler, prefetched_data=category_data)
        results.append(result)
        if not result.success:
            logger.error(f"Stopping sync due to error in {category_group_handler.entity_type}")
            return results

        category_handler = CategorySyncHandler(session, self.monarch)
        result = await self._run_handler(category_handler, prefetched_data=category_data)
        results.append(result)
        if not result.success:
            logger.error(f"Stopping sync due to error in {category_handler.entity_type}")
            return results

        # Run remaining handlers normally
        remaining_handlers = [
            TagSyncHandler(session, self.monarch),
            AccountSyncHandler(session, self.monarch),
            TransactionSyncHandler(session, self.monarch),
            RecurringTransactionSyncHandler(session, self.monarch),
        ]

        for handler in remaining_handlers:
            result = await self._run_handler(handler)
            results.append(result)

            # Stop on error to maintain data integrity
            if not result.success:
                logger.error(f"Stopping sync due to error in {handler.entity_type}")
                break

        return results

    async def _run_handler(self, handler, prefetched_data: dict | None = None) -> SyncResult:
        """Run a single sync handler and return result.

        Args:
            handler: The sync handler to run.
            prefetched_data: Optional pre-fetched data to pass to the handler.
        """
        start = datetime.now()

        try:
            if prefetched_data is not None:
                count = await handler.sync(prefetched_data=prefetched_data)
            else:
                count = await handler.sync()
            duration = (datetime.now() - start).total_seconds()

            return SyncResult(
                entity_type=handler.entity_type,
                success=True,
                records_synced=count,
                duration_seconds=duration,
            )
        except Exception as e:
            duration = (datetime.now() - start).total_seconds()
            logger.exception(f"Sync failed for {handler.entity_type}")

            return SyncResult(
                entity_type=handler.entity_type,
                success=False,
                records_synced=0,
                error=str(e),
                duration_seconds=duration,
            )

    async def sync_entity(
        self, entity_type: str, session: AsyncSession | None = None
    ) -> SyncResult:
        """Sync a specific entity type."""
        handler_map = {
            "category_groups": CategoryGroupSyncHandler,
            "categories": CategorySyncHandler,
            "tags": TagSyncHandler,
            "accounts": AccountSyncHandler,
            "transactions": TransactionSyncHandler,
            "recurring_transactions": RecurringTransactionSyncHandler,
        }

        if entity_type not in handler_map:
            return SyncResult(
                entity_type=entity_type,
                success=False,
                records_synced=0,
                error=f"Unknown entity type: {entity_type}",
            )

        if session:
            handler = handler_map[entity_type](session, self.monarch)
            return await self._run_handler(handler)
        else:
            async with AsyncSessionLocal() as session:
                handler = handler_map[entity_type](session, self.monarch)
                result = await self._run_handler(handler)
                await session.commit()
                return result

    async def get_status(self, session: AsyncSession | None = None) -> dict:
        """Get sync status for all entity types."""
        if session:
            return await self._get_status_with_session(session)
        else:
            async with AsyncSessionLocal() as session:
                return await self._get_status_with_session(session)

    async def _get_status_with_session(self, session: AsyncSession) -> dict:
        """Get sync status with provided session."""
        repo = SyncStatusRepository(session)
        statuses = await repo.get_all()

        return {
            status.entity_type: {
                "status": status.status,
                "last_sync_at": status.last_sync_at.isoformat() if status.last_sync_at else None,
                "records_synced": status.records_synced,
                "error_message": status.error_message,
            }
            for status in statuses
        }
