# Automation Scripts

Helper scripts for deploying applications with GitOps.

## Quick Start

### One-Command Deployment (Gitea + ArgoCD)

Deploy a complete app from template to running with HTTPS in one command:

```bash
./scripts/deploy-app-gitea.sh my-api
```

This will:
1. ✅ Create private repo in Gitea
2. ✅ Initialize with app template
3. ✅ Create ArgoCD Application
4. ✅ Add DNS entry
5. ✅ App running at `https://my-api.apps.homelab`

## Individual Scripts

### Gitea Repository Management

#### Create Repository
```bash
./scripts/gitea-create-repo.sh <repo-name> [description] [private]
```

Examples:
```bash
# Create private repo
./scripts/gitea-create-repo.sh my-app "My application" true

# Create public repo
./scripts/gitea-create-repo.sh public-app "Public app" false
```

#### Setup Repository with Template
```bash
./scripts/gitea-setup-repo.sh <repo-name> <template>
```

Templates:
- `basic-app` - Full Kubernetes app (deployment, service, ingress)
- `empty` - Empty repository with README

Example:
```bash
./scripts/gitea-setup-repo.sh my-api basic-app
```

This creates the repo, initializes it with the template, and pushes to Gitea.

#### Add Gitea to ArgoCD
```bash
./scripts/gitea-add-to-argocd.sh
```

One-time setup to add Gitea credentials to ArgoCD. After this, all Gitea repos can be used in ArgoCD Applications.

### ArgoCD Application Management

#### Create ArgoCD Application
```bash
./scripts/create-argocd-app.sh <app-name> [path] [namespace]
```

Examples:
```bash
# App manifests in repo root
./scripts/create-argocd-app.sh my-api . default

# App manifests in subdirectory
./scripts/create-argocd-app.sh my-api k8s/ default

# Deploy to custom namespace
./scripts/create-argocd-app.sh my-api . production
```

### DNS Management

#### Add DNS Entry
```bash
./scripts/add-dns.sh <app-name>
```

Adds `<app-name>.apps.homelab → 192.168.200.100` to Pi-hole.

Example:
```bash
./scripts/add-dns.sh my-api
# Adds: my-api.apps.homelab → 192.168.200.100
```

### Legacy (GitHub-based)

#### Create App from Template
```bash
./scripts/create-app.sh <app-name> <image>
```

Creates app manifests in this GitHub repo. Use `deploy-app-gitea.sh` instead for private Gitea repos.

## Complete Workflows

### Workflow 1: Deploy New App (Gitea - Recommended)

```bash
# One command does everything
./scripts/deploy-app-gitea.sh my-new-app

# Wait ~30 seconds, then access
open https://my-new-app.apps.homelab
```

### Workflow 2: Deploy from Existing Gitea Repo

```bash
# Repo already exists in Gitea
./scripts/create-argocd-app.sh existing-app k8s/ default
./scripts/add-dns.sh existing-app
```

### Workflow 3: Create Empty Private Repo

```bash
# Create empty repo
./scripts/gitea-setup-repo.sh my-project empty

# Clone and add your files
git clone https://gitea.apps.homelab/homelab/my-project.git
cd my-project
# ... add your files ...
git add .
git commit -m "Add project files"
git push

# Deploy with ArgoCD
./scripts/create-argocd-app.sh my-project
./scripts/add-dns.sh my-project
```

## First-Time Setup

### 1. Ensure Gitea is Running

```bash
kubectl get pods -n gitea
# Should show gitea and postgres pods running
```

If not deployed:
```bash
kubectl apply -f kubernetes/apps/gitea/
./scripts/add-dns.sh gitea
```

### 2. Add Gitea to ArgoCD (One-Time)

```bash
./scripts/gitea-add-to-argocd.sh
```

This adds your Gitea credentials to ArgoCD so it can pull from private repos.

### 3. Deploy Your First App

```bash
./scripts/deploy-app-gitea.sh my-first-app
```

## Credentials

### Gitea
- URL: https://gitea.apps.homelab
- Username: `homelab`
- Password: `homelab123`

### ArgoCD
- URL: https://argocd.apps.homelab
- Username: `admin`
- Password: `kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 --decode`

## Troubleshooting

### Script fails with "repo already exists"

Delete the repo in Gitea UI first, or use a different name.

### ArgoCD can't access Gitea repo

Make sure you've run:
```bash
./scripts/gitea-add-to-argocd.sh
```

### DNS not resolving

Check Pi-hole has the entry:
```bash
ssh pi "cat /etc/hosts | grep apps.homelab"
```

Manually add if needed:
```bash
./scripts/add-dns.sh <app-name>
```

### App not syncing in ArgoCD

Check application status:
```bash
kubectl get application -n argocd <app-name>
argocd app get <app-name>
```

Force sync:
```bash
argocd app sync <app-name>
```

## Examples

### Deploy a Python API

```bash
# Create repo with template
./scripts/gitea-setup-repo.sh python-api basic-app

# Clone and customize
git clone https://gitea.apps.homelab/homelab/python-api.git
cd python-api

# Update image in deployment.yaml
sed -i '' 's|nginx:alpine|python:3.11-slim|g' deployment.yaml

# Commit changes
git add .
git commit -m "Update to Python image"
git push

# Deploy via ArgoCD
./scripts/create-argocd-app.sh python-api
./scripts/add-dns.sh python-api

# Access at https://python-api.apps.homelab
```

### Deploy Multiple Microservices

```bash
# Deploy all services
for app in api-gateway auth-service user-service; do
  ./scripts/deploy-app-gitea.sh $app
done

# All services get:
# - Private Gitea repo
# - ArgoCD sync
# - Automatic HTTPS
# - DNS entry
```

### Deploy from Subdirectory

```bash
# Create monorepo
./scripts/gitea-setup-repo.sh monorepo empty

# Clone and add multiple apps
git clone https://gitea.apps.homelab/homelab/monorepo.git
cd monorepo
mkdir -p services/{api,web,worker}
# ... add manifests to each directory ...

# Deploy each service
./scripts/create-argocd-app.sh api services/api default
./scripts/create-argocd-app.sh web services/web default
./scripts/create-argocd-app.sh worker services/worker default
```

## Script Reference

| Script | Purpose | Output |
|--------|---------|--------|
| `deploy-app-gitea.sh` | Complete deployment automation | Running app with HTTPS |
| `gitea-create-repo.sh` | Create Gitea repository | Empty repo |
| `gitea-setup-repo.sh` | Create & initialize repo | Repo with template |
| `gitea-add-to-argocd.sh` | Add Gitea credentials to ArgoCD | ArgoCD can access private repos |
| `create-argocd-app.sh` | Create ArgoCD Application | App syncing from git |
| `add-dns.sh` | Add DNS entry to Pi-hole | DNS resolution |
| `create-app.sh` | Legacy GitHub-based deployment | Manifests in this repo |

## Tips

- **Change Gitea password**: Visit https://gitea.apps.homelab → Settings → Account
- **View repos**: https://gitea.apps.homelab/homelab
- **Monitor ArgoCD**: https://argocd.apps.homelab
- **Check DNS**: `dig <app>.apps.homelab @192.168.200.62`
- **List apps**: `kubectl get applications -n argocd`
