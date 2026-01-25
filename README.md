# Proxmox Kubernetes Cluster with Terraform

Enterprise-grade 3-node Kubernetes cluster on Proxmox with k3s, Let's Encrypt HTTPS, SSO authentication, and GitOps deployment.

## Table of Contents

- [Quick Start: Deploy a New App](#quick-start-deploy-a-new-app)
- [Architecture](#architecture)
- [Security & Authentication](#security--authentication)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
  - [1. Create Proxmox Cloud-Init Template](#1-create-proxmox-cloud-init-template)
  - [2. Configure Cloudflare](#2-configure-cloudflare)
  - [3. Configure Local Environment](#3-configure-local-environment)
  - [4. Configure Terraform](#4-configure-terraform)
  - [5. Deploy Cluster](#5-deploy-cluster)
  - [6. Install Infrastructure](#6-install-infrastructure)
  - [7. Verify Setup](#7-verify-setup)
  - [8. Configure SSO Authentication](#8-configure-sso-authentication)
- [Deploying Applications](#deploying-applications)
  - [Simple Deployment (No GitOps)](#simple-deployment-no-gitops)
  - [Advanced: GitOps with Gitea + ArgoCD](#advanced-gitops-with-gitea--argocd)
- [AI-Assisted Deployment Patterns](#ai-assisted-deployment-patterns)
- [Homelab Dashboard](#homelab-dashboard)
- [Local Devices with HTTPS](#local-devices-with-https)
- [User Management](#user-management)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Cleanup](#cleanup)
- [Documentation](#documentation)
- [Features](#features)

## Quick Start: Deploy a New App

```bash
# Deploy frontend app (with HTTPS ingress)
./scripts/deploy-app.sh my-web-app frontend nginx:alpine

# Deploy backend API (internal only)
./scripts/deploy-app.sh my-api backend myregistry.com/api:v1.0
```

Apps are automatically configured with:
- Let's Encrypt trusted HTTPS certificates
- Automatic DNS via Cloudflare
- Kubernetes deployment with 2 replicas
- Resource limits and health checks

## Architecture

**Infrastructure Stack:**
- **Proxmox VE** - Hypervisor hosting 3 VMs
- **Terraform** - Infrastructure as Code for VM provisioning
- **k3s** - Lightweight Kubernetes (1 control plane + 2 workers)
- **MetalLB** - LoadBalancer for bare metal Kubernetes
- **Nginx Ingress** - HTTP/HTTPS routing with TLS termination
- **cert-manager** - Automated Let's Encrypt certificates via Cloudflare DNS-01
- **Authelia** - SSO authentication with 2FA (WebAuthn/TOTP)
- **Redis** - Session storage for Authelia
- **Sealed Secrets** - Encrypted secrets management (safe for Git)
- **ArgoCD** - GitOps continuous deployment
- **Gitea** - Self-hosted Git for private repos

**Network:**
- Control Plane: 1 node (k8s-control-1)
- Worker Nodes: 2 nodes (k8s-worker-1, k8s-worker-2)
- LoadBalancer IP Pool: Configurable (default: 192.168.68.100-110)
- Ingress Controller: First IP from MetalLB pool
- DNS: Cloudflare wildcard DNS pointing to Ingress IP

## Security & Authentication

This cluster implements **enterprise-grade security** with Single Sign-On (SSO) and Two-Factor Authentication (2FA) for all services.

### Authentication Flow

1. **User accesses any service** → Redirected to Authelia login (`https://auth.home.example.com`)
2. **Enter credentials** → Username + Password
3. **Complete 2FA** → WebAuthn (Face ID/Touch ID) or TOTP app
4. **Session established** → Access granted for 12 hours (4-hour inactivity timeout)

### Protected Services

All infrastructure services require authentication:
- **Dashboard** (`home.example.com`) - Homelab landing page
- **ArgoCD** (`argocd.home.example.com`) - GitOps management
- **Gitea** (`gitea.home.example.com`) - Web UI only (git operations use basic auth)
- **Pi-hole** (`pihole.home.example.com`) - DNS management
- **Container Registry** (`registry.home.example.com`) - Docker images
- **App Registry API** (`registry-api.home.example.com`) - Write operations only

### Authentication Bypass Rules

For automation and usability:
- **Git operations** (push/pull) - Use Gitea credentials, bypass SSO
- **Registry API reads** (`/api/v1/apps`, `/health`) - Public for dashboard
- **Future user apps** - Can be configured per-app

### Security Features

- **SSO with 2FA** - Single authentication point for all services
- **WebAuthn Support** - Use Face ID, Touch ID, or security keys (easy for family)
- **TOTP Support** - Traditional authenticator apps (Google Authenticator, Authy)
- **Session Management** - Redis-backed sessions with configurable timeouts
- **Email Notifications** - Gmail SMTP for password resets and 2FA setup
- **Encrypted Secrets** - Sealed Secrets encrypt credentials before Git commit
- **Rate Limiting** - Protection against brute force attacks
- **Group-Based Access** - Ready for multi-user with role-based permissions

### Default Credentials

**Admin User:**
- URL: `https://auth.home.example.com`
- Username: `admin`
- Password: Set during installation
- Email: Your Gmail address
- **WARNING: Change default password immediately after first login**

### Multi-User Support

Ready to add family members or team members with different permission levels:
- **Admin Group** - Full access to all services
- **Family Group** - Access to user applications only (future)
- **Developer Group** - Access to Gitea, Registry, ArgoCD (future)

See [User Management](#user-management) section for adding users.

## Prerequisites

1. **Proxmox VE 8.x**
2. **Terraform >= 1.0**
3. **Proxmox API token** with VM provisioning permissions
4. **Ubuntu cloud-init template** (VM ID 9000)
5. **SSH key pair**
6. **Domain name on Cloudflare** (free account works)
7. **Cloudflare API token** with DNS edit permissions

## Setup

### 1. Create Proxmox Cloud-Init Template

On your Proxmox host:

```bash
# Download Ubuntu 24.04 cloud image
cd /var/lib/vz/template/iso
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img

# Create VM template
qm create 9000 --name ubuntu-cloud --memory 2048 --net0 virtio,bridge=vmbr0
qm importdisk 9000 noble-server-cloudimg-amd64.img local-lvm
qm set 9000 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-9000-disk-0
qm set 9000 --ide2 local-lvm:cloudinit
qm set 9000 --boot c --bootdisk scsi0
qm set 9000 --serial0 socket --vga serial0
qm set 9000 --agent enabled=1
qm template 9000
```

### 2. Configure Cloudflare

**Create API Token:**
1. Go to https://dash.cloudflare.com/profile/api-tokens
2. Create Token → Use "Edit zone DNS" template
3. Permissions: Zone / DNS / Edit, Zone / Zone / Read
4. Zone Resources: Include / Specific zone / your-domain.com
5. Copy the token

**Create DNS Record:**
1. Go to your domain's DNS settings
2. Add A record: `*.home` → Your Ingress IP (e.g., `192.168.68.100`)
3. Proxy status: DNS only (disable Cloudflare proxy)

### 3. Configure Local Environment

```bash
# Create .env file with your configuration
cp .env.example .env
```

Edit `.env`:
```bash
APP_DOMAIN=home.example.com
CLOUDFLARE_API_TOKEN=your-cloudflare-token-here
LETSENCRYPT_EMAIL=admin@example.com
```

### 4. Configure Terraform

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
proxmox_api_url          = "https://192.168.1.100:8006/api2/json"
proxmox_api_token_id     = "root@pam!terraform"
proxmox_api_token_secret = "your-secret-here"
ssh_public_key_file      = "~/.ssh/id_rsa.pub"
```

### 5. Deploy Cluster

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

Deployment takes 5-10 minutes. Terraform will:
1. Create 3 VMs from cloud-init template
2. Install k3s on control plane
3. Join worker nodes automatically
4. Save kubeconfig to `terraform/kubeconfig.yaml`

### 6. Install Infrastructure

```bash
# From project root
export KUBECONFIG=$(pwd)/terraform/kubeconfig.yaml

# Install MetalLB, Ingress, cert-manager, ArgoCD
./scripts/bootstrap-gitops.sh
```

This installs:
- MetalLB (LoadBalancer)
- Nginx Ingress Controller
- cert-manager with Let's Encrypt
- ArgoCD (GitOps engine)

### 7. Verify Setup

```bash
kubectl get nodes
# All nodes should be Ready

kubectl get svc -n ingress-nginx
# ingress-nginx-controller should have EXTERNAL-IP from MetalLB

kubectl get certificate -A
# Certificates should be Ready
```

### 8. Configure SSO Authentication

The cluster is now protected with Authelia SSO. All infrastructure services require authentication with 2FA.

**First Time Login:**
```bash
# Access Authelia
open https://auth.home.example.com

# Login with admin credentials
# Username: admin
# Password: (set during bootstrap)
```

**Set Up 2FA:**
1. Go to https://auth.home.example.com settings
2. Click "ADD" under "WebAuthn Credentials"
3. Check your email for the verification code
4. Follow prompts to register Face ID/Touch ID or security key

**Session Configuration:**
- Session duration: 12 hours
- Inactivity timeout: 4 hours
- Remember me: 30 days (if checkbox selected)

**Email Notifications:**
- SMTP configured via Gmail
- Password resets sent to your email
- 2FA setup codes delivered via email

All infrastructure services now require authentication:
- Dashboard, ArgoCD, Gitea (web UI), Pi-hole, Registry, Registry API

Git operations (push/pull) bypass SSO and use Gitea credentials.

## Deploying Applications

### Simple Deployment (No GitOps)

```bash
# Frontend app with HTTPS
./scripts/deploy-app.sh my-app frontend nginx:alpine

# Backend service (internal only)
./scripts/deploy-app.sh my-api backend hashicorp/http-echo
```

Your app will be accessible at: `https://my-app.home.example.com`

### Advanced: GitOps with Gitea + ArgoCD

This cluster uses **ArgoCD GitOps** for automated deployment and **ArgoCD PreSync hooks** for building container images without separate CI runners.

#### Repository Setup

**Dual Remote Configuration:**
```bash
# Add Gitea as a second remote (if not already added)
git remote add gitea https://gitea:homelab123@gitea.home.example.com/gitea/homelab.git

# View all remotes
git remote -v
# origin → GitHub (public/backup)
# gitea  → Gitea (local, watched by ArgoCD)

# Push to both remotes
git push origin main  # Backup to GitHub
git push gitea main   # Deploy via ArgoCD
```

#### GitOps Architecture

**ArgoCD Applications:**
1. **`infrastructure`** - Core cluster components (MetalLB, Ingress, cert-manager, ArgoCD)
   - Path: `kubernetes/infrastructure/`
   - Sync: Automated with self-heal enabled

2. **`app-registry`** - Application registry API with automated builds
   - Path: `kubernetes/apps/app-registry/`
   - Sync: Automated with PreSync build hook
   - Image: Built automatically before deployment

**How Deployments Work:**

```
┌─────────────┐    ┌──────────────┐    ┌──────────────────┐    ┌────────────┐
│   Developer │───→│ git push     │───→│ ArgoCD Detects   │───→│  PreSync   │
│   (Local)   │    │ gitea main   │    │    Changes       │    │ Build Hook │
└─────────────┘    └──────────────┘    └──────────────────┘    └────────────┘
                                                                      │
                                                                      ↓
┌─────────────┐    ┌──────────────┐    ┌──────────────────┐    ┌────────────┐
│   Browser   │←───│ Service      │←───│ Deployment       │←───│   Kaniko   │
│   Access    │    │ Routes       │    │  Updated         │    │ Pushes Img │
└─────────────┘    └──────────────┘    └──────────────────┘    └────────────┘
```

#### CI/CD Without Runners

**Traditional CI/CD:** Requires dedicated runners (Gitea Actions, GitHub Actions, Jenkins)
**This Setup:** Uses ArgoCD PreSync hooks - no runners needed!

**How It Works:**
1. **Code Change** - Edit app code (e.g., `kubernetes/apps/app-registry/main.go`)
2. **Commit & Push** - `git add . && git commit -m "Update" && git push gitea main`
3. **ArgoCD Detects** - Polls Gitea every 3 minutes (or manual sync)
4. **PreSync Hook Runs** - `build-job.yaml` creates Kubernetes Job
5. **Kaniko Builds** - Builds image from Git context without Docker daemon
6. **Image Pushed** - To `registry.home.mcztest.com/homelab/app-registry:latest`
7. **Deployment Updates** - ArgoCD applies deployment with new image
8. **Pods Rolling Update** - `imagePullPolicy: Always` pulls latest image

**Example PreSync Hook (build-job.yaml):**
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: build-app-registry
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation
spec:
  template:
    spec:
      containers:
      - name: kaniko
        image: gcr.io/kaniko-project/executor:latest
        args:
        - "--context=git://github.com/user/repo.git#refs/heads/main"
        - "--context-sub-path=kubernetes/apps/app-registry"
        - "--dockerfile=Dockerfile"
        - "--destination=registry.home.example.com/homelab/app-registry:latest"
        - "--skip-tls-verify"
      restartPolicy: Never
```

**Key Files for Builds:**
- `build-job.yaml` - ArgoCD PreSync hook definition
- `kustomization.yaml` - Must include `build-job.yaml` in resources
- `Dockerfile` - Standard multi-stage build
- `deployment.yaml` - Must have `imagePullPolicy: Always`

**Benefits:**
- ✅ No CI runner maintenance (no Gitea Actions, GitHub Actions, etc.)
- ✅ No webhook configuration
- ✅ Declarative - build configuration lives with deployment
- ✅ Kaniko builds without Docker daemon (secure)
- ✅ GitOps native - everything in Git

#### Access Points

- **Gitea**: `https://gitea.home.example.com`
  - Web UI: homelab / homelab123
  - Git operations: Uses basic auth, bypasses SSO

- **ArgoCD**: `https://argocd.home.example.com`
  - Username: admin
  - Password: Retrieved with `kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 --decode`

#### GitOps Workflow

**For Infrastructure Changes:**
```bash
# 1. Edit infrastructure manifests
vim kubernetes/infrastructure/metallb/config.yaml

# 2. Commit and push
git add .
git commit -m "Update MetalLB pool"
git push gitea main
git push origin main  # Optional: backup to GitHub

# 3. ArgoCD auto-syncs within 3 minutes
# Or force sync: kubectl -n argocd patch app infrastructure --type json -p='[{"op": "replace", "path": "/operation", "value": {"sync": {}}}]'
```

**For Application Changes (with build):**
```bash
# 1. Edit application code
vim kubernetes/apps/app-registry/main.go

# 2. Commit and push to Gitea (triggers CI/CD)
git add .
git commit -m "Fix API endpoint"
git push gitea main

# 3. Watch ArgoCD build and deploy
kubectl get jobs -n default -w                    # Watch build job
kubectl rollout status deployment/app-registry -n default

# 4. Verify deployment
curl -sk https://registry-api.home.example.com/health
```

#### Initial Setup

**One-Time Configuration:**
```bash
# 1. Install infrastructure and ArgoCD
./scripts/bootstrap-gitops.sh

# 2. Create Gitea repository
# Go to https://gitea.home.example.com → Create Repository
# Name: proxmox-k8s (or your repo name)

# 3. Add Gitea remote and push
git remote add gitea https://gitea:homelab123@gitea.home.example.com/gitea/homelab.git
git push gitea main

# 4. Create ArgoCD Applications
kubectl apply -f kubernetes/infrastructure/argocd/applications/

# 5. Verify ArgoCD is watching
kubectl get application -n argocd
# infrastructure should show "Synced" and "Healthy"
```

#### Monitoring GitOps

**Check ArgoCD Application Status:**
```bash
# List all applications
kubectl get application -n argocd

# View detailed status
kubectl describe application app-registry -n argocd

# Check sync history
kubectl get application app-registry -n argocd -o jsonpath='{.status.history}'
```

**Check Build Job Execution:**
```bash
# Watch for build jobs
kubectl get jobs -n default -w

# View build logs
kubectl logs -f -l job-name=build-app-registry -n default

# Check build job status
kubectl describe job build-app-registry -n default
```

**ArgoCD Web UI:**
- Visual sync status for all applications
- Git commit history
- Deployment logs and events
- Manual sync/rollback buttons

#### Troubleshooting

**ArgoCD Not Syncing:**
```bash
# Check application status
kubectl get application -n argocd

# View ArgoCD controller logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller --tail=50

# Force manual sync
kubectl -n argocd patch app app-registry --type=merge -p '{"operation":{"initiatedBy":{"username":"admin"},"sync":{}}}'
```

**Build Job Failing:**
```bash
# Check job status
kubectl get jobs -n default

# View job logs
kubectl logs -l job-name=build-app-registry -n default

# Common issues:
# - Git repository not accessible (check URL in build-job.yaml)
# - Dockerfile errors (check Dockerfile syntax)
# - Registry not accessible (check registry credentials)
```

**Image Not Updating:**
```bash
# Ensure imagePullPolicy is Always
kubectl get deployment app-registry -o yaml | grep imagePullPolicy

# Force pod restart to pull new image
kubectl rollout restart deployment/app-registry -n default
```

See `scripts/README.md` for automation scripts.

## AI-Assisted Deployment Patterns

This repository implements a three-layer architecture for AI-assisted infrastructure management using [MCP (Model Context Protocol)](https://modelcontextprotocol.io), skills, and specialized subagents. Each layer serves a distinct purpose and they work together for complex deployments.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Request                             │
│            "Deploy a new Python API to the cluster"             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  SKILLS (Workflow Orchestration)                                │
│  ────────────────────────────────────────────────────────────── │
│  /feature, /commit, /add-app-proxmox, /build-image              │
│  Repeatable multi-step procedures invoked by users              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  SUBAGENTS (Specialized Execution)                              │
│  ────────────────────────────────────────────────────────────── │
│  infra-researcher → infra-planner → infra-executor → validator  │
│  Autonomous agents with focused context and tools               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  MCP SERVERS (Capabilities)                                     │
│  ────────────────────────────────────────────────────────────── │
│  proxmox-k8s        → K8s operations (list_services, deploy)    │
│  proxmox-k8s-homelab → Filesystem access (read, write, search)  │
│  monarch-money      → Financial queries (optional)              │
└─────────────────────────────────────────────────────────────────┘
```

### Layer 1: MCP Servers (Capabilities)

MCP servers expose tools that Claude and subagents can call. Each server has a single, well-defined purpose.

**Registered MCP Servers:**

| Server | Purpose | Example Tools |
|--------|---------|---------------|
| `proxmox-k8s` | Kubernetes infrastructure | `list_services`, `check_health`, `get_deployment_pattern` |
| `proxmox-k8s-homelab` | Filesystem operations | `read_file`, `write_file`, `search_files` |
| `monarch-money` | Financial data (optional) | `get_accounts`, `get_transactions` |

**Setup (Global Registration):**
```bash
# Register MCP servers globally (available in any project)
claude mcp add --scope user --transport stdio proxmox-k8s -- \
  node /path/to/proxmox/mcp-server/dist/index.js

claude mcp add --scope user --transport stdio proxmox-k8s-homelab -- \
  npx -y @modelcontextprotocol/server-filesystem /path/to/proxmox

# Verify registration
claude mcp list
```

**Direct Tool Usage:**
```
# Check cluster health
What services are running in the cluster?
→ Claude calls: mcp__proxmox-k8s__list_services

# Get deployment pattern
How should I deploy a Python API?
→ Claude calls: mcp__proxmox-k8s__get_deployment_pattern
```

### Layer 2: Subagents (Specialized Execution)

Subagents are autonomous agents spawned for complex tasks. They have access to MCP tools and focused context.

**Available Subagents:**

| Subagent | Purpose | When to Use |
|----------|---------|-------------|
| `infra-researcher` | Explore cluster state | "What's deployed?", "Do we have Redis?" |
| `infra-planner` | Design deployment plans | Multi-step deployments, architecture decisions |
| `infra-executor` | Execute approved plans | Apply manifests, run deployments |
| `infra-validator` | Verify deployments | Health checks, DNS verification |
| `git-manager` | Git operations | Commits, branches, PRs |
| `mcp-developer` | Build MCP servers | Create new integrations |

**Example Flow:**
```
User: "Deploy a new monitoring dashboard"

1. infra-researcher  → Checks existing monitoring stack
2. infra-planner     → Creates deployment plan with steps
3. [User approves]
4. infra-executor    → Applies Helm chart and manifests
5. infra-validator   → Verifies pods, ingress, certificates
```

### Layer 3: Skills (Workflow Orchestration)

Skills are prompt templates that orchestrate multi-step workflows. Users invoke them with `/skill-name`.

**Available Skills:**

| Skill | Purpose | Example |
|-------|---------|---------|
| `/feature` | Phased development workflow | `/feature add user authentication` |
| `/commit` | Smart git commits | `/commit` (analyzes changes, writes message) |
| `/add-app-proxmox` | Full app deployment | `/add-app-proxmox my-api` |
| `/build-image` | Container builds with Kaniko | `/build-image my-app` |
| `/checkpoint` | Save progress snapshot | `/checkpoint` |

**Skills vs Direct Commands:**
```
# Direct (one-off):
"Check the health of the grafana service"

# Skill (repeatable workflow):
/add-app-proxmox my-new-api
→ Creates Gitea repo
→ Generates Helm chart from template
→ Creates ArgoCD Application
→ Adds DNS entry
→ Validates deployment
```

### When to Use Each Layer

| Scenario | Recommended Approach |
|----------|---------------------|
| Quick status check | Direct MCP tool call |
| One-off file read | Direct MCP tool call |
| Explore codebase | Subagent (infra-researcher) |
| Plan complex deployment | Subagent (infra-planner) |
| Repeatable workflow | Skill (/add-app-proxmox) |
| Git operations | Subagent (git-manager) or Skill (/commit) |

### Practical Examples

**Example 1: Check Cluster Status**
```
User: "What's running in the cluster?"
Claude: [Calls mcp__proxmox-k8s__list_services]
→ Returns list of services with health status
```

**Example 2: Deploy New Application**
```
User: /add-app-proxmox my-python-api

Skill orchestrates:
1. Spawns infra-researcher to check existing patterns
2. Uses MCP tools to create Gitea repo
3. Generates Helm chart from template
4. Creates ArgoCD Application
5. Spawns infra-validator to verify deployment
```

**Example 3: Troubleshoot Failing Pod**
```
User: "The grafana pod keeps crashing"

Claude spawns infra-researcher:
1. Calls mcp__proxmox-k8s__check_health for grafana
2. Reads pod logs via kubectl
3. Checks resource limits
4. Returns diagnosis and fix
```

### Configuration Files

**MCP Server Registration:** `~/.claude.json`
```json
{
  "mcpServers": {
    "proxmox-k8s": {
      "command": "node",
      "args": ["/path/to/mcp-server/dist/index.js"]
    }
  }
}
```

**Skills Location:** `~/.claude/commands/*.md`

**Subagents Location:** `~/.claude/agents/*.md`

### Benefits

- **Composable**: Mix and match layers based on task complexity
- **Focused**: Each layer has clear responsibility (capabilities → execution → orchestration)
- **Auditable**: MCP provides standardized, traceable tool calls
- **Extensible**: Add new MCP servers, skills, or subagents as needed
- **Efficient**: Direct tool calls for simple tasks, full orchestration for complex ones

## Homelab Dashboard

A beautiful landing page showing all your services and devices in one place.

**Access:** https://home.example.com

**Features:**
- Clean, modern interface with gradient background
- Lists all infrastructure services (ArgoCD, Gitea, etc.)
- Shows local devices with HTTPS access (Proxmox, Pi-hole, etc.)
- Quick links to documentation and cluster info
- Automatic HTTPS with Let's Encrypt
- Mobile responsive

**Customize:**
Edit `kubernetes/apps/dashboard/deployment.yaml` to add your services, then:
```bash
kubectl apply -f kubernetes/apps/dashboard/deployment.yaml
kubectl rollout restart deployment/dashboard
```

See `kubernetes/apps/dashboard/README.md` for details.

## Local Devices with HTTPS

Give your local network devices (Proxmox, Pi-hole, routers, NAS) friendly domain names with automatic HTTPS certificates.

### Quick Start

**1. Scan your network to find devices:**
```bash
./scripts/scan-network.sh
```

**2. Add DNS record (automatic via Cloudflare API):**
```bash
./scripts/add-dns.sh proxmox 192.168.68.2
```

**3. Create ingress with HTTPS:**
```bash
./scripts/add-device.sh proxmox 192.168.68.2 8006 https
kubectl apply -f kubernetes/local-devices/proxmox-ingress.yaml
```

**4. Access with HTTPS:**
```
https://proxmox.home.example.com
```

### Supported Workflows

**Option 1: Automated (Recommended)**
```bash
# One command to add DNS + create ingress
./scripts/add-dns.sh pihole 192.168.68.3
./scripts/add-device.sh pihole 192.168.68.3 80 http
kubectl apply -f kubernetes/local-devices/pihole-ingress.yaml
```

**Option 2: Manual Cloudflare + Script**
- Add DNS record manually in Cloudflare dashboard
- Use `add-device.sh` to create ingress

**Option 3: Full Manual**
- Use pre-made templates in `kubernetes/local-devices/`

### Benefits

- ✅ **Automatic HTTPS** - Let's Encrypt certificates for every device
- ✅ **No device config** - Devices don't need to support HTTPS
- ✅ **Centralized** - Everything managed through Kubernetes
- ✅ **Consistent** - All devices use *.home.example.com pattern

See `kubernetes/local-devices/README.md` for detailed guide with examples.

## Project Structure

```
proxmox/
├── .env                    # Local config (not in git)
├── .env.example            # Configuration template
├── terraform/              # Infrastructure as Code
│   ├── main.tf
│   ├── variables.tf
│   ├── terraform.tfvars   # Your credentials (not in git)
│   ├── kubeconfig.yaml    # Generated (not in git)
│   └── cloud-init/        # VM bootstrap templates
├── kubernetes/
│   ├── infrastructure/    # Core cluster components
│   │   ├── metallb/
│   │   ├── ingress-nginx/
│   │   ├── cert-manager/
│   │   └── argocd/
│   ├── apps/
│   │   └── dashboard/     # Homelab landing page
│   └── local-devices/     # Local device ingresses (Proxmox, etc.)
├── templates/
│   ├── frontend-app/      # App with HTTPS ingress
│   └── backend-app/       # Internal service only
└── scripts/
    ├── bootstrap-gitops.sh  # Install infrastructure
    ├── deploy-app.sh        # Deploy application
    ├── add-dns.sh           # Add Cloudflare DNS record
    ├── add-device.sh        # Create device ingress
    └── scan-network.sh      # Discover network devices
```

## Configuration

### Application Domain

Apps use the domain from `.env`:
```bash
APP_DOMAIN=home.example.com
```

Apps will be accessible at: `app-name.home.example.com`

### Network Settings

Update in `terraform/variables.tf`:
```hcl
network_gateway = "192.168.1.1"
dns_servers     = ["192.168.1.1", "8.8.8.8"]
```

Update MetalLB IP pool in `kubernetes/infrastructure/metallb/config.yaml`:
```yaml
addresses:
- 192.168.1.100-192.168.1.110
```

### VM Resources

Customize in `terraform/variables.tf`:
```hcl
control_plane_config = {
  cores  = 2
  memory = 4096  # MB
  disk   = 20    # GB
}
```

## Troubleshooting

**VMs not getting IPs:**
- Check Proxmox network bridge configuration
- Verify DHCP server is running

**Workers not joining cluster:**
```bash
# SSH to worker
ssh ubuntu@<worker-ip>
sudo journalctl -u k3s-agent -f
```

**Certificates not issuing:**
```bash
kubectl describe certificate -A
kubectl get certificaterequest -A
# Check for DNS or Cloudflare API errors
```

**App not accessible:**
1. Check ingress: `kubectl get ingress -A`
2. Check certificate: `kubectl get certificate`
3. Check DNS: `dig app-name.home.example.com`
4. Verify Cloudflare wildcard DNS points to correct IP

**Authentication Issues:**
```bash
# Check Authelia logs
kubectl logs -n authelia -l app=authelia --tail=50

# Check if rate limited (clear Redis)
kubectl exec -n authelia redis-<pod-name> -- redis-cli FLUSHALL

# Restart Authelia
kubectl delete pod -n authelia -l app=authelia
```

## User Management

The cluster supports multi-user access with group-based permissions. Currently configured with admin-only access.

### Current User

**Admin:**
- Username: `admin`
- Email: Your Gmail address (configured during setup)
- Groups: `admins`
- Access: All services

### Adding Family Members (Future)

To add family users with limited access:

1. **Edit user database** in `kubernetes/infrastructure/authelia/authelia.yaml`:
```yaml
users:
  admin:
    displayname: "Admin User"
    password: "$argon2id$v=19$..."
    email: admin@example.com
    groups:
      - admins

  jane:
    displayname: "Jane Doe"
    password: "$argon2id$v=19$..."  # Generate with authelia hash
    email: jane@example.com
    groups:
      - family
```

2. **Configure access control** in `kubernetes/infrastructure/authelia/config.yaml`:
```yaml
access_control:
  rules:
    # Admin-only infrastructure
    - domain: argocd.home.example.com
      policy: two_factor
      subject: "group:admins"

    # Family can access dashboard and user apps
    - domain: home.example.com
      policy: two_factor
      subject:
        - "group:admins"
        - "group:family"
```

3. **Generate password hash:**
```bash
kubectl run authelia-hash --image=authelia/authelia:latest --rm --restart=Never -- \
  authelia crypto hash generate argon2 --password "user-password"
```

4. **Commit and deploy:**
```bash
git add kubernetes/infrastructure/authelia/
git commit -m "Add new user: jane"
git push && git push gitea main
```

5. **User setup:**
- New user receives email with login details
- First login: https://auth.home.example.com
- Set up WebAuthn (Face ID/Touch ID) for easy 2FA

### Group-Based Access

**Planned Groups:**
- **admins** - Full access (ArgoCD, Gitea, Registry, Pi-hole, all apps)
- **family** - Dashboard + user applications only
- **developers** - Gitea, Registry, ArgoCD (for development team)

Currently only `admins` group is active. Family group structure is ready for future implementation.

## Cleanup

```bash
cd terraform
terraform destroy
```

## Documentation

- `scripts/README.md` - Deployment automation
- `templates/README.md` - Application templates
- `kubernetes/infrastructure/*/README.md` - Component-specific guides

## Features

- **Automated Infrastructure** - One command cluster deployment
- **Enterprise SSO** - Authelia authentication with 2FA for all services
- **WebAuthn/TOTP** - Face ID, Touch ID, or authenticator app support
- **Encrypted Secrets** - Sealed Secrets for safe Git storage
- **Multi-User Ready** - Group-based access control (admin/family/developer)
- **Email Notifications** - Gmail SMTP for password resets and 2FA codes
- **Session Management** - Redis-backed with configurable timeouts
- **Trusted HTTPS** - Let's Encrypt certificates (no browser warnings!)
- **GitOps Ready** - ArgoCD + Gitea for private repos
- **Simple Deployment** - Deploy apps with one script
- **Template System** - Pre-configured frontend/backend templates
- **Production Ready** - Resource limits, health checks, auto-scaling ready
- **Homelab Dashboard** - Beautiful landing page at home.example.com
- **Local Device HTTPS** - Automatic certificates for Proxmox, routers, NAS, etc.
- **Automated DNS** - Manage Cloudflare DNS via API
- **Network Discovery** - Scan and find all devices on your network
- **AI Assistant Ready** - MCP server for Claude and other AI tools
