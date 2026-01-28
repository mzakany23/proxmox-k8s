"""MCP server for conversation history search."""

import logging
import os
import sys
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from ..config import settings
from ..db import AsyncSessionLocal

logger = logging.getLogger(__name__)


def create_mcp_server(host: str = "127.0.0.1", port: int = 8000) -> FastMCP:
    """Create and configure the MCP server.

    Args:
        host: Host to bind to (default: 127.0.0.1, use 0.0.0.0 for K8s)
        port: Port to listen on (default: 8000)
    """
    mcp = FastMCP(name="conversation-history", host=host, port=port)

    @asynccontextmanager
    async def get_session():
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # Register tools
    from .tools import (
        register_browse_tools,
        register_search_tools,
        register_sync_tools,
    )

    register_search_tools(mcp, get_session)
    register_browse_tools(mcp, get_session)
    register_sync_tools(mcp, get_session)

    return mcp


# Global server instance (created lazily)
_mcp_server: FastMCP | None = None


def get_mcp_server() -> FastMCP:
    """Get or create the MCP server instance."""
    global _mcp_server
    if _mcp_server is None:
        host = os.getenv("FASTMCP_HOST", "127.0.0.1")
        port = int(os.getenv("FASTMCP_PORT", "8000"))
        _mcp_server = create_mcp_server(host=host, port=port)
    return _mcp_server




def main():
    """Entry point for the MCP server.

    Supports stdio (default), streamable-http (recommended for K8s), and sse (deprecated).
    Set MCP_TRANSPORT=streamable-http for HTTP mode (used in K8s).

    For HTTP transports, host/port are configured via FASTMCP_HOST and FASTMCP_PORT
    environment variables (defaults: 0.0.0.0:8000).
    """
    logging.basicConfig(
        level=logging.INFO if settings.debug else logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    mcp_server = get_mcp_server()

    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport in ("streamable-http", "http"):
        # Streamable HTTP transport for K8s deployment (recommended)
        # Claude Code and modern MCP clients use this protocol
        host = os.getenv("FASTMCP_HOST", "0.0.0.0")
        port = os.getenv("FASTMCP_PORT", "8000")
        logger.info(f"Starting MCP server with streamable-http transport on {host}:{port}")
        mcp_server.run(transport="streamable-http")
    elif transport == "sse":
        # SSE transport (deprecated, kept for backwards compatibility)
        host = os.getenv("FASTMCP_HOST", "0.0.0.0")
        port = os.getenv("FASTMCP_PORT", "8000")
        logger.info(f"Starting MCP server with SSE transport on {host}:{port}")
        mcp_server.run(transport="sse")
    else:
        # stdio transport for local CLI usage
        mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
