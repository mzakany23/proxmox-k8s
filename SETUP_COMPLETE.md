# Setup Complete! 🎉

Your Proxmox Kubernetes cluster with automated HTTPS and GitOps is ready!

## What's Been Deployed

### Infrastructure Components (All Running)

✅ **MetalLB** - LoadBalancer IP pool: `192.168.200.100-110`
✅ **Nginx Ingress Controller** - LoadBalancer IP: `192.168.200.100`
✅ **cert-manager** - Self-signed CA for internal HTTPS certificates
✅ **ArgoCD** - GitOps continuous deployment

### Applications (Managed by ArgoCD)

✅ **whoami** - Request inspection tool
✅ **hello-world** - Beautiful demo page with gradient background

## 🚨 REQUIRED: Configure Pi-hole DNS

To access your applications, you need to add ONE wildcard DNS entry to Pi-hole:

### Steps:

1. **Access Pi-hole admin interface**
   - URL: `http://192.168.200.1/admin` (or wherever your Pi-hole is)

2. **Go to Local DNS → DNS Records**

3. **Add this entry:**
   ```
   Domain: apps.homelab
   IP Address: 192.168.200.100
   ```

   If Pi-hole supports wildcards, use:
   ```
   Domain: *.apps.homelab
   IP Address: 192.168.200.100
   ```

4. **If Pi-hole doesn't support wildcards directly:**

   Add a dnsmasq custom configuration:

   - SSH to your Pi-hole host
   - Create file: `/etc/dnsmasq.d/02-homelab.conf`
   - Add this line:
     ```
     address=/apps.homelab/192.168.200.100
     ```
   - Restart dnsmasq: `sudo systemctl restart dnsmasq`

## 🔒 Trust the CA Certificate

To avoid browser security warnings, install the CA certificate on your devices:

### macOS
```bash
cd /Users/michaelzakany/projects/proxmox
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain \
  kubernetes/infrastructure/cert-manager/homelab-ca.crt
```

### Linux (Ubuntu/Debian)
```bash
sudo cp kubernetes/infrastructure/cert-manager/homelab-ca.crt \
  /usr/local/share/ca-certificates/homelab-ca.crt
sudo update-ca-certificates
```

### Windows
1. Double-click `homelab-ca.crt`
2. Install Certificate → Local Machine
3. Place in "Trusted Root Certification Authorities"

### iOS/iPadOS
1. AirDrop the `.crt` file to your device
2. Settings → General → VPN & Device Management → Install
3. Settings → General → About → Certificate Trust Settings → Enable

## 🌐 Access Your Applications

After configuring DNS and trusting the CA:

| Application | URL | Description |
|------------|-----|-------------|
| **Hello World** | https://hello.apps.homelab | Beautiful demo page |
| **whoami** | https://whoami.apps.homelab | Request inspector |
| **ArgoCD** | https://argocd.apps.homelab | GitOps dashboard |

### ArgoCD Login
- Username: `admin`
- Password: `4gUL2ye8fMxxQbM1`
- **⚠️ Change this password after first login!**

## 🚀 Deploy New Applications (GitOps Workflow)

### 1. Create Application Manifests

```bash
mkdir -p kubernetes/apps/my-app
```

Create your Kubernetes manifests in `kubernetes/apps/my-app/`:
- `deployment.yaml`
- `service.yaml`
- `ingress.yaml` (with annotation: `cert-manager.io/cluster-issuer: homelab-ca-issuer`)

### 2. Create ArgoCD Application

Create `kubernetes/infrastructure/argocd/app-my-app.yaml`:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
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
```

### 3. Deploy

```bash
# Commit and push to GitHub
git add .
git commit -m "Add my-app"
git push origin main

# Apply ArgoCD Application
kubectl apply -f kubernetes/infrastructure/argocd/app-my-app.yaml

# Watch deployment
kubectl get pods -w
```

### 4. Access Your App

Visit: `https://my-app.apps.homelab`

## 📊 Cluster Status

View all components:

```bash
# Switch to cluster context
ctx local-proxmox-cluster

# View all pods
kubectl get pods -A

# View applications
kubectl get applications -n argocd

# View ingress resources
kubectl get ingress -A

# View certificates
kubectl get certificate -A
```

## 🔧 Useful Commands

```bash
# Check MetalLB IP assignments
kubectl get svc -A | grep LoadBalancer

# Check cert-manager certificates
kubectl get certificate -A

# Check ArgoCD sync status
kubectl get applications -n argocd

# View ArgoCD UI
open https://argocd.apps.homelab

# Get ArgoCD admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 --decode
```

## 📚 Documentation

- Main README: `README.md`
- cert-manager: `kubernetes/infrastructure/cert-manager/README.md`
- ArgoCD: `kubernetes/infrastructure/argocd/README.md`
- Nginx Ingress: `kubernetes/infrastructure/ingress-nginx/README.md`

## 🎯 Next Steps

1. **Configure Pi-hole DNS** (required to access apps)
2. **Trust the CA certificate** on your devices
3. **Change ArgoCD admin password**
4. **Deploy your first application** using the GitOps workflow
5. **Optional:** Set up automated backups with Velero
6. **Optional:** Add monitoring with Prometheus + Grafana
7. **Optional:** Add logging with Loki

## 🔍 Troubleshooting

### Can't access applications
- ✅ Verify Pi-hole DNS is configured: `nslookup hello.apps.homelab`
- ✅ Check ingress has IP: `kubectl get ingress`
- ✅ Check pods are running: `kubectl get pods`

### Certificate warnings in browser
- ✅ Install the CA certificate on your device
- ✅ Verify certificate is trusted: `security verify-cert -c homelab-ca.crt` (macOS)

### ArgoCD app not syncing
- ✅ Check GitHub repo is accessible
- ✅ Check ArgoCD logs: `kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server`
- ✅ Force sync: `argocd app sync <app-name>`

## 🏆 What You've Built

A production-ready Kubernetes homelab with:
- **Automated HTTPS** for all applications
- **GitOps deployments** - push to git, apps auto-deploy
- **Self-healing** - ArgoCD ensures cluster matches git
- **Load balancing** - MetalLB provides stable IPs
- **Certificate management** - cert-manager handles TLS automatically
- **Ingress routing** - Nginx routes traffic to the right apps

Enjoy your cluster! 🚀
