#!/bin/bash
# register-app.sh - Register an app for K8s deployment
# Usage: ./deploy/scripts/register-app.sh <app-name> [--build]
#
# This script:
# 1. Validates the app exists in apps/<app-name>/ with a Dockerfile
# 2. Creates Kustomize overlay at deploy/kubernetes/overlays/<app-name>/
# 3. Generates values.yaml for the shared homelab-app Helm chart
# 4. Optionally builds and pushes the container image

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="registry.home.mcztest.com"
DOMAIN="home.mcztest.com"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APPS_DIR="$REPO_ROOT/apps"
OVERLAYS_DIR="$REPO_ROOT/deploy/kubernetes/overlays"
HELM_CHART_PATH="../../../helm/homelab-app"

# Parse arguments
APP_NAME=""
BUILD_IMAGE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            BUILD_IMAGE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 <app-name> [--build]"
            echo ""
            echo "Arguments:"
            echo "  app-name    Name of the app (must exist in apps/<app-name>/)"
            echo ""
            echo "Options:"
            echo "  --build     Build and push container image to registry"
            echo "  --help      Show this help message"
            exit 0
            ;;
        *)
            APP_NAME="$1"
            shift
            ;;
    esac
done

if [ -z "$APP_NAME" ]; then
    echo -e "${RED}Error: App name is required${NC}"
    echo "Usage: $0 <app-name> [--build]"
    exit 1
fi

APP_DIR="$APPS_DIR/$APP_NAME"
OVERLAY_DIR="$OVERLAYS_DIR/$APP_NAME"

echo "========================================"
echo "Registering app: $APP_NAME"
echo "========================================"

# Step 1: Validate app structure
echo ""
echo -e "${YELLOW}Step 1: Validating app structure...${NC}"

if [ ! -d "$APP_DIR" ]; then
    echo -e "${RED}Error: App directory not found: $APP_DIR${NC}"
    echo "Please migrate the app to apps/$APP_NAME/ first"
    exit 1
fi

if [ ! -f "$APP_DIR/Dockerfile" ]; then
    echo -e "${RED}Error: Dockerfile not found: $APP_DIR/Dockerfile${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Validated apps/$APP_NAME/Dockerfile${NC}"

# Detect app type (Python or Node.js)
APP_TYPE="unknown"
if [ -f "$APP_DIR/pyproject.toml" ]; then
    APP_TYPE="python"
    echo -e "${GREEN}✓ Detected Python app (pyproject.toml)${NC}"
elif [ -f "$APP_DIR/package.json" ]; then
    APP_TYPE="nodejs"
    echo -e "${GREEN}✓ Detected Node.js app (package.json)${NC}"
fi

# Detect if MCP is present
HAS_MCP=false
if [ -d "$APP_DIR/src" ]; then
    if find "$APP_DIR/src" -type d -name "mcp" 2>/dev/null | grep -q .; then
        HAS_MCP=true
        echo -e "${GREEN}✓ Detected MCP server${NC}"
    fi
fi

# Step 2: Check if overlay already exists
echo ""
echo -e "${YELLOW}Step 2: Creating Kustomize overlay...${NC}"

if [ -d "$OVERLAY_DIR" ]; then
    echo -e "${YELLOW}Warning: Overlay already exists at $OVERLAY_DIR${NC}"
    read -p "Overwrite? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping overlay creation"
    else
        rm -rf "$OVERLAY_DIR"
    fi
fi

mkdir -p "$OVERLAY_DIR"

# Step 3: Generate kustomization.yaml
cat > "$OVERLAY_DIR/kustomization.yaml" << EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: apps

helmCharts:
  - name: homelab-app
    releaseName: $APP_NAME
    namespace: apps
    valuesFile: values.yaml
    includeCRDs: true
    # Use local chart path relative to this directory
    repo: file://$HELM_CHART_PATH
EOF

echo -e "${GREEN}✓ Created $OVERLAY_DIR/kustomization.yaml${NC}"

# Step 4: Generate values.yaml with interactive prompts (or defaults)
echo ""
echo -e "${YELLOW}Step 3: Generating values.yaml...${NC}"

# Default values
ENABLE_INGRESS="true"
HOSTNAME="${APP_NAME}.${DOMAIN}"
ENABLE_POSTGRES="false"
POSTGRES_STORAGE="1Gi"
ENABLE_MCP="$HAS_MCP"
HEALTH_PATH="/health"
TARGET_PORT="8000"

# Check if running interactively
if [ -t 0 ]; then
    # Interactive mode - prompt for values
    read -p "Enable ingress? (Y/n) " -r
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        ENABLE_INGRESS="false"
    fi

    if [ "$ENABLE_INGRESS" = "true" ]; then
        read -p "Hostname [$HOSTNAME]: " -r
        if [ -n "$REPLY" ]; then
            HOSTNAME="$REPLY"
        fi
    fi

    read -p "Enable PostgreSQL? (y/N) " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ENABLE_POSTGRES="true"
        read -p "PostgreSQL storage size [$POSTGRES_STORAGE]: " -r
        if [ -n "$REPLY" ]; then
            POSTGRES_STORAGE="$REPLY"
        fi
    fi

    if [ "$HAS_MCP" = "true" ]; then
        read -p "Enable MCP service? (Y/n) " -r
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            ENABLE_MCP="false"
        fi
    fi

    read -p "Health check path [$HEALTH_PATH]: " -r
    if [ -n "$REPLY" ]; then
        HEALTH_PATH="$REPLY"
    fi

    read -p "Container port [$TARGET_PORT]: " -r
    if [ -n "$REPLY" ]; then
        TARGET_PORT="$REPLY"
    fi
fi

# Generate values.yaml
cat > "$OVERLAY_DIR/values.yaml" << EOF
# Values for $APP_NAME
# Generated by register-app.sh on $(date -u +"%Y-%m-%dT%H:%M:%SZ")

image:
  repository: $REGISTRY/$APP_NAME
  tag: latest
  pullPolicy: Always

service:
  port: 80
  targetPort: $TARGET_PORT

EOF

if [ "$ENABLE_INGRESS" = "true" ]; then
    cat >> "$OVERLAY_DIR/values.yaml" << EOF
ingress:
  enabled: true
  host: $HOSTNAME

EOF
fi

if [ "$ENABLE_MCP" = "true" ]; then
    cat >> "$OVERLAY_DIR/values.yaml" << EOF
mcp:
  enabled: true
  transport: streamable-http

# MCP apps typically use TCP health checks (no /health endpoint)
healthCheck:
  enabled: true
  http:
    enabled: false
  tcp:
    enabled: true
    port: http

EOF
else
    cat >> "$OVERLAY_DIR/values.yaml" << EOF
healthCheck:
  enabled: true
  http:
    enabled: true
    path: $HEALTH_PATH
  tcp:
    enabled: false

EOF
fi

if [ "$ENABLE_POSTGRES" = "true" ]; then
    cat >> "$OVERLAY_DIR/values.yaml" << EOF
postgres:
  enabled: true
  sidecar:
    enabled: true
    storage: $POSTGRES_STORAGE

EOF
fi

cat >> "$OVERLAY_DIR/values.yaml" << EOF
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi
EOF

echo -e "${GREEN}✓ Created $OVERLAY_DIR/values.yaml${NC}"

# Step 5: Optionally build the image
if [ "$BUILD_IMAGE" = "true" ]; then
    echo ""
    echo -e "${YELLOW}Step 4: Building container image...${NC}"

    # Check if buildah is available
    if command -v buildah &> /dev/null; then
        echo "Using buildah to build image..."
        cd "$APP_DIR"
        buildah build -t "$REGISTRY/$APP_NAME:latest" .
        buildah push "$REGISTRY/$APP_NAME:latest"
        echo -e "${GREEN}✓ Built and pushed: $REGISTRY/$APP_NAME:latest${NC}"
    elif command -v docker &> /dev/null; then
        echo "Using docker to build image..."
        cd "$APP_DIR"
        docker build -t "$REGISTRY/$APP_NAME:latest" .
        docker push "$REGISTRY/$APP_NAME:latest"
        echo -e "${GREEN}✓ Built and pushed: $REGISTRY/$APP_NAME:latest${NC}"
    else
        echo -e "${YELLOW}Warning: Neither buildah nor docker found${NC}"
        echo "To build the image later, run:"
        echo "  cd apps/$APP_NAME && docker build -t $REGISTRY/$APP_NAME:latest . && docker push $REGISTRY/$APP_NAME:latest"
        echo ""
        echo "Or use Kaniko in-cluster build (recommended):"
        echo "  kubectl apply -f - <<EOF"
        echo "apiVersion: batch/v1"
        echo "kind: Job"
        echo "metadata:"
        echo "  name: build-$APP_NAME"
        echo "  namespace: kaniko"
        echo "spec:"
        echo "  template:"
        echo "    spec:"
        echo "      containers:"
        echo "      - name: kaniko"
        echo "        image: gcr.io/kaniko-project/executor:latest"
        echo "        args:"
        echo "        - \"--dockerfile=Dockerfile\""
        echo "        - \"--context=git://gitea-http.gitea:3000/homelab/proxmox.git#refs/heads/main\""
        echo "        - \"--context-sub-path=apps/$APP_NAME\""
        echo "        - \"--destination=$REGISTRY/$APP_NAME:latest\""
        echo "      restartPolicy: Never"
        echo "EOF"
    fi
fi

# Summary
echo ""
echo "========================================"
echo -e "${GREEN}Registration complete!${NC}"
echo "========================================"
echo ""
echo "Created files:"
echo "  - $OVERLAY_DIR/kustomization.yaml"
echo "  - $OVERLAY_DIR/values.yaml"
echo ""
echo "Next steps:"
echo "  1. Review the generated values.yaml"
echo "  2. git add -A && git commit -m \"Register $APP_NAME for K8s deployment\""
echo "  3. git push origin main"
echo "  4. ArgoCD will auto-discover and sync the app"
echo ""
if [ "$BUILD_IMAGE" != "true" ]; then
    echo "Note: Image not built. Run with --build flag or build manually."
fi
