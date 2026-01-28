FROM python:3.11-slim

WORKDIR /app

# Install uv for fast package installation
RUN pip install uv

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ src/
COPY config.yaml ./

# Install the package
RUN uv pip install --system .

# Create data directory for ChromaDB
RUN mkdir -p /data/ncsoccer

# Set environment variables for MCP server
ENV MCP_TRANSPORT=streamable-http
ENV FASTMCP_HOST=0.0.0.0
ENV FASTMCP_PORT=8000

# ChromaDB data path
ENV NCSOCCER_DB_PATH=/data/ncsoccer

EXPOSE 8000

# Run the MCP server
CMD ["ncsoccer-mcp"]
