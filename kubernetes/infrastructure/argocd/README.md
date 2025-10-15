# ArgoCD - GitOps Continuous Deployment

ArgoCD automatically deploys and manages applications from your git repository.

## Access ArgoCD UI

**URL:** `https://argocd.apps.homelab` (after configuring Pi-hole DNS)

**Initial Login:**
- Username: `admin`
- Password: `4gUL2ye8fMxxQbM1`

**Change the password after first login:**
```bash
kubectl -n argocd patch secret argocd-secret \
  -p '{"stringData": {"admin.password": "'$(htpasswd -nbBC 10 "" <new-password> | tr -d ':\n' | sed 's/$2y/$2a/')'"}}'
```

Or use the ArgoCD CLI:
```bash
argocd login argocd.apps.homelab
argocd account update-password
```

## How GitOps Works

1. **Create manifests** in `kubernetes/apps/<app-name>/`
2. **Commit and push** to GitHub
3. **ArgoCD detects changes** and automatically deploys
4. **Self-healing**: If someone manually changes resources in the cluster, ArgoCD will revert to git state
5. **Pruning**: If you delete files from git, ArgoCD will delete them from the cluster

## Deployed Applications

ArgoCD is currently managing:
- **hello-world** - Demo application at `https://hello.apps.homelab`
- **whoami** - Request inspection tool at `https://whoami.apps.homelab`

## Adding New Applications

### Method 1: Create ArgoCD Application Manifest (Recommended)

Create a file in `kubernetes/infrastructure/argocd/app-<name>.yaml`:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://github.com/mzakany23/proxmox-k8s.git
    targetRevision: main
    path: kubernetes/apps/my-app
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
      - CreateNamespace=true
```

Apply it:
```bash
kubectl apply -f kubernetes/infrastructure/argocd/app-my-app.yaml
```

### Method 2: Using ArgoCD UI

1. Go to `https://argocd.apps.homelab`
2. Click "+ NEW APP"
3. Fill in:
   - Application Name: `my-app`
   - Project: `default`
   - Sync Policy: `Automatic`
   - Repository URL: `https://github.com/mzakany23/proxmox-k8s.git`
   - Revision: `main`
   - Path: `kubernetes/apps/my-app`
   - Cluster: `https://kubernetes.default.svc`
   - Namespace: `default`

## Application Template

Create a new app directory structure:

```
kubernetes/apps/my-app/
├── deployment.yaml
├── service.yaml
└── ingress.yaml
```

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: my-app
        image: my-image:latest
        ports:
        - containerPort: 80
```

**service.yaml:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app
  namespace: default
spec:
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 80
```

**ingress.yaml:**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app
  namespace: default
  annotations:
    cert-manager.io/cluster-issuer: homelab-ca-issuer
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - my-app.apps.homelab
    secretName: my-app-tls
  rules:
  - host: my-app.apps.homelab
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: my-app
            port:
              number: 80
```

## ArgoCD CLI

Install the CLI:
```bash
brew install argocd
```

Login:
```bash
argocd login argocd.apps.homelab --username admin --password <password>
```

Useful commands:
```bash
# List applications
argocd app list

# Get app details
argocd app get hello-world

# Sync an application manually
argocd app sync hello-world

# Watch sync status
argocd app wait hello-world

# View application resources
argocd app resources hello-world

# View application logs
argocd app logs hello-world
```

## Sync Policies

### Automatic Sync (Current Configuration)
- ArgoCD automatically syncs when it detects changes in git
- Runs every 3 minutes by default

### Manual Sync
Change `syncPolicy` in the Application manifest:
```yaml
syncPolicy:
  syncOptions:
    - CreateNamespace=true
  # Remove automated section for manual sync
```

## Troubleshooting

### Application not syncing
```bash
# Check application status
kubectl get application -n argocd <app-name> -o yaml

# Check ArgoCD controller logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller

# Force refresh
argocd app get <app-name> --refresh
```

### Application stuck in "OutOfSync"
```bash
# Check diff
argocd app diff <app-name>

# Sync manually
argocd app sync <app-name>
```

## Security Notes

- The ArgoCD UI is accessible via HTTPS with the self-signed CA
- Git repository is public (GitHub)
- For private repos, add SSH keys or tokens to ArgoCD
- Change the default admin password after first login
