# Deploy Structure

This directory contains the deployment configuration for the application.

## Structure

```
deploy/
├── docker/
│   └── Dockerfile        # Container build instructions
├── helm/<app-name>/
│   ├── Chart.yaml        # Helm chart metadata
│   ├── values.yaml       # Default configuration values
│   └── templates/
│       ├── _helpers.tpl  # Template helper functions
│       ├── NOTES.txt     # Post-install notes
│       ├── deployment.yaml
│       ├── service.yaml
│       └── ingress.yaml
└── argocd/
    └── application.yaml  # ArgoCD Application manifest
```

## Docker

The `docker/` directory contains the Dockerfile for building the container image.

### Building locally

```bash
docker build -f deploy/docker/Dockerfile -t my-app:latest .
```

### Multi-stage builds

All Dockerfile templates use multi-stage builds to minimize final image size:
1. **Builder stage**: Compiles/installs dependencies
2. **Runtime stage**: Minimal image with only runtime requirements

## Helm Chart

The `helm/<app-name>/` directory contains the Kubernetes manifests as a Helm chart.

### Testing locally

```bash
# Render templates
helm template my-app ./deploy/helm/my-app

# Install to cluster
helm install my-app ./deploy/helm/my-app

# Upgrade existing release
helm upgrade my-app ./deploy/helm/my-app
```

### Key Configuration (values.yaml)

```yaml
image:
  repository: registry.home.mcztest.com/my-app
  tag: "latest"
  pullPolicy: Always

service:
  port: 80
  targetPort: 8000  # Your app's listening port

ingress:
  enabled: true
  hosts:
    - host: my-app.mcztest.com

resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "256Mi"
    cpu: "200m"
```

## ArgoCD

The `argocd/` directory contains the ArgoCD Application manifest.

### Manual deployment

```bash
kubectl apply -f deploy/argocd/application.yaml
```

### What ArgoCD does

1. Watches the Gitea repository for changes
2. Automatically syncs Helm chart changes to the cluster
3. Manages rollbacks and health checks

## Workflow

1. **Build**: Push code to Gitea → Kaniko builds container image
2. **Deploy**: ArgoCD detects Helm chart changes → syncs to cluster
3. **Route**: Ingress routes `<app>.mcztest.com` to the service
4. **TLS**: cert-manager provides Let's Encrypt certificates
