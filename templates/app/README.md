# App Templates

This directory contains templates for deploying applications to the Kubernetes cluster.

## Structure

```
templates/app/
└── deploy/
    ├── README.md                    # Deploy structure documentation
    ├── docker/
    │   ├── Dockerfile.python        # Python multi-stage build
    │   ├── Dockerfile.node          # Node.js multi-stage build
    │   ├── Dockerfile.go            # Go multi-stage build
    │   ├── Dockerfile.static        # Static site (nginx)
    │   └── .dockerignore            # Common ignore patterns
    ├── helm/
    │   └── app-template/            # Helm chart template
    │       ├── Chart.yaml
    │       ├── values.yaml
    │       └── templates/
    │           ├── _helpers.tpl
    │           ├── NOTES.txt
    │           ├── deployment.yaml
    │           ├── service.yaml
    │           └── ingress.yaml
    └── argocd/
        └── application.yaml         # ArgoCD Application template
```

## Usage

These templates are used by the `/create-app` Claude Code command to generate deployment infrastructure for an application.

### Manual Usage

1. Copy the appropriate Dockerfile to your project's `deploy/docker/Dockerfile`
2. Copy the helm chart template to `deploy/helm/<your-app-name>/`
3. Update `values.yaml` with your app-specific settings
4. Update `application.yaml` with your app name and repo URL

### Automated Usage

Run `/create-app` from your application directory. The command will:
1. Detect your app type (Python, Node, Go, or static)
2. Copy and configure the appropriate Dockerfile
3. Generate a Helm chart with your app name
4. Create an ArgoCD Application manifest

## Placeholders

The templates use these placeholders that need to be replaced:

| Placeholder | Description |
|-------------|-------------|
| `REPLACE_APP_NAME` | Your application name (e.g., `my-app`) |
| `REPLACE_PORT` | The port your application listens on |
| `REPLACE_GITEA_URL` | The Gitea repository URL |

## Required Values

When using these templates, ensure you configure:

- **image.repository**: Your container registry path
- **service.targetPort**: The port your app listens on
- **ingress.hosts[0].host**: Your app's domain name
- **resources**: Appropriate CPU/memory limits for your app
