# Dockerfile for perfin-analysis-mcp
# MCP server for personal finance analysis

FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency management
RUN pip install uv

# Copy project files
COPY pyproject.toml ./
COPY src/ src/

# Install dependencies using uv (non-editable for container)
RUN uv pip install --system .

# Environment defaults (override in K8s deployment)
ENV MCP_TRANSPORT=streamable-http
ENV FASTMCP_HOST=0.0.0.0
ENV FASTMCP_PORT=8000

# Data directory for transaction CSVs (mount as volume in K8s)
ENV PERFIN_DATA_DIR=/data/transactions

# MCP server listens on port 8000 for HTTP transport
EXPOSE 8000

CMD ["perfin-mcp"]
