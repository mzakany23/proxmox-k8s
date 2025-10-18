# Homelab Dashboard

A beautiful landing page showing all your homelab services and devices.

## Features

- Beautiful responsive design
- Lists all infrastructure services (ArgoCD, Gitea)
- Shows local devices with HTTPS access
- Quick links to documentation and cluster info
- Automatic HTTPS with Let's Encrypt

## Deploy

```bash
kubectl apply -f kubernetes/apps/dashboard/deployment.yaml
```

## Access

After deployment, access at:
```
https://home.mcztest.com
```

## Customize

Edit the ConfigMap in `deployment.yaml` to:
- Add more services
- Change colors/styling
- Update descriptions
- Add your deployed applications

To add a new service, copy a service card and modify:

```html
<a href="https://your-service.home.mcztest.com" class="service-card" target="_blank">
    <div class="service-name">Your Service</div>
    <div class="service-url">your-service.home.mcztest.com</div>
    <div class="service-description">Service description</div>
    <span class="badge">Tag</span>
</a>
```

After editing, redeploy:
```bash
kubectl apply -f kubernetes/apps/dashboard/deployment.yaml
kubectl rollout restart deployment/dashboard
```

## Network Discovery

To find devices on your network:

```bash
# Scan network for all devices
./scripts/scan-network.sh

# Or with nmap directly
nmap -sn 192.168.68.0/24
```

Then add discovered devices using:
```bash
./scripts/add-device.sh <name> <ip> <port> [http|https]
```

## Update

The dashboard is deployed from a ConfigMap, so changes require a restart:

```bash
kubectl apply -f kubernetes/apps/dashboard/deployment.yaml
kubectl rollout restart deployment/dashboard
```
