# Proxmox Kubernetes Cluster with Terraform

Enterprise-grade 3-node Kubernetes cluster on Proxmox with k3s, Let's Encrypt HTTPS, SSO authentication, and GitOps deployment.

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Deploying Applications](#deploying-applications)
- [GitOps Workflow](#gitops-workflow)
- [Monitoring](#monitoring)
- [Local Devices with HTTPS](#local-devices-with-https)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Cleanup](#cleanup)

## Quick Start

```bash
# Deploy a new app with GitOps (creates Gitea repo, ArgoCD app, DNS)
./scripts/deploy-app-gitea.sh my-app

# Or deploy directly without GitOps
./scripts/deploy-app.sh my-web-app frontend nginx:alpine
```

Apps are automatically configured with:
- Let's Encrypt trusted HTTPS certificates
- Automatic DNS via Cloudflare
- Kubernetes deployment with resource limits
- Health checks and rolling updates

## Architecture

### Infrastructure Stack

```
Proxmox VE → Terraform → k3s → GitOps (ArgoCD + Gitea)
```

| Component | Purpose |
|-----------|---------|
| **Proxmox VE** | Hypervisor hosting 3 VMs (1 control plane, 2 workers) |
| **Terraform** | Infrastructure as Code for VM provisioning |
| **k3s** | Lightweight Kubernetes distribution |
| **MetalLB** | LoadBalancer for bare metal Kubernetes |
| **Nginx Ingress** | HTTP/HTTPS routing with TLS termination |
| **cert-manager** | Automated Let's Encrypt certificates via Cloudflare DNS-01 |
| **Sealed Secrets** | Encrypted secrets management (safe for Git) |
| **ArgoCD** | GitOps continuous deployment |
| **Gitea** | Self-hosted Git for private repos |
| **Prometheus** | Metrics collection and alerting |
| **Grafana** | Metrics visualization and dashboards |

### Network

- **Control Plane**: 1 node (k8s-control-1)
- **Worker Nodes**: 2 nodes (k8s-worker-1, k8s-worker-2)
- **LoadBalancer IP Pool**: `192.168.68.100-110` (configurable)
- **Ingress Controller**: `192.168.68.101` (static assignment)
- **DNS**: Cloudflare wildcard DNS pointing to Ingress IP

## Prerequisites

1. **Proxmox VE 8.x** with API access
2. **Terraform >= 1.0**
3. **Ubuntu cloud-init template** (VM ID 9000)
4. **SSH key pair**
5. **Domain on Cloudflare** (free account works)
6. **Cloudflare API token** with DNS edit permissions

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

1. Go to https://dash.cloudflare.com/profile/api-tokens
2. Create Token → Use "Edit zone DNS" template
3. Permissions: Zone / DNS / Edit, Zone / Zone / Read
4. Zone Resources: Include / Specific zone / your-domain.com
5. Add wildcard A record: `*.home` → Your Ingress IP (e.g., `192.168.68.101`)

### 3. Configure Local Environment

```bash
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

Terraform will:
1. Create 3 VMs from cloud-init template
2. Install k3s on control plane
3. Join worker nodes automatically
4. Save kubeconfig to `terraform/kubeconfig.yaml`

### 6. Install Infrastructure

```bash
export KUBECONFIG=$(pwd)/terraform/kubeconfig.yaml

# Bootstrap GitOps infrastructure
./scripts/bootstrap-gitops.sh
```

This installs (via sync-waves):
1. **Core** (wave 1): MetalLB, Nginx Ingress, cert-manager, Sealed Secrets, ArgoCD
2. **Secrets** (wave 2): SealedSecrets for services
3. **Platform** (wave 3): Gitea, Prometheus, Grafana, Registry
4. **Databases** (wave 4): PostgreSQL instances
5. **Apps** (wave 5): MCP servers and user applications

### 7. Verify Setup

```bash
kubectl get nodes                    # All nodes should be Ready
kubectl get svc -A | grep LoadBalancer  # Check MetalLB IPs
kubectl get certificate -A           # Certificates should be Ready
kubectl get application -n argocd    # ArgoCD apps should be Synced
```

## Deploying Applications

### GitOps Workflow (Recommended)

```bash
# One command: creates Gitea repo, ArgoCD app, and DNS entry
./scripts/deploy-app-gitea.sh my-api

# Or step by step:
./scripts/gitea-setup-repo.sh my-api basic-app    # Create repo with template
./scripts/create-argocd-app.sh my-api             # Create ArgoCD Application
./scripts/add-dns.sh my-api                       # Add DNS entry
```

### Direct Deployment (No GitOps)

```bash
# Frontend with HTTPS ingress
./scripts/deploy-app.sh my-app frontend nginx:alpine

# Backend service (internal only)
./scripts/deploy-app.sh my-api backend hashicorp/http-echo
```

Your app will be accessible at: `https://my-app.home.example.com`

## GitOps Workflow

### Repository Structure

This repo uses ArgoCD for GitOps. ArgoCD Applications are defined in `cluster/gitops/argocd/` and point to manifests in other directories.

```
cluster/
├── gitops/argocd/     # ArgoCD Application definitions ONLY
├── core/              # Essential infra (metallb, ingress, cert-manager, argocd server)
├── secrets/           # Centralized SealedSecrets
├── platform/          # Shared services (gitea, monitoring, registry)
├── databases/         # Stateful services (postgres)
└── apps/              # MCP server deployments
```

**Key Distinction:**
- `cluster/core/argocd/` = ArgoCD **server** (Deployment, Ingress, RBAC)
- `cluster/gitops/argocd/` = ArgoCD **Applications** (what to deploy where)

### Deployment Flow

```
git push → ArgoCD detects changes → Syncs to cluster → Ingress routes traffic
```

ArgoCD polls every 3 minutes or sync manually:
```bash
kubectl -n argocd patch app <app-name> --type=merge -p '{"operation":{"sync":{}}}'
```

### Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| ArgoCD | `https://argocd.home.example.com` | admin / `kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" \| base64 -d` |
| Gitea | `https://gitea.home.example.com` | homelab / homelab123 |
| Grafana | `https://grafana.home.example.com` | admin / homelab123 |
| Prometheus | `https://prometheus.home.example.com` | No auth |

## Monitoring

### Prometheus + Grafana Stack

Pre-configured monitoring with:
- Prometheus for metrics collection
- Grafana with Kubernetes dashboards
- Persistent storage for dashboards

```bash
# Check monitoring stack
kubectl get pods -n monitoring
kubectl get ingress -n monitoring
```

Access:
- **Grafana**: `https://grafana.home.example.com` (admin / homelab123)
- **Prometheus**: `https://prometheus.home.example.com`

## Local Devices with HTTPS

Give local network devices (Proxmox, routers, NAS) HTTPS certificates:

```bash
# Scan network for devices
./scripts/scan-network.sh

# Add DNS entry pointing to ingress
./scripts/add-dns.sh proxmox 192.168.68.101

# Create ingress for the device
./scripts/add-device.sh proxmox 192.168.68.2 8006 https

# Access with trusted HTTPS
open https://proxmox.home.example.com
```

## Project Structure

```
proxmox/
├── terraform/              # VM provisioning (Proxmox + cloud-init)
│   ├── main.tf
│   ├── variables.tf
│   └── cloud-init/         # VM bootstrap templates
├── cluster/                # Kubernetes manifests (GitOps managed)
│   ├── gitops/argocd/      # ArgoCD Application definitions
│   ├── core/               # MetalLB, Ingress, cert-manager, ArgoCD server
│   ├── secrets/            # Centralized SealedSecrets
│   ├── platform/           # Gitea, monitoring, registry
│   ├── databases/          # PostgreSQL instances
│   └── apps/               # MCP server deployments
├── helm/charts/            # Shared Helm charts (homelab-app)
├── apps/                   # MCP servers source code
├── scripts/                # Cluster management scripts
├── templates/              # App templates for new deployments
├── .env                    # Local config (not in git)
└── CLAUDE.md               # Developer reference (detailed commands)
```

## Configuration

### Application Domain

Set in `.env`:
```bash
APP_DOMAIN=home.example.com
```

Apps accessible at: `<app-name>.home.example.com`

### Network Settings

**Terraform** (`terraform/variables.tf`):
```hcl
network_gateway = "192.168.1.1"
dns_servers     = ["192.168.1.1", "8.8.8.8"]
```

**MetalLB Pool** (`cluster/core/metallb/config.yaml`):
```yaml
addresses:
- 192.168.68.100-192.168.68.110
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

### VMs Not Getting IPs
- Check Proxmox network bridge configuration
- Verify DHCP server is running

### Workers Not Joining Cluster
```bash
ssh ubuntu@<worker-ip>
sudo journalctl -u k3s-agent -f
```

### ArgoCD Not Syncing
```bash
kubectl get application -n argocd
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller --tail=50
```

### Certificates Not Issuing
```bash
kubectl describe certificate -A
kubectl get certificaterequest -A
```

### App Not Accessible
1. Check ingress: `kubectl get ingress -A`
2. Check certificate: `kubectl get certificate`
3. Check DNS: `dig app-name.home.example.com`
4. Verify Cloudflare wildcard points to Ingress IP

### After Power Cycle

MetalLB may reassign IPs. Critical services have pinned IPs via annotations:
```bash
# Verify IPs are correct
kubectl get svc -A | grep LoadBalancer

# Ingress should be 192.168.68.101
# If wrong, reapply manifests to restore annotations
```

See `CLAUDE.md` for detailed power cycle recovery checklist.

## Cleanup

```bash
cd terraform
terraform destroy
```

## Documentation

- `CLAUDE.md` - Comprehensive developer reference
- `scripts/README.md` - Deployment automation scripts
- `templates/README.md` - Application templates

## Features

- **Automated Infrastructure** - One command cluster deployment
- **Trusted HTTPS** - Let's Encrypt certificates (no browser warnings)
- **GitOps Ready** - ArgoCD + Gitea for private repos
- **Encrypted Secrets** - Sealed Secrets for safe Git storage
- **Monitoring Stack** - Prometheus + Grafana with dashboards
- **Simple Deployment** - Deploy apps with one script
- **Template System** - Pre-configured frontend/backend templates
- **Production Ready** - Resource limits, health checks, rolling updates
- **Local Device HTTPS** - Automatic certificates for network devices
- **AI Assistant Ready** - MCP server for Claude Code integration
