# Dockerfile for proxmox-k8s-mcp
# MCP server for Kubernetes homelab infrastructure
# Includes kubectl for cluster operations

FROM node:20-alpine

WORKDIR /app

# Install kubectl
RUN apk add --no-cache curl && \
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && \
    rm kubectl && \
    apk del curl

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY src ./src
COPY tsconfig.json ./

# Build TypeScript
RUN npm run build

# Environment defaults (override in K8s deployment)
ENV MCP_TRANSPORT=streamable-http
ENV HOST=0.0.0.0
ENV PORT=8000

# MCP server listens on port 8000 for HTTP transport
EXPOSE 8000

CMD ["node", "dist/index.js"]
