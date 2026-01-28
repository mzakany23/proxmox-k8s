"""CLI entry point for running the Monarch Money API server."""

import argparse

import uvicorn

from .config import settings


def main() -> None:
    """Run the Monarch Money API server."""
    parser = argparse.ArgumentParser(description="Monarch Money API Server")
    parser.add_argument("--host", default=settings.host, help="Host to bind to")
    parser.add_argument("--port", type=int, default=settings.port, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()

    uvicorn.run(
        "monarch_api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload or args.debug,
        log_level="debug" if args.debug else "info",
    )


if __name__ == "__main__":
    main()
