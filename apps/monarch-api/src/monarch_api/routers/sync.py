"""Sync router for triggering and monitoring data sync."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import require_scope
from ..db import get_db
from ..db.models import APIToken
from ..dependencies import get_monarch
from ..sync.scheduler import scheduler
from ..sync.service import SyncService

router = APIRouter(prefix="/sync", tags=["Sync"])


class SyncTriggerRequest(BaseModel):
    """Request to trigger sync."""

    entity: Literal[
        "all",
        "category_groups",
        "categories",
        "tags",
        "accounts",
        "transactions",
        "recurring_transactions",
    ] = "all"


class SyncResultItem(BaseModel):
    """Individual sync result."""

    entity_type: str
    success: bool
    records_synced: int
    error: str | None = None
    duration_seconds: float = 0.0


class SyncResponse(BaseModel):
    """Response from sync operation."""

    success: bool
    results: list[SyncResultItem] = []
    error: str | None = None


class SyncStatusResponse(BaseModel):
    """Response with sync status."""

    scheduler_running: bool
    last_sync: str | None
    last_error: str | None
    entities: dict


@router.post("/trigger", response_model=SyncResponse)
async def trigger_sync(
    request: SyncTriggerRequest,
    _: Annotated[APIToken, Depends(require_scope("write"))],
    monarch=Depends(get_monarch),
    db: AsyncSession = Depends(get_db),
) -> SyncResponse:
    """Trigger a data sync from Monarch Money API.

    Syncs data from the Monarch Money API to the local PostgreSQL database.
    By default syncs all entities, but can be limited to specific entity types.
    """
    try:
        service = SyncService(monarch)

        if request.entity == "all":
            results = await service.sync_all(db)
        else:
            result = await service.sync_entity(request.entity, db)
            results = [result]

        return SyncResponse(
            success=all(r.success for r in results),
            results=[
                SyncResultItem(
                    entity_type=r.entity_type,
                    success=r.success,
                    records_synced=r.records_synced,
                    error=r.error,
                    duration_seconds=r.duration_seconds,
                )
                for r in results
            ],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    _: Annotated[APIToken, Depends(require_scope("read"))],
    db: AsyncSession = Depends(get_db),
) -> SyncStatusResponse:
    """Get sync status for all entity types.

    Returns the current status of the sync scheduler and the last sync
    information for each entity type.
    """
    from ..dependencies import MonarchClient

    try:
        monarch = await MonarchClient.get_client()
        service = SyncService(monarch)
        entities = await service.get_status(db)

        return SyncStatusResponse(
            scheduler_running=scheduler.is_running,
            last_sync=scheduler.last_sync.isoformat() if scheduler.last_sync else None,
            last_error=scheduler.last_error,
            entities=entities,
        )
    except Exception as e:
        return SyncStatusResponse(
            scheduler_running=scheduler.is_running,
            last_sync=scheduler.last_sync.isoformat() if scheduler.last_sync else None,
            last_error=str(e),
            entities={},
        )


@router.post("/scheduler/start")
async def start_scheduler(
    _: Annotated[APIToken, Depends(require_scope("admin"))],
) -> dict:
    """Start the background sync scheduler."""
    await scheduler.start()
    return {"status": "started", "running": scheduler.is_running}


@router.post("/scheduler/stop")
async def stop_scheduler(
    _: Annotated[APIToken, Depends(require_scope("admin"))],
) -> dict:
    """Stop the background sync scheduler."""
    await scheduler.stop()
    return {"status": "stopped", "running": scheduler.is_running}
