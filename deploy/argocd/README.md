# ArgoCD Configuration

This directory contains ArgoCD Application definitions for the homelab cluster.

## ApplicationSet: homelab-apps

The `apps.yaml` ApplicationSet auto-discovers applications from `deploy/kubernetes/overlays/`.

### How it works:

1. ArgoCD watches the `deploy/kubernetes/overlays/` directory
2. Each subdirectory becomes an ArgoCD Application
3. The directory name becomes the application name
4. Applications auto-sync with prune and self-heal enabled

### Adding a new app:

1. Migrate source code to `apps/<app-name>/`
2. Run `./deploy/scripts/register-app.sh <app-name>`
3. This creates `deploy/kubernetes/overlays/<app-name>/`
4. Push to git - ArgoCD auto-discovers and syncs

### Directory structure:

```
deploy/kubernetes/overlays/<app-name>/
├── kustomization.yaml   # References homelab-app Helm chart
└── values.yaml          # App-specific Helm values
```

### Verifying:

```bash
# List all ApplicationSet-generated apps
kubectl get applications -n argocd -l homelab.mcztest.com/type=app

# Check specific app status
argocd app get <app-name>

# Force sync
argocd app sync <app-name>
```
