FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency management
RUN pip install uv

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

# Install dependencies using uv (non-editable for container)
RUN uv pip install --system .

# Environment defaults (override in K8s deployment)
ENV MCP_TRANSPORT=streamable-http
ENV DATABASE_HOST=postgres.conversation-history.svc.cluster.local
ENV DATABASE_PORT=5432
ENV DATABASE_NAME=conversation_history
ENV DATABASE_USER=convo_user

# MCP server listens on port 8000 for SSE transport
EXPOSE 8000

CMD ["conversation-history-mcp"]
