# Homelab Platform

A self-hosted platform for running applications, experimenting with infrastructure, and managing local devices. Built on Kubernetes with GitOps workflows and automatic HTTPS.

## Quick Start

Deploy an app by adding a values file:

```bash
# Create app config
mkdir cluster/apps/my-app
cat > cluster/apps/my-app/values.yaml << 'EOF'
image:
  repository: nginx
  tag: alpine

ingress:
  enabled: true
  host: my-app.$APP_DOMAIN
EOF

# Push to trigger deployment
git add . && git commit -m "Add my-app" && git push
```

ArgoCD auto-discovers apps in `cluster/apps/` and deploys them using the shared Helm chart.

## Architecture

Proxmox VMs running a 3-node k3s cluster with GitOps deployment.

```
Proxmox VE → Terraform → k3s → ArgoCD (GitOps)
```

| Component | Purpose |
|-----------|---------|
| **Proxmox VE** | Hypervisor hosting 3 VMs |
| **Terraform** | VM provisioning via cloud-init |
| **k3s** | Lightweight Kubernetes |
| **MetalLB** | LoadBalancer for bare metal |
| **Nginx Ingress** | HTTPS routing |
| **cert-manager** | Let's Encrypt certificates via Cloudflare DNS-01 |
| **ArgoCD** | GitOps - watches git, syncs to cluster |
| **Gitea** | Self-hosted git server |
| **Prometheus + Grafana** | Monitoring |

### Network

- **Nodes**: 1 control plane + 2 workers
- **LoadBalancer Pool**: Configurable IP range for services
- **Ingress IP**: Static assignment for consistent DNS
- **DNS**: Cloudflare wildcard pointing to ingress

## Deploying Apps

Apps live in `cluster/apps/<app-name>/values.yaml`. An ApplicationSet auto-discovers them and renders the shared Helm chart (`helm/charts/homelab-app`).

### Minimal App

```yaml
# cluster/apps/my-app/values.yaml
image:
  repository: nginx
  tag: alpine

ingress:
  enabled: true
  host: my-app.$APP_DOMAIN
```

### MCP Server

```yaml
# cluster/apps/my-mcp/values.yaml
image:
  repository: $REGISTRY/my-mcp
  tag: latest

ingress:
  enabled: true
  host: my-mcp.$APP_DOMAIN

mcp:
  enabled: true
  transport: streamable-http

healthCheck:
  http:
    enabled: false
  tcp:
    enabled: true
```

### With Database

```yaml
# cluster/apps/my-api/values.yaml
image:
  repository: $REGISTRY/my-api
  tag: latest

ingress:
  enabled: true
  host: my-api.$APP_DOMAIN

postgres:
  enabled: true
  external:
    enabled: true
    host: postgres.gitea.svc.cluster.local
    port: 5432
    database: mydb
    existingSecret: my-db-credentials
    passwordKey: password
```

### Deployment Flow

```
git push → ArgoCD detects (polls every 3m) → Syncs to cluster → Ingress routes traffic
```

Manual sync: `argocd app sync <app-name>`

## Project Structure

```
proxmox/
├── terraform/           # VM provisioning
├── cluster/
│   ├── gitops/argocd/   # ArgoCD ApplicationSets
│   ├── core/            # MetalLB, Ingress, cert-manager, ArgoCD
│   ├── platform/        # Gitea, monitoring, registry
│   ├── databases/       # PostgreSQL
│   └── apps/            # Your apps (values.yaml per app)
├── helm/charts/         # Shared Helm chart (homelab-app)
├── apps/                # App source code
└── scripts/             # Utilities
```

## Setup

### Prerequisites

- Proxmox VE 8.x with API access
- Terraform >= 1.0
- Ubuntu cloud-init template (VM ID 9000)
- Domain on Cloudflare

### 1. Create Cloud-Init Template

On Proxmox host:

```bash
cd /var/lib/vz/template/iso
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img

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

1. Create API token at https://dash.cloudflare.com/profile/api-tokens
2. Permissions: Zone / DNS / Edit, Zone / Zone / Read
3. Add wildcard A record: `*.<subdomain>` → your ingress IP

### 3. Configure Environment

```bash
cp .env.example .env
# Edit: APP_DOMAIN, CLOUDFLARE_API_TOKEN, LETSENCRYPT_EMAIL

cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit: proxmox_api_url, proxmox_api_token_id, proxmox_api_token_secret
```

### 4. Deploy

```bash
cd terraform
terraform init && terraform apply

export KUBECONFIG=$(pwd)/kubeconfig.yaml
./scripts/bootstrap-gitops.sh
```

### 5. Verify

```bash
kubectl get nodes                        # All Ready
kubectl get application -n argocd        # All Synced
```

## Access

Services are available at `<service>.$APP_DOMAIN`:
- **ArgoCD** - GitOps dashboard
- **Gitea** - Git repositories
- **Grafana** - Metrics dashboards
- **Prometheus** - Metrics collection

ArgoCD password: `kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d`

## Local Devices with HTTPS

Give network devices (Proxmox, routers, NAS) trusted certificates:

```bash
./scripts/add-dns.sh proxmox $INGRESS_IP
./scripts/add-device.sh proxmox <device-ip> 8006 https
```

Access at: `https://proxmox.$APP_DOMAIN`

## Troubleshooting

**ArgoCD not syncing:**
```bash
kubectl get application -n argocd
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller --tail=50
```

**Certificate not issuing:**
```bash
kubectl describe certificate -A
kubectl get certificaterequest -A
```

**App not accessible:**
1. `kubectl get ingress -A`
2. `kubectl get certificate`
3. `dig app.$APP_DOMAIN`

**After power cycle:**
```bash
kubectl get svc -A | grep LoadBalancer  # Verify ingress IP matches DNS
```

## Cleanup

```bash
cd terraform && terraform destroy
```
