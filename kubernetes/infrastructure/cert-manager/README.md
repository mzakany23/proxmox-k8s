# cert-manager Configuration

This directory contains cert-manager configuration for automated TLS certificate management using a self-signed CA.

## Architecture

1. **selfsigned-issuer.yaml** - Bootstrap issuer that creates self-signed certificates
2. **ca-certificate.yaml** - Root CA certificate (10-year validity)
3. **ca-issuer.yaml** - CA issuer that uses the root CA to sign certificates for ingress resources

## Trust the CA Certificate

To avoid browser warnings, install the CA certificate on your devices:

### macOS
```bash
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain homelab-ca.crt
```

### Linux (Ubuntu/Debian)
```bash
sudo cp homelab-ca.crt /usr/local/share/ca-certificates/homelab-ca.crt
sudo update-ca-certificates
```

### Windows
1. Double-click `homelab-ca.crt`
2. Click "Install Certificate"
3. Select "Local Machine"
4. Choose "Place all certificates in the following store"
5. Select "Trusted Root Certification Authorities"

### iOS/iPadOS
1. AirDrop or email the `homelab-ca.crt` file to your device
2. Open Settings → General → VPN & Device Management
3. Install the profile
4. Go to Settings → General → About → Certificate Trust Settings
5. Enable full trust for the certificate

### Android
1. Copy `homelab-ca.crt` to your device
2. Settings → Security → Encryption & Credentials → Install a certificate
3. Select "CA certificate"
4. Choose the file

## Using in Ingress Resources

Add this annotation to your Ingress resources to automatically provision HTTPS certificates:

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

cert-manager will automatically:
1. Detect the ingress
2. Request a certificate from the homelab-ca-issuer
3. Store it in the specified secret (my-app-tls)
4. The ingress controller will use it for HTTPS
