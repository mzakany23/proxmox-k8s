# Dockerfile for agent-progress-mcp
# MCP server for agent progress tracking

FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY agent-progress-mcp/package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY agent-progress-mcp/src ./src
COPY agent-progress-mcp/tsconfig.json ./

# Build TypeScript
RUN npm run build

# Environment defaults (override in K8s deployment)
ENV MCP_TRANSPORT=streamable-http
ENV HOST=0.0.0.0
ENV PORT=8000

# MCP server listens on port 8000 for HTTP transport
EXPOSE 8000

CMD ["node", "dist/index.js"]
