# Local Device DNS with HTTPS

Give your local network devices (Proxmox, Pi-hole, routers, NAS, etc.) friendly domain names with automatic HTTPS certificates.

## How It Works

Use Kubernetes Ingress to proxy external devices, providing:
- **Automatic Let's Encrypt HTTPS** certificates
- **Consistent domain pattern** (everything under *.home.mcztest.com)
- **Centralized access** through the ingress controller
- **No device configuration needed** (devices don't need to support HTTPS)

**Traffic Flow:**
```
Browser → device.home.mcztest.com
        → DNS resolves to 192.168.68.100 (Ingress)
        → Ingress proxies to device's real IP
        → Device at 192.168.68.x
```

## Quick Start

1. **Find your device's IP address**:
   ```bash
   # Example: Proxmox at 192.168.68.2
   ping proxmox
   ```

2. **Create ingress manifest** (see examples below)

3. **Apply to cluster**:
   ```bash
   kubectl apply -f kubernetes/local-devices/proxmox-ingress.yaml
   ```

4. **Access with HTTPS**:
   ```
   https://proxmox.home.mcztest.com
   ```

## Examples

### Proxmox (HTTPS Backend)

For devices that already use HTTPS (like Proxmox):

```yaml
# See: proxmox-ingress.yaml
# Access: https://proxmox.home.mcztest.com
# Backend: https://192.168.68.2:8006
```

**Apply:**
```bash
kubectl apply -f kubernetes/local-devices/proxmox-ingress.yaml
```

### Pi-hole (HTTP Backend)

For devices using HTTP:

```yaml
# See: pihole-ingress.yaml
# Access: https://pihole.home.mcztest.com (HTTPS!)
# Backend: http://192.168.68.3:80
```

**Apply:**
```bash
# Edit pihole-ingress.yaml with your Pi-hole IP
kubectl apply -f kubernetes/local-devices/pihole-ingress.yaml
```

### Generic Template

For any other device:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: DEVICE-NAME-external
  namespace: default
spec:
  ports:
  - port: DEVICE-PORT
    targetPort: DEVICE-PORT
    protocol: TCP
---
apiVersion: v1
kind: Endpoints
metadata:
  name: DEVICE-NAME-external
  namespace: default
subsets:
- addresses:
  - ip: DEVICE-IP
  ports:
  - port: DEVICE-PORT
    protocol: TCP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: DEVICE-NAME
  namespace: default
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-cloudflare
    # For HTTPS backends (Proxmox, etc):
    nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"
    nginx.ingress.kubernetes.io/ssl-passthrough: "true"
    # For HTTP backends (Pi-hole, etc):
    # nginx.ingress.kubernetes.io/backend-protocol: "HTTP"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - DEVICE-NAME.home.mcztest.com
    secretName: DEVICE-NAME-tls
  rules:
  - host: DEVICE-NAME.home.mcztest.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: DEVICE-NAME-external
            port:
              number: DEVICE-PORT
```

**Replace:**
- `DEVICE-NAME` → Short name (e.g., `router`, `nas`, `homeassistant`)
- `DEVICE-IP` → Device's IP address (e.g., `192.168.68.10`)
- `DEVICE-PORT` → Device's port (e.g., `80`, `443`, `8080`)

## Common Devices

| Device | Port | Protocol | Example |
|--------|------|----------|---------|
| Proxmox | 8006 | HTTPS | proxmox.home.mcztest.com |
| Pi-hole | 80 | HTTP | pihole.home.mcztest.com |
| Home Assistant | 8123 | HTTP | homeassistant.home.mcztest.com |
| Unraid | 443 | HTTPS | unraid.home.mcztest.com |
| Router | 80 | HTTP | router.home.mcztest.com |
| NAS (Synology) | 5000 | HTTP | nas.home.mcztest.com |
| ESXi | 443 | HTTPS | esxi.home.mcztest.com |

## Alternative Approaches

### 1. Ingress Proxy (Recommended ✅)

**Pros:**
- Automatic HTTPS with Let's Encrypt
- Centralized management
- No device configuration needed
- Consistent domain pattern

**Cons:**
- Extra network hop through ingress
- Requires Kubernetes cluster to be running

**Use when:** You want automatic HTTPS and don't mind proxying

---

### 2. Direct Cloudflare DNS Records

Add individual A records in Cloudflare:

```
proxmox.home.mcztest.com → 192.168.68.2
pihole.home.mcztest.com  → 192.168.68.3
```

**Pros:**
- Direct connection (no proxy)
- Works without Kubernetes
- Simple setup

**Cons:**
- No automatic HTTPS (unless device supports it)
- Must manually manage each record
- Browser warnings for self-signed certs

**Use when:** You need direct access and devices already have HTTPS

---

### 3. Local DNS (Pi-hole/Router)

Configure local DNS overrides in Pi-hole or your router:

```
proxmox.home.mcztest.com → 192.168.68.2
```

**Pros:**
- Works offline (no internet needed for DNS)
- Fast resolution
- Simple

**Cons:**
- No HTTPS certificates
- Only works on local network
- Must configure on each DNS server

**Use when:** You don't need HTTPS and want offline DNS

## Troubleshooting

**Certificate not issuing:**
```bash
kubectl get certificate
kubectl describe certificate DEVICE-NAME-tls
```

**Ingress not routing:**
```bash
kubectl get ingress
kubectl describe ingress DEVICE-NAME
```

**Can't reach device:**
```bash
# Test direct connection first
curl -k http://192.168.68.2:8006

# Check service endpoints
kubectl get endpoints DEVICE-NAME-external
```

**SSL errors for HTTPS backends:**
- Add `nginx.ingress.kubernetes.io/ssl-passthrough: "true"` annotation
- Add `nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"` annotation

## Tips

1. **Update DNS**: Cloudflare wildcard `*.home.mcztest.com` already points to ingress
2. **Test locally first**: Use direct IP before creating ingress
3. **Check device allows proxying**: Some devices block reverse proxy access
4. **Use backend-protocol**: Set to HTTP or HTTPS based on device
5. **Disable SSL verification**: Add `ssl-verify: "false"` for self-signed device certs

## See Also

- [Nginx Ingress Annotations](https://kubernetes.github.io/ingress-nginx/user-guide/nginx-configuration/annotations/)
- [cert-manager Configuration](../infrastructure/cert-manager/README.md)
- [Let's Encrypt Troubleshooting](https://cert-manager.io/docs/troubleshooting/)
