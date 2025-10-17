#!/bin/bash
# Deploy an application from template
# Usage: ./scripts/deploy-app.sh <app-name> <type> <image> [namespace]
#   type: frontend | backend
#   image: Docker image (e.g., nginx:alpine, myregistry.com/api:v1.0)
#   namespace: Optional namespace (default: default)

set -e

if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <app-name> <type> <image> [namespace]"
    echo ""
    echo "Examples:"
    echo "  # Frontend app (with HTTPS ingress)"
    echo "  $0 my-web-app frontend nginx:alpine"
    echo ""
    echo "  # Backend API (internal only, no ingress)"
    echo "  $0 my-api backend myregistry.com/api:v1.0"
    echo ""
    echo "  # Custom namespace"
    echo "  $0 my-app frontend nginx:alpine prod"
    exit 1
fi

APP_NAME=$1
APP_TYPE=$2
IMAGE=$3
NAMESPACE=${4:-default}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATES_DIR="$PROJECT_ROOT/templates"
DEPLOY_DIR="/tmp/k8s-deploy-$APP_NAME"

# Load configuration from .env if it exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Use APP_DOMAIN from env or default
APP_DOMAIN=${APP_DOMAIN:-"apps.homelab"}

# Validate app type
if [ "$APP_TYPE" != "frontend" ] && [ "$APP_TYPE" != "backend" ]; then
    echo "Error: type must be 'frontend' or 'backend'"
    exit 1
fi

# Select template
if [ "$APP_TYPE" = "frontend" ]; then
    TEMPLATE_DIR="$TEMPLATES_DIR/frontend-app"
    echo "Deploying frontend app: $APP_NAME"
    echo "   Accessible at: https://$APP_NAME.$APP_DOMAIN"
else
    TEMPLATE_DIR="$TEMPLATES_DIR/backend-app"
    echo "Deploying backend app: $APP_NAME"
    echo "   Internal only (no ingress)"
fi

# Create temporary deploy directory
rm -rf "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"

# Copy templates and replace placeholders
echo "📦 Preparing manifests..."
cp -r "$TEMPLATE_DIR"/* "$DEPLOY_DIR/"

# Replace placeholders in all YAML files
find "$DEPLOY_DIR" -name "*.yaml" -exec sed -i '' "s/REPLACE_APP_NAME/$APP_NAME/g" {} \;
find "$DEPLOY_DIR" -name "*.yaml" -exec sed -i '' "s|REPLACE_IMAGE|$IMAGE|g" {} \;
find "$DEPLOY_DIR" -name "*.yaml" -exec sed -i '' "s|REPLACE_DOMAIN|$APP_DOMAIN|g" {} \;

# Update namespace if not default
if [ "$NAMESPACE" != "default" ]; then
    find "$DEPLOY_DIR" -name "*.yaml" -exec sed -i '' "s/namespace: default/namespace: $NAMESPACE/g" {} \;

    # Create namespace if it doesn't exist
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
fi

# Apply manifests
echo "🚀 Deploying to Kubernetes..."
kubectl apply -k "$DEPLOY_DIR"

# Wait for deployment
echo "⏳ Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=120s deployment/$APP_NAME -n "$NAMESPACE" || true

# Show status
echo ""
echo "✅ Deployment complete!"
echo ""
kubectl get pods -n "$NAMESPACE" -l app=$APP_NAME
echo ""

if [ "$APP_TYPE" = "frontend" ]; then
    echo "📝 Next steps:"
    echo "  1. Add DNS entry:"
    echo "     ./scripts/add-dns.sh $APP_NAME"
    echo ""
    echo "  2. Access your app:"
    echo "     https://$APP_NAME.apps.homelab"
else
    echo "📝 Service accessible within cluster at:"
    echo "   http://$APP_NAME.$NAMESPACE.svc.cluster.local"
fi

echo ""
echo "🗑️  To delete: kubectl delete -k $DEPLOY_DIR"

# Clean up
rm -rf "$DEPLOY_DIR"
