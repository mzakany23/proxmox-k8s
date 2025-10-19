# Gitea Actions CI/CD Setup

Complete CI/CD pipeline using Gitea Actions for building and deploying applications locally.

## Architecture

```
Git Push to Main
    ↓
Gitea detects push
    ↓
Triggers workflow in .gitea/workflows/
    ↓
act_runner picks up job
    ↓
Runs workflow steps (checkout, build with Kaniko, push to registry)
    ↓
Image pushed to registry.home.mcztest.com
    ↓
ArgoCD Image Updater detects new tag
    ↓
Updates manifest and deploys
```

## Components

### 1. Local Container Registry
- **URL**: `registry.home.mcztest.com`
- **Storage**: 20Gi PVC
- **Purpose**: Store locally built images

### 2. Gitea Actions Runner (act_runner)
- **Name**: k8s-runner
- **Mode**: Docker mode (isolated builds)
- **Labels**: ubuntu-latest, ubuntu-22.04
- **Capacity**: 2 concurrent jobs

### 3. Workflow Templates
- Located in `templates/gitea-workflows/`
- Drop into `.gitea/workflows/` in your repos

## Setup Instructions

### Step 1: Run Setup Script

```bash
chmod +x scripts/setup-gitea-actions.sh
./scripts/setup-gitea-actions.sh
```

The script will guide you through:
1. Getting the registration token from Gitea admin panel
2. Creating Kubernetes secret
3. Deploying the act_runner
4. Verifying registration

### Step 2: Verify Runner

1. Open Gitea: https://gitea.home.mcztest.com
2. Go to: Site Administration → Actions → Runners
3. You should see `k8s-runner` with status `idle`

## Using Gitea Actions in Your Repos

### Enable Actions for Repository

1. Go to your repository settings
2. Enable "Enable Repository Actions"

### Add Workflow File

Create `.gitea/workflows/build.yaml` in your repository:

```yaml
name: Build and Push
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build with Kaniko
        uses: docker://gcr.io/kaniko-project/executor:latest
        with:
          args: >
            --dockerfile=Dockerfile
            --context=.
            --destination=registry.home.mcztest.com/${{ gitea.repository }}:${{ gitea.sha }}
            --destination=registry.home.mcztest.com/${{ gitea.repository }}:latest
            --insecure
            --skip-tls-verify
```

### Push and Watch

```bash
git add .gitea/workflows/build.yaml
git commit -m "Add build workflow"
git push

# Watch the workflow run in Gitea
# Go to: Repository → Actions tab
```

## Workflow Templates

### Basic Build and Push

Use `templates/gitea-workflows/build-and-push.yaml`:

```bash
# Copy to your repo
mkdir -p .gitea/workflows
cp templates/gitea-workflows/build-and-push.yaml .gitea/workflows/
```

### Custom Workflows

Common use cases:

#### Build with Tests

```yaml
name: Test and Build
on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: npm test

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        uses: docker://gcr.io/kaniko-project/executor:latest
        with:
          args: --dockerfile=Dockerfile --context=. --destination=registry.home.mcztest.com/my-app:latest
```

#### Build on Tag

```yaml
name: Release Build
on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build release
        uses: docker://gcr.io/kaniko-project/executor:latest
        with:
          args: >
            --dockerfile=Dockerfile
            --context=.
            --destination=registry.home.mcztest.com/my-app:${{ gitea.ref_name }}
```

## Troubleshooting

### Runner Not Appearing

```bash
# Check runner pod
kubectl get pods -n gitea-actions
kubectl logs -n gitea-actions deployment/act-runner

# Check secret
kubectl get secret gitea-runner-token -n gitea-actions -o yaml
```

### Workflow Not Triggering

1. Check Actions are enabled in repo settings
2. Verify workflow file is in `.gitea/workflows/` (not `.github/`)
3. Check runner is idle (not busy): `https://gitea.home.mcztest.com/-/admin/actions/runners`

### Build Failing

```bash
# View workflow logs in Gitea UI
# Repository → Actions → Click on workflow run

# Check runner logs
kubectl logs -n gitea-actions deployment/act-runner -f
```

### Registry Push Failing

```bash
# Verify registry is accessible
curl -k https://registry.home.mcztest.com/v2/

# Check registry pod
kubectl get pods -n container-registry
kubectl logs -n container-registry deployment/docker-registry
```

## Available Context Variables

In your workflows, you can use:

- `${{ gitea.repository }}` - Repository name (e.g., `homelab/my-app`)
- `${{ gitea.sha }}` - Full commit SHA
- `${{ gitea.ref }}` - Branch ref (e.g., `refs/heads/main`)
- `${{ gitea.ref_name }}` - Branch or tag name (e.g., `main`, `v1.0.0`)
- `${{ gitea.actor }}` - User who triggered the workflow

## Best Practices

### Image Tagging

Always tag with both commit SHA and latest:

```yaml
--destination=registry.home.mcztest.com/my-app:${{ gitea.sha }}
--destination=registry.home.mcztest.com/my-app:latest
```

This allows:
- Rollback to specific versions (SHA tags)
- Easy deployment of latest (latest tag)
- ArgoCD Image Updater to track changes

### Caching

Enable Kaniko caching for faster builds:

```yaml
--cache=true
--cache-repo=registry.home.mcztest.com/cache
```

### Security

- Runner runs in isolated Docker containers
- No credentials stored in workflows
- Registry is internal-only (no internet exposure)

## Next Steps

After setting up Gitea Actions:

1. Install ArgoCD Image Updater (automatically updates deployments on new images)
2. Configure App Registry API (track deployed apps)
3. Update dashboard to show deployed apps dynamically

See main README for complete setup guide.
