"""Background scheduler for periodic sync."""

import asyncio
import logging
from datetime import datetime

from ..config import settings
from ..dependencies import MonarchClient

logger = logging.getLogger(__name__)


class SyncScheduler:
    """Background scheduler for periodic data sync."""

    def __init__(self):
        self._task: asyncio.Task | None = None
        self._running = False
        self._last_sync: datetime | None = None
        self._last_error: str | None = None

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running

    @property
    def last_sync(self) -> datetime | None:
        """Get last successful sync time."""
        return self._last_sync

    @property
    def last_error(self) -> str | None:
        """Get last error message."""
        return self._last_error

    async def start(self) -> None:
        """Start the background sync scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        if not settings.sync_enabled:
            logger.info("Sync is disabled, not starting scheduler")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            f"Started sync scheduler with interval of {settings.sync_interval_minutes} minutes"
        )

    async def stop(self) -> None:
        """Stop the background sync scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Stopped sync scheduler")

    async def trigger_sync(self) -> dict:
        """Trigger an immediate sync."""
        from .service import SyncService

        try:
            monarch = await MonarchClient.get_client()
            service = SyncService(monarch)
            results = await service.sync_all()

            self._last_sync = datetime.now()
            self._last_error = None

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
            self._last_error = str(e)
            logger.exception("Sync failed")
            return {"success": False, "error": str(e)}

    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        # Initial sync on startup
        await asyncio.sleep(5)  # Small delay to let app fully initialize

        while self._running:
            try:
                logger.info("Starting scheduled sync")
                await self.trigger_sync()
            except Exception as e:
                logger.exception("Scheduled sync failed")
                self._last_error = str(e)

            # Wait for next interval
            await asyncio.sleep(settings.sync_interval_minutes * 60)


# Global scheduler instance
scheduler = SyncScheduler()
