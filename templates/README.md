# Kubernetes Application Templates

This directory contains templates and documentation for deploying applications to your Proxmox Kubernetes cluster with automatic HTTPS.

## Quick Start

### Deploy a New App (5 Steps)

1. **Copy a template**
   ```bash
   cp -r templates/basic-app kubernetes/apps/my-new-app
   ```

2. **Replace placeholders**
   ```bash
   cd kubernetes/apps/my-new-app

   # On macOS
   find . -type f -exec sed -i '' 's/REPLACE_APP_NAME/my-new-app/g' {} +
   find . -type f -exec sed -i '' 's/REPLACE_IMAGE/nginx:alpine/g' {} +

   # On Linux
   find . -type f -exec sed -i 's/REPLACE_APP_NAME/my-new-app/g' {} +
   find . -type f -exec sed -i 's/REPLACE_IMAGE/nginx:alpine/g' {} +
   ```

3. **Create ArgoCD Application**
   ```bash
   cp templates/argocd-apps/application.yaml kubernetes/infrastructure/argocd/app-my-new-app.yaml

   # Edit the file and replace:
   # - REPLACE_APP_NAME → my-new-app
   # - REPLACE_REPO_URL → https://github.com/mzakany23/proxmox-k8s.git
   # - REPLACE_PATH → kubernetes/apps/my-new-app
   ```

4. **Commit and deploy**
   ```bash
   git add .
   git commit -m "Add my-new-app"
   git push

   kubectl apply -f kubernetes/infrastructure/argocd/app-my-new-app.yaml
   ```

5. **Add DNS entry**
   ```bash
   ssh pi "echo '192.168.200.100 my-new-app.apps.homelab' | sudo tee -a /etc/hosts && sudo pihole reloaddns"
   ```

6. **Access your app**
   ```
   https://my-new-app.apps.homelab
   ```

---

## Available Templates

### 1. Basic App (`basic-app/`)

Simple stateless application with deployment, service, and ingress.

**Use for:**
- Web applications
- APIs
- Microservices
- Static sites

**Files:**
- `deployment.yaml` - Application deployment with 2 replicas
- `service.yaml` - ClusterIP service
- `ingress.yaml` - HTTPS ingress with cert-manager
- `kustomization.yaml` - Optional kustomize config

**Example apps:** Nginx, your custom API, frontend apps

---

### 2. Stateful App (`stateful-app/`)

Application with persistent storage using StatefulSet.

**Use for:**
- Databases
- Message queues
- Applications that need persistent data

**Includes:**
- StatefulSet with volumeClaimTemplates
- Headless service
- PersistentVolumeClaim

**Example apps:** PostgreSQL, Redis, MongoDB

---

### 3. Multi-Container App (`multi-container/`)

Pod with multiple containers (sidecar pattern).

**Use for:**
- App + logging sidecar
- App + proxy sidecar
- App + metrics exporter

**Example apps:** App with nginx proxy, app with fluentd logger

---

### 4. ArgoCD Application (`argocd-apps/`)

Template for creating ArgoCD Applications that watch git repositories.

**Use for:**
- Deploying apps from any git repo
- Multi-repo GitOps setups
- External application management

---

## Automatic HTTPS

All templates include the **magic annotation** that enables automatic HTTPS:

```yaml
annotations:
  cert-manager.io/cluster-issuer: homelab-ca-issuer
```

When you deploy an Ingress with this annotation:
1. cert-manager detects it
2. Requests a certificate from the homelab CA
3. Stores it in a Kubernetes Secret
4. Nginx Ingress uses it for HTTPS

**No manual certificate management needed!**

---

## GitOps Workflows

### Workflow 1: Single Repo (This Repo)

**Best for:** All your homelab apps in one place

```
proxmox-k8s/
└── kubernetes/
    └── apps/
        ├── app1/
        ├── app2/
        └── app3/
```

Deploy:
```bash
# Add app manifests
mkdir kubernetes/apps/my-app
# ... add manifests ...

# Create ArgoCD app
kubectl apply -f kubernetes/infrastructure/argocd/app-my-app.yaml

# ArgoCD watches this repo and auto-deploys
```

---

### Workflow 2: Multi-Repo

**Best for:** Each app has its own repository

```
App Repo (github.com/user/my-app)
└── k8s/
    ├── deployment.yaml
    ├── service.yaml
    └── ingress.yaml

Cluster Repo (this repo)
└── kubernetes/infrastructure/argocd/
    └── app-my-app.yaml  # Points to app repo
```

Create ArgoCD app:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  source:
    repoURL: https://github.com/user/my-app.git  # External repo
    path: k8s/
  # ... rest of config
```

---

### Workflow 3: Self-Hosted Git (Gitea in Cluster)

**Best for:** Complete control, private repos, no external dependencies

See `kubernetes/apps/gitea/` for setup instructions.

Benefits:
- Host code in your cluster
- Private repositories
- No external dependencies
- Full control

---

## Adding External Git Repositories to ArgoCD

### Method 1: Public Repos (No Credentials)

Just reference the HTTPS URL:

```yaml
spec:
  source:
    repoURL: https://github.com/user/repo.git
```

### Method 2: Private Repos via SSH

1. **Generate SSH key pair**
   ```bash
   ssh-keygen -t ed25519 -C "argocd@homelab" -f argocd-key -N ""
   ```

2. **Add public key to GitHub/GitLab**
   - GitHub: Settings → SSH Keys → Add SSH key
   - GitLab: Settings → SSH Keys → Add key
   - Gitea: Settings → SSH Keys → Add Key

3. **Add private key to ArgoCD**
   ```bash
   kubectl create secret generic my-repo-ssh \
     --from-file=sshPrivateKey=argocd-key \
     --namespace argocd

   # Label it so ArgoCD finds it
   kubectl label secret my-repo-ssh \
     -n argocd \
     argocd.argoproj.io/secret-type=repository
   ```

4. **Register repository**
   ```bash
   argocd repo add git@github.com:user/repo.git \
     --ssh-private-key-path argocd-key \
     --name my-private-repo
   ```

   Or via YAML:
   ```yaml
   apiVersion: v1
   kind: Secret
   metadata:
     name: my-private-repo
     namespace: argocd
     labels:
       argocd.argoproj.io/secret-type: repository
   type: Opaque
   stringData:
     type: git
     url: git@github.com:user/repo.git
     sshPrivateKey: |
       -----BEGIN OPENSSH PRIVATE KEY-----
       ... your private key ...
       -----END OPENSSH PRIVATE KEY-----
   ```

### Method 3: Private Repos via HTTPS Token

1. **Create personal access token**
   - GitHub: Settings → Developer settings → Personal access tokens
   - GitLab: Settings → Access Tokens
   - Gitea: Settings → Applications → Generate New Token

2. **Add to ArgoCD**
   ```bash
   argocd repo add https://github.com/user/repo.git \
     --username <username> \
     --password <token>
   ```

   Or via Secret:
   ```yaml
   apiVersion: v1
   kind: Secret
   metadata:
     name: my-private-repo
     namespace: argocd
     labels:
       argocd.argoproj.io/secret-type: repository
   type: Opaque
   stringData:
     type: git
     url: https://github.com/user/repo.git
     username: your-username
     password: ghp_yourTokenHere
   ```

### Method 4: Gitea (Self-Hosted) Integration

After deploying Gitea to your cluster:

```bash
# Add Gitea repository
argocd repo add https://gitea.apps.homelab/user/repo.git \
  --username git \
  --password <gitea-token>
```

Or use SSH with Gitea's built-in SSH server.

---

## ArgoCD Application Patterns

### Pattern 1: Auto-Sync Everything

```yaml
syncPolicy:
  automated:
    prune: true
    selfHeal: true
```

**Behavior:** Git is the source of truth. Any changes in git or cluster sync automatically.

**Best for:** Development environments, trusted repos

---

### Pattern 2: Manual Approval

```yaml
syncPolicy: {}  # No automated section
```

**Behavior:** Changes detected but require manual sync via UI or CLI.

**Best for:** Production environments, cautious deployments

**Sync manually:**
```bash
argocd app sync my-app
```

---

### Pattern 3: Auto-Sync with Manual Pruning

```yaml
syncPolicy:
  automated:
    prune: false  # Don't auto-delete
    selfHeal: true
```

**Behavior:** New/updated resources auto-sync, but deletions require manual approval.

**Best for:** Safety-critical applications

---

## Advanced: App of Apps Pattern

Deploy multiple applications with one ArgoCD Application:

```yaml
# kubernetes/infrastructure/argocd/app-of-apps.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: all-apps
  namespace: argocd
spec:
  source:
    repoURL: https://github.com/mzakany23/proxmox-k8s.git
    path: kubernetes/infrastructure/argocd
    targetRevision: main
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

This watches `kubernetes/infrastructure/argocd/` and creates ArgoCD Applications for every YAML file it finds.

**Result:** Add new `app-*.yaml` files, push to git, and apps deploy automatically!

---

## Troubleshooting

### App not syncing?

```bash
# Check application status
kubectl get application -n argocd my-app

# Check detailed status
argocd app get my-app

# Force refresh
argocd app get my-app --refresh

# View sync status
argocd app sync my-app --dry-run
```

### Certificate not working?

```bash
# Check if certificate was created
kubectl get certificate -n default

# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager

# Check certificate details
kubectl describe certificate my-app-tls -n default
```

### DNS not resolving?

```bash
# Test from your Mac
dig my-app.apps.homelab @192.168.200.62

# Add to Pi-hole
ssh pi "echo '192.168.200.100 my-app.apps.homelab' | sudo tee -a /etc/hosts && sudo pihole reloaddns"
```

---

## Helper Scripts

### Create New App from Template

```bash
#!/bin/bash
# Usage: ./create-app.sh my-new-app nginx:alpine

APP_NAME=$1
IMAGE=$2

cp -r templates/basic-app kubernetes/apps/$APP_NAME

find kubernetes/apps/$APP_NAME -type f -exec sed -i '' "s/REPLACE_APP_NAME/$APP_NAME/g" {} +
find kubernetes/apps/$APP_NAME -type f -exec sed -i '' "s|REPLACE_IMAGE|$IMAGE|g" {} +

# Create ArgoCD app
cat > kubernetes/infrastructure/argocd/app-$APP_NAME.yaml <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: $APP_NAME
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/mzakany23/proxmox-k8s.git
    targetRevision: main
    path: kubernetes/apps/$APP_NAME
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
EOF

echo "✅ Created app: $APP_NAME"
echo "Next steps:"
echo "1. Review and customize kubernetes/apps/$APP_NAME/"
echo "2. git add . && git commit -m 'Add $APP_NAME' && git push"
echo "3. kubectl apply -f kubernetes/infrastructure/argocd/app-$APP_NAME.yaml"
echo "4. ssh pi \"echo '192.168.200.100 $APP_NAME.apps.homelab' | sudo tee -a /etc/hosts && sudo pihole reloaddns\""
echo "5. Open https://$APP_NAME.apps.homelab"
```

### Add DNS Entry

```bash
#!/bin/bash
# Usage: ./add-dns.sh my-app

APP=$1
ssh pi "echo '192.168.200.100 $APP.apps.homelab' | sudo tee -a /etc/hosts && sudo pihole reloaddns"
echo "✅ Added DNS: $APP.apps.homelab → 192.168.200.100"
```

---

## Examples

See `kubernetes/apps/` for working examples:
- `whoami/` - Simple request inspector
- `hello-world/` - Custom HTML page
- `gitea/` - Self-hosted Git server (if deployed)

---

## Resources

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [cert-manager Documentation](https://cert-manager.io/docs/)
- [Kubernetes Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [Kustomize](https://kustomize.io/)

---

**Remember:** The magic annotation is `cert-manager.io/cluster-issuer: homelab-ca-issuer` - that's all you need for automatic HTTPS! 🔒
