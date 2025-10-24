#!/bin/bash
set -e

echo "🔨 Building app-registry..."

# Delete old job if exists
kubectl delete job build-app-registry -n default 2>/dev/null || true

# Apply build job
kubectl apply -f kubernetes/apps/app-registry/build-job.yaml

# Wait for completion
echo "⏳ Waiting for build to complete..."
kubectl wait --for=condition=complete job/build-app-registry -n default --timeout=180s

# Restart deployment
echo "🔄 Restarting app-registry deployment..."
kubectl rollout restart deployment/app-registry -n default

# Wait for rollout
kubectl rollout status deployment/app-registry -n default --timeout=60s

echo "✅ App registry built and deployed successfully!"
echo ""
echo "API: https://registry-api.home.mcztest.com/api/v1/apps"
echo "Dashboard: https://home.mcztest.com"
