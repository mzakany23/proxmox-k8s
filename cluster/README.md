# Cluster Directory

Everything in this directory gets deployed to Kubernetes. Structure matches deployment order.

## Directory Structure

| Directory | Sync Wave | Purpose |
|-----------|-----------|---------|
| `gitops/argocd/` | - | ArgoCD Application definitions (what to deploy where) |
| `core/` | 1 | Essential infra: metallb, ingress-nginx, cert-manager, sealed-secrets, argocd server |
| `secrets/` | 2 | Centralized SealedSecret resources |
| `platform/` | 3 | Shared services: gitea, monitoring, registry |
| `databases/` | 4 | Stateful services: postgres instances, milvus |
| `apps/` | 5 | User applications using shared Helm chart |

## Key Distinctions

**ArgoCD split:**
- `core/argocd/` = ArgoCD **server** (Deployment, Ingress, RBAC)
- `gitops/argocd/` = ArgoCD **Applications** (what to deploy where)

**Two `apps/` directories:**
- Root `apps/` = Application source code (Python, TypeScript, etc.)
- `cluster/apps/` = Kubernetes manifests for those apps

## Sync Waves

ArgoCD deploys in order: core -> secrets -> platform -> databases -> apps

Each Application in `gitops/argocd/` has sync-wave annotation:
```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "1"  # Lower = deploys first
```

## Adding New Apps

1. Create `cluster/apps/<app-name>/` with:
   - `kustomization.yaml` (references `../../../helm/charts/homelab-app`)
   - `values.yaml` (app-specific Helm values)

2. The ApplicationSet in `gitops/argocd/apps.yaml` auto-discovers new apps.

## Adding Platform Services

1. Create `cluster/platform/<service>/` with manifests
2. Add to `cluster/platform/kustomization.yaml`
3. Create ArgoCD Application in `gitops/argocd/` if needed
