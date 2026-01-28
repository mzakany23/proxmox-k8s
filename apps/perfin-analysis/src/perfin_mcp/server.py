"""Personal Finance MCP Server entry point using FastMCP."""

import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

from .tools import (
    get_spending_analysis,
    get_fixed_costs,
    model_budget_scenario,
    compare_spending_periods,
    generate_report,
)

logger = logging.getLogger(__name__)


def create_mcp_server(host: str = "127.0.0.1", port: int = 8000) -> FastMCP:
    """Create and configure the MCP server.

    Args:
        host: Host to bind to (default: 127.0.0.1, use 0.0.0.0 for K8s)
        port: Port to listen on (default: 8000)
    """
    mcp = FastMCP(name="perfin-analysis", host=host, port=port)

    @mcp.tool()
    def tool_get_spending_analysis(
        months: int = 6,
        category: str | None = None,
    ) -> dict:
        """Get spending analysis with monthly averages by category.

        Returns categories with amounts, totals (variable, fixed, income, surplus),
        savings rate, and date range analyzed.

        Args:
            months: Number of full months to average (excluding current month). Default: 6
            category: Optional filter to specific category name (partial match)
        """
        return get_spending_analysis(months=months, category=category)

    @mcp.tool()
    def tool_get_fixed_costs() -> dict:
        """Get fixed costs breakdown (mortgage, insurance, auto payments, utilities, etc.)
        with monthly amounts and annual totals.
        """
        return get_fixed_costs()

    @mcp.tool()
    def tool_model_budget_scenario(
        income: float | None = None,
        cuts: dict[str, float] | None = None,
        scenario_name: str | None = None,
    ) -> dict:
        """Model a budget scenario with income changes and/or spending cuts.

        Returns current vs projected state with feasibility analysis.
        Useful for planning income changes (e.g., retirement) or budget cuts.

        Args:
            income: New monthly income amount. If not provided, uses current income.
            cuts: Dict mapping category names to dollar amounts to cut.
                  E.g., {"Dining Out": 500, "Travel": 1000}
            scenario_name: Optional name for this scenario
        """
        return model_budget_scenario(
            income=income,
            cuts=cuts,
            scenario_name=scenario_name,
        )

    @mcp.tool()
    def tool_compare_spending_periods(
        period1: dict,
        period2: dict,
    ) -> dict:
        """Compare spending between two time periods.

        Returns totals and category breakdown for each period with changes.

        Args:
            period1: First period with 'start' and 'end' keys in YYYY-MM format
            period2: Second period with 'start' and 'end' keys in YYYY-MM format
        """
        return compare_spending_periods(period1=period1, period2=period2)

    @mcp.tool()
    def tool_generate_report(
        output_filename: str | None = None,
        include_scenarios: bool = True,
    ) -> dict:
        """Generate a formatted Excel financial report.

        Includes spending analysis, fixed costs, and budget scenarios.
        Returns the path to the generated file.

        Args:
            output_filename: Custom filename for the report
                            (default: financial-report-YYYYMMDD.xlsx)
            include_scenarios: Include budget scenario analysis sheet (default: true)
        """
        return generate_report(
            output_filename=output_filename,
            include_scenarios=include_scenarios,
        )

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
    debug = os.getenv("DEBUG", "false").lower() == "true"
    logging.basicConfig(
        level=logging.INFO if debug else logging.WARNING,
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
