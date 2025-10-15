# Nginx Ingress Controller

This directory contains the Nginx Ingress Controller configuration.

## Installation

The ingress controller is installed via the official manifest and will automatically receive a LoadBalancer IP from MetalLB.

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.12.0-beta.0/deploy/static/provider/cloud/deploy.yaml
```

## Getting the Ingress IP

After installation, get the external IP assigned by MetalLB:

```bash
kubectl get svc -n ingress-nginx ingress-nginx-controller
```

Configure this IP in your Pi-hole DNS as a wildcard A record:
```
*.apps.homelab → <INGRESS_IP>
```
