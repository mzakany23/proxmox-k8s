# Conversation History

Vector database and MCP server for conversation history search.

## Features

- Vector similarity search across conversation history
- Multiple data sources (file system, agent-progress database)
- MCP server with SSE transport for remote access
- Semantic and keyword search capabilities

## Installation

```bash
pip install -e .
```

## Usage

### Local CLI (stdio transport)
```bash
conversation-history-mcp
```

### K8s Deployment (SSE transport)
Set `MCP_TRANSPORT=sse` environment variable.

## Configuration

Environment variables:
- `DATABASE_HOST` - PostgreSQL host
- `DATABASE_PORT` - PostgreSQL port (default: 5432)
- `DATABASE_NAME` - Database name
- `DATABASE_USER` - Database user
- `DATABASE_PASSWORD` - Database password
- `OPENAI_API_KEY` - OpenAI API key for embeddings
- `MCP_TRANSPORT` - Transport mode: `stdio` or `sse`
