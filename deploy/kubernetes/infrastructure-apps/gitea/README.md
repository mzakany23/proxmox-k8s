# Gitea - Self-Hosted Git Service

Gitea is a lightweight, self-hosted Git service. This deployment includes PostgreSQL database and automatic HTTPS.

## Features

- ✅ Self-hosted Git repositories
- ✅ Web UI for repository management
- ✅ SSH and HTTPS git access
- ✅ Pull requests, issues, wiki
- ✅ Organizations and teams
- ✅ Webhooks for CI/CD
- ✅ PostgreSQL database backend
- ✅ Automatic HTTPS with cert-manager

## Deployment

### 1. Deploy Gitea

```bash
# Apply all manifests
kubectl apply -f kubernetes/apps/gitea/

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=gitea -n gitea --timeout=300s
kubectl wait --for=condition=ready pod -l app=postgres -n gitea --timeout=300s
```

### 2. Add DNS Entry

```bash
ssh pi "echo '192.168.200.100 gitea.apps.homelab' | sudo tee -a /etc/hosts && sudo pihole reloaddns"
```

### 3. Access Gitea

Open https://gitea.apps.homelab

### 4. Initial Setup

On first access, complete the installation:

1. **Database Settings** (pre-filled):
   - Database Type: PostgreSQL
   - Host: postgres:5432
   - Username: gitea
   - Password: gitea
   - Database Name: gitea

2. **General Settings**:
   - Site Title: Homelab Git
   - Repository Root Path: /data/git/repositories
   - Git LFS Root Path: /data/git/lfs
   - Run As Username: git

3. **Server and Third-Party Service Settings**:
   - Server Domain: gitea.apps.homelab
   - SSH Server Domain: gitea.apps.homelab
   - Gitea Base URL: https://gitea.apps.homelab/
   - SSH Server Port: 22

4. **Administrator Account**:
   - Create your admin account
   - Username: admin (or your choice)
   - Password: (choose a strong password)
   - Email: your@email.com

5. Click **Install Gitea**

## Using Gitea

### Create a New Repository

1. Log in to Gitea
2. Click "+" → "New Repository"
3. Fill in repository details
4. Click "Create Repository"

### Clone via HTTPS

```bash
git clone https://gitea.apps.homelab/username/repo.git
cd repo
```

### Clone via SSH

First, add your SSH key to Gitea:
1. Gitea → Settings → SSH / GPG Keys → Add Key
2. Paste your public key (`cat ~/.ssh/id_rsa.pub`)

Get the SSH LoadBalancer IP:
```bash
kubectl get svc gitea-ssh -n gitea -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
# Should show: 192.168.200.101 (or similar)
```

Clone:
```bash
# Add to ~/.ssh/config:
Host gitea.apps.homelab
  HostName 192.168.200.101  # Use the LoadBalancer IP
  Port 22
  User git
  IdentityFile ~/.ssh/id_rsa

git clone git@gitea.apps.homelab:username/repo.git
```

## Integrate with ArgoCD

### Deploy Apps from Gitea

Create repository in Gitea, then create ArgoCD Application:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://gitea.apps.homelab/username/my-app.git
    targetRevision: main
    path: k8s/
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### Add Gitea Repo to ArgoCD (Private Repos)

**Method 1: Via HTTPS with Token**

1. Create Gitea access token:
   - Gitea → Settings → Applications → Generate New Token
   - Select scopes: repo (all)
   - Copy the token

2. Add to ArgoCD:
   ```bash
   argocd repo add https://gitea.apps.homelab/username/repo.git \
     --username your-username \
     --password <your-token>
   ```

**Method 2: Via SSH**

1. Generate SSH key:
   ```bash
   ssh-keygen -t ed25519 -C "argocd@homelab" -f argocd-gitea -N ""
   ```

2. Add public key to Gitea:
   - Gitea → Settings → SSH / GPG Keys → Add Key
   - Paste content of `argocd-gitea.pub`

3. Add to ArgoCD:
   ```bash
   kubectl create secret generic gitea-ssh \
     --from-file=sshPrivateKey=argocd-gitea \
     --namespace argocd

   kubectl label secret gitea-ssh \
     -n argocd \
     argocd.argoproj.io/secret-type=repository

   argocd repo add git@gitea.apps.homelab:username/repo.git \
     --ssh-private-key-path argocd-gitea
   ```

## Complete GitOps Workflow with Gitea

### 1. Create App Repository in Gitea

```bash
# Create new repo in Gitea UI: my-app

# Clone locally
git clone https://gitea.apps.homelab/username/my-app.git
cd my-app

# Create k8s manifests
mkdir k8s
cp -r /path/to/proxmox/templates/basic-app/* k8s/

# Replace placeholders
find k8s -type f -exec sed -i '' 's/REPLACE_APP_NAME/my-app/g' {} +
find k8s -type f -exec sed -i '' 's|REPLACE_IMAGE|nginx:alpine|g' {} +

# Commit and push
git add .
git commit -m "Initial commit"
git push origin main
```

### 2. Deploy via ArgoCD

```bash
# Create ArgoCD Application
cat > argocd-app.yaml <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://gitea.apps.homelab/username/my-app.git
    targetRevision: main
    path: k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
EOF

kubectl apply -f argocd-app.yaml
```

### 3. Make Changes

```bash
# Edit k8s manifests
vim k8s/deployment.yaml

# Commit and push
git add .
git commit -m "Update deployment"
git push

# ArgoCD automatically detects and deploys within ~3 minutes!
```

## Backup and Restore

### Backup Gitea Data

```bash
# Backup persistent data
kubectl exec -n gitea deployment/gitea -- tar czf /tmp/gitea-backup.tar.gz /data

kubectl cp gitea/$(kubectl get pod -n gitea -l app=gitea -o jsonpath='{.items[0].metadata.name}'):/tmp/gitea-backup.tar.gz \
  ./gitea-backup-$(date +%Y%m%d).tar.gz
```

### Backup Database

```bash
kubectl exec -n gitea deployment/postgres -- \
  pg_dump -U gitea gitea > gitea-db-$(date +%Y%m%d).sql
```

## Webhooks for CI/CD

Configure webhooks in Gitea to trigger CI/CD pipelines:

1. Repository → Settings → Webhooks → Add Webhook
2. Select webhook type (e.g., Gitea, Slack, Discord)
3. Payload URL: Your CI/CD webhook endpoint
4. Trigger events: Push, Pull Request, etc.

## Resource Usage

- **Gitea**: ~256MB RAM, 0.1 CPU
- **PostgreSQL**: ~256MB RAM, 0.1 CPU
- **Total Storage**: ~15GB (5GB DB + 10GB repos)

## Troubleshooting

### Can't access Gitea web UI

```bash
# Check pods
kubectl get pods -n gitea

# Check ingress
kubectl get ingress -n gitea

# Check logs
kubectl logs -n gitea deployment/gitea
```

### SSH clone not working

```bash
# Get SSH service IP
kubectl get svc gitea-ssh -n gitea

# Test SSH connection
ssh -T git@<LOADBALANCER_IP>
```

### Database connection errors

```bash
# Check postgres logs
kubectl logs -n gitea deployment/postgres

# Verify service
kubectl get svc postgres -n gitea

# Test connection from gitea pod
kubectl exec -n gitea deployment/gitea -- nc -zv postgres 5432
```

## Uninstall

```bash
kubectl delete -f kubernetes/apps/gitea/
```

**Note:** This will delete all repositories and data. Backup first!

## Resources

- [Gitea Documentation](https://docs.gitea.io/)
- [Gitea API](https://docs.gitea.io/en-us/api-usage/)
- [ArgoCD Integration](https://argo-cd.readthedocs.io/en/stable/user-guide/private-repositories/)
