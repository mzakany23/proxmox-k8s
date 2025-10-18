# Proxmox Kubernetes Cluster with Terraform

Automated 3-node Kubernetes cluster on Proxmox with k3s, Let's Encrypt HTTPS, and GitOps deployment.

## Table of Contents

- [Quick Start: Deploy a New App](#quick-start-deploy-a-new-app)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
  - [1. Create Proxmox Cloud-Init Template](#1-create-proxmox-cloud-init-template)
  - [2. Configure Cloudflare](#2-configure-cloudflare)
  - [3. Configure Local Environment](#3-configure-local-environment)
  - [4. Configure Terraform](#4-configure-terraform)
  - [5. Deploy Cluster](#5-deploy-cluster)
  - [6. Install Infrastructure](#6-install-infrastructure)
  - [7. Verify Setup](#7-verify-setup)
- [Deploying Applications](#deploying-applications)
  - [Simple Deployment (No GitOps)](#simple-deployment-no-gitops)
  - [Advanced: GitOps with Gitea + ArgoCD](#advanced-gitops-with-gitea--argocd)
- [AI-Assisted Deployments with MCP](#ai-assisted-deployments-with-mcp)
- [Homelab Dashboard](#homelab-dashboard)
- [Local Devices with HTTPS](#local-devices-with-https)
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
- **ArgoCD** - GitOps continuous deployment (optional)
- **Gitea** - Self-hosted Git for private repos (optional)

**Network:**
- Control Plane: 1 node (k8s-control-1)
- Worker Nodes: 2 nodes (k8s-worker-1, k8s-worker-2)
- LoadBalancer IP Pool: Configurable (default: 192.168.68.100-110)
- Ingress Controller: First IP from MetalLB pool
- DNS: Cloudflare wildcard DNS pointing to Ingress IP

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

This repository is configured with dual remotes for maximum flexibility:

**Repository Setup:**
```bash
# Add Gitea as a second remote (if not already added)
git remote add gitea https://gitea.home.example.com/homelab/proxmox-k8s.git

# View all remotes
git remote -v
# origin → GitHub (public/backup)
# gitea  → Gitea (local, watched by ArgoCD)

# Push to both remotes
git push origin main
git push gitea main
```

**GitOps Workflow:**
1. **ArgoCD watches** `kubernetes/infrastructure/` in the Gitea repo
2. **Make infrastructure changes** locally in `kubernetes/infrastructure/`
3. **Commit and push** to both remotes
4. **ArgoCD auto-syncs** changes to cluster within seconds

**Access Points:**
- **Gitea**: `https://gitea.home.example.com` (homelab / homelab123)
- **ArgoCD**: `https://argocd.home.example.com` (admin / see bootstrap output)

**Initial Setup:**
1. Run `./scripts/bootstrap-gitops.sh` (installs ArgoCD and Gitea)
2. Create `proxmox-k8s` repo in Gitea via web UI
3. Push code: `git push gitea main`
4. ArgoCD Application is pre-configured to watch `kubernetes/infrastructure/`

See `scripts/README.md` for automation scripts.

## AI-Assisted Deployments with MCP

This repository can be configured as an [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server to provide AI assistants with full context about your cluster setup, deployment workflows, and infrastructure configuration.

### Quick Setup

1. **Configure MCP Server** (see `MCP_SETUP.md` for full instructions):
   ```json
   {
     "mcpServers": {
       "proxmox-k8s-homelab": {
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/proxmox"]
       }
     }
   }
   ```

2. **Ask AI for Help** - Once configured, you can get deployment assistance:
   ```
   @proxmox-k8s: Help me deploy a React app with HTTPS to the cluster

   @proxmox-k8s: Show me how to troubleshoot ArgoCD sync failures

   @proxmox-k8s: Walk me through the GitOps workflow for infrastructure changes

   @proxmox-k8s: What's the command to check certificate status?
   ```

The AI will have access to:
- All deployment scripts and templates
- Infrastructure manifests (MetalLB, Ingress, cert-manager, ArgoCD)
- Network configuration and cluster architecture
- GitOps workflow documentation
- Troubleshooting guides

**Benefits:**
- Get step-by-step deployment instructions tailored to your setup
- Troubleshoot issues with full cluster context
- Learn commands and workflows interactively
- Generate custom Kubernetes manifests following your templates

See `MCP_SETUP.md` for detailed configuration instructions.

## Homelab Dashboard

A beautiful landing page showing all your services and devices in one place.

**Access:** https://home.mcztest.com

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
