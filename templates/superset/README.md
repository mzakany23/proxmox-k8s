# Apache Superset Template

This directory contains the Helm chart configuration and generated Kubernetes manifests for Apache Superset.

## Overview

Apache Superset is deployed to the homelab k8s cluster with:
- PostgreSQL database for metadata storage (included)
- Redis for caching and Celery message broker (included)
- Nginx Ingress with cert-manager TLS
- API access enabled for programmatic dashboard/dataset creation

## Files

- `values.yaml`: Custom Helm chart values for homelab environment
- `manifests.yaml`: Generated Kubernetes manifests (auto-generated, do not edit directly)
- `README.md`: This file

## Initial Setup

These manifests were generated using:

```bash
# Add Superset Helm repository
helm repo add superset https://apache.github.io/superset
helm repo update

# Generate manifests
helm template superset superset/superset \
  --values values.yaml \
  --namespace superset \
  > manifests.yaml
```

## Deploying to Cluster

Use the automated GitOps deployment script:

```bash
# From repository root
./scripts/deploy-app-gitea.sh superset
```

This will:
1. Create a Gitea repository named 'superset'
2. Push the manifests to the repo
3. Create an ArgoCD Application
4. Add DNS entry to Pi-hole for superset.apps.homelab

## Manual Deployment (Alternative)

```bash
# Create namespace
kubectl create namespace superset

# Apply manifests
kubectl apply -f manifests.yaml -n superset

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=superset -n superset --timeout=300s
```

## Accessing Superset

- URL: https://superset.apps.homelab
- Username: `admin`
- Password: `admin` (change after first login)

## API Access

Superset provides a REST API for programmatic access:

### Authentication

```bash
# Get access token
curl -X POST https://superset.apps.homelab/api/v1/security/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin",
    "provider": "db",
    "refresh": true
  }'
```

### Example API Calls

See the main documentation for API examples:
- Creating databases
- Creating datasets
- Creating charts
- Creating dashboards

## Updating the Deployment

To update Superset version or configuration:

```bash
# 1. Update values.yaml with desired changes

# 2. Regenerate manifests
helm template superset superset/superset \
  --values values.yaml \
  --namespace superset \
  > manifests.yaml

# 3. Commit and push to Gitea
git add .
git commit -m "Update Superset configuration"
git push

# 4. ArgoCD will auto-sync within 3 minutes
# Or manually sync:
kubectl -n argocd patch app superset --type json \
  -p='[{"op": "replace", "path": "/operation", "value": {"sync": {"revision": "main"}}}]'
```

## Helm Chart Information

- Chart Repository: https://apache.github.io/superset
- Chart Documentation: https://github.com/apache/superset/tree/master/helm/superset
- Upstream Docs: https://superset.apache.org/docs/installation/kubernetes/

## Configuration Notes

### PostgreSQL
- Included PostgreSQL instance (not for production use at scale)
- Database: `superset`
- Username: `superset`
- Password: `superset`
- Persistence: 8Gi PVC

### Redis
- Included Redis instance
- No authentication (cluster-internal only)
- Persistence: 2Gi PVC

### Resources
- Web nodes: 512Mi-1Gi memory, 250m-500m CPU
- Workers: 512Mi-1Gi memory, 250m-500m CPU

For production, consider:
- External managed PostgreSQL
- External managed Redis
- Increased replica counts
- Resource limit adjustments
