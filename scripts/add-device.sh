#!/bin/bash
set -e

# Add local device with HTTPS ingress
# Usage: ./scripts/add-device.sh <name> <ip> <port> [http|https]

if [ $# -lt 3 ]; then
    echo "Usage: $0 <device-name> <device-ip> <port> [http|https]"
    echo ""
    echo "Examples:"
    echo "  $0 proxmox 192.168.68.2 8006 https"
    echo "  $0 pihole 192.168.68.3 80 http"
    echo "  $0 router 192.168.68.1 80 http"
    exit 1
fi

DEVICE_NAME=$1
DEVICE_IP=$2
DEVICE_PORT=$3
PROTOCOL=${4:-http}

# Get domain from .env
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi
APP_DOMAIN=${APP_DOMAIN:-"home.mcztest.com"}

OUTPUT_FILE="$PROJECT_ROOT/kubernetes/local-devices/${DEVICE_NAME}-ingress.yaml"

echo "Creating ingress for $DEVICE_NAME..."
echo "  Domain: ${DEVICE_NAME}.${APP_DOMAIN}"
echo "  Backend: ${PROTOCOL}://${DEVICE_IP}:${DEVICE_PORT}"

# Set protocol-specific annotations
if [ "$PROTOCOL" = "https" ]; then
    BACKEND_PROTOCOL="HTTPS"
    SSL_PASSTHROUGH='nginx.ingress.kubernetes.io/ssl-passthrough: "true"'
else
    BACKEND_PROTOCOL="HTTP"
    SSL_PASSTHROUGH=""
fi

# Create ingress manifest
cat > "$OUTPUT_FILE" <<EOF
apiVersion: v1
kind: Service
metadata:
  name: ${DEVICE_NAME}-external
  namespace: default
spec:
  ports:
  - port: ${DEVICE_PORT}
    targetPort: ${DEVICE_PORT}
    protocol: TCP
---
apiVersion: v1
kind: Endpoints
metadata:
  name: ${DEVICE_NAME}-external
  namespace: default
subsets:
- addresses:
  - ip: ${DEVICE_IP}
  ports:
  - port: ${DEVICE_PORT}
    protocol: TCP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ${DEVICE_NAME}
  namespace: default
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-cloudflare
    nginx.ingress.kubernetes.io/backend-protocol: "${BACKEND_PROTOCOL}"
$([ -n "$SSL_PASSTHROUGH" ] && echo "    $SSL_PASSTHROUGH")
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - ${DEVICE_NAME}.${APP_DOMAIN}
    secretName: ${DEVICE_NAME}-tls
  rules:
  - host: ${DEVICE_NAME}.${APP_DOMAIN}
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ${DEVICE_NAME}-external
            port:
              number: ${DEVICE_PORT}
EOF

echo ""
echo "Created: $OUTPUT_FILE"
echo ""
echo "Apply with:"
echo "  kubectl apply -f $OUTPUT_FILE"
echo ""
echo "Access at:"
echo "  https://${DEVICE_NAME}.${APP_DOMAIN}"
echo ""
echo "Check certificate:"
echo "  kubectl get certificate ${DEVICE_NAME}-tls"
