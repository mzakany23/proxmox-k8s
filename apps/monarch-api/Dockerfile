# Dockerfile for monarch-money-mcp
# MCP server for Monarch Money financial queries

FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency management
RUN pip install uv

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ src/
COPY alembic.ini .
COPY migrations/ migrations/

# Install dependencies using uv (non-editable for container)
RUN uv pip install --system .

# Environment defaults (override in K8s deployment)
ENV MCP_TRANSPORT=streamable-http
ENV FASTMCP_HOST=0.0.0.0
ENV FASTMCP_PORT=8000

# MCP server listens on port 8000 for HTTP transport
EXPOSE 8000

CMD ["monarch-mcp"]
