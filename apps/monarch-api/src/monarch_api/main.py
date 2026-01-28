"""FastAPI application for Monarch Money API."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .exceptions import register_exception_handlers
from .routers import accounts, auth, budgets, cashflow, categories, sync, tokens, transactions

# Static files directory
STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup: Start background sync scheduler if database is configured
    if settings.has_database and settings.sync_enabled:
        from .sync.scheduler import scheduler

        await scheduler.start()

    yield

    # Shutdown: Stop background sync scheduler
    if settings.has_database:
        from .sync.scheduler import scheduler

        await scheduler.stop()


app = FastAPI(
    title="Monarch Money API",
    description="REST API wrapper for Monarch Money personal finance service",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
register_exception_handlers(app)

# Include routers
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(accounts.router, prefix=settings.api_prefix)
app.include_router(transactions.router, prefix=settings.api_prefix)
app.include_router(categories.router, prefix=settings.api_prefix)
app.include_router(budgets.router, prefix=settings.api_prefix)
app.include_router(cashflow.router, prefix=settings.api_prefix)
app.include_router(sync.router, prefix=settings.api_prefix)
app.include_router(tokens.router, prefix=settings.api_prefix)


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "monarch-api"}


@app.get("/", tags=["Health"])
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "name": "Monarch Money API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "auth": "/auth",
    }


@app.get("/auth", tags=["Authentication"], include_in_schema=False)
async def auth_page() -> FileResponse:
    """Serve the authentication page."""
    return FileResponse(STATIC_DIR / "auth.html")
