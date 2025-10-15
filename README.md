# Proxmox Kubernetes Cluster with Terraform

Automated 3-node Kubernetes cluster deployment on Proxmox using Terraform and k3s.

## Architecture

- **Control Plane**: 1 node (k8s-control-1)
- **Worker Nodes**: 2 nodes (k8s-worker-1, k8s-worker-2)
- **Kubernetes**: k3s (lightweight Kubernetes)
- **OS**: Ubuntu Server 24.04 LTS

## Prerequisites

1. Proxmox VE 8.x
2. Terraform >= 1.0
3. Proxmox API token with appropriate permissions
4. Ubuntu cloud-init template (VM ID 9000)
5. SSH key pair

## Setup

### 1. Create Proxmox Cloud-Init Template

On your Proxmox host, run:

```bash
# Download Ubuntu 24.04 cloud image
cd /var/lib/vz/template/iso
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img

# Create VM
qm create 9000 --name ubuntu-cloud --memory 2048 --net0 virtio,bridge=vmbr0
qm importdisk 9000 noble-server-cloudimg-amd64.img local-lvm
qm set 9000 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-9000-disk-0
qm set 9000 --ide2 local-lvm:cloudinit
qm set 9000 --boot c --bootdisk scsi0
qm set 9000 --serial0 socket --vga serial0
qm set 9000 --agent enabled=1
qm template 9000
```

### 2. Configure Terraform Variables

Navigate to the terraform directory and create `terraform.tfvars`:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your Proxmox credentials
```

```hcl
proxmox_api_url          = "https://192.168.200.2:8006/api2/json"
proxmox_api_token_id     = "root@pam!terraform"
proxmox_api_token_secret = "your-secret-here"
ssh_public_key_file      = "~/.ssh/id_rsa.pub"
```

### 3. Deploy

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### 4. Access Kubernetes

After deployment completes (~5-10 minutes):

```bash
# Get kubeconfig from control plane
ssh ubuntu@<control-plane-ip> "sudo cat /etc/rancher/k3s/k3s.yaml" > kubeconfig.yaml

# Update server IP in kubeconfig
sed -i '' 's/127.0.0.1/<control-plane-ip>/g' kubeconfig.yaml

# Use it
export KUBECONFIG=$(pwd)/kubeconfig.yaml
kubectl get nodes
```

## Resources Created

- 3 VMs with cloud-init configuration
- Fully configured k3s cluster
- Automatic worker node joining

## Kubernetes Infrastructure

The cluster includes production-ready infrastructure components:

### Installed Components

1. **MetalLB** - LoadBalancer implementation for bare metal
   - IP Pool: `192.168.200.100-192.168.200.110`
   - Provides stable IPs for LoadBalancer services

2. **Nginx Ingress Controller** - HTTP/HTTPS ingress
   - LoadBalancer IP: `192.168.200.100`
   - Handles routing for all applications

3. **cert-manager** - Automated TLS certificate management
   - Self-signed CA for internal HTTPS
   - Automatic certificate provisioning for Ingress resources

### DNS Configuration (Pi-hole)

Add this DNS record to your Pi-hole:

```
*.apps.homelab → 192.168.200.100
```

This routes all `*.apps.homelab` requests to the Ingress Controller.

### Trust the CA Certificate

To avoid browser warnings, install the CA certificate on your devices:

**macOS:**
```bash
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain \
  kubernetes/infrastructure/cert-manager/homelab-ca.crt
```

See `kubernetes/infrastructure/cert-manager/README.md` for other platforms.

### Deploy Applications with HTTPS

Example application with automatic HTTPS:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app
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

Access your app at: `https://my-app.apps.homelab`

### Example Application

A whoami demo app is deployed to test the setup:

```bash
kubectl get pods -l app=whoami
kubectl get ingress whoami
```

Test it: `https://whoami.apps.homelab` (after configuring Pi-hole DNS)

## Project Structure

```
proxmox/
├── README.md                           # This file
├── .gitignore                          # Git ignore rules
├── terraform/                          # Infrastructure as Code
│   ├── main.tf                         # VM resources
│   ├── providers.tf                    # Provider configuration
│   ├── variables.tf                    # Input variables
│   ├── outputs.tf                      # Output values
│   ├── terraform.tfvars                # Your credentials (not in git)
│   ├── terraform.tfvars.example        # Example configuration
│   ├── kubeconfig.yaml                 # Cluster access (not in git)
│   └── cloud-init/                     # Cloud-init templates
│       ├── control-plane.yaml.tpl      # Control plane setup
│       └── worker.yaml.tpl             # Worker node setup
└── kubernetes/                         # Kubernetes manifests
    ├── infrastructure/                 # Core cluster services
    │   ├── metallb/                    # LoadBalancer
    │   ├── ingress-nginx/              # Ingress controller
    │   └── cert-manager/               # Certificate management
    │       ├── homelab-ca.crt          # CA certificate (not in git)
    │       └── *.yaml                  # Configuration files
    └── apps/                           # Application deployments
        └── whoami/                     # Example app
            ├── deployment.yaml
            ├── service.yaml
            └── ingress.yaml
```

## Cleanup

```bash
cd terraform
terraform destroy
```

## Configuration

See `terraform/variables.tf` for customizable options:
- VM resources (CPU, RAM, disk)
- Network configuration
- Node names
- Kubernetes version (via k3s channel)
