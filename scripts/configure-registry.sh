#!/bin/bash

# Configure k3s to use the internal container registry
# This allows nodes to pull images from the cluster-internal registry

REGISTRY_CONFIG="/etc/rancher/k3s/registries.yaml"

cat <<EOF | sudo tee $REGISTRY_CONFIG
mirrors:
  docker-registry.container-registry.svc.cluster.local:5000:
    endpoint:
      - "http://docker-registry.container-registry.svc.cluster.local:5000"
configs:
  "docker-registry.container-registry.svc.cluster.local:5000":
    tls:
      insecure_skip_verify: true
EOF

echo "Registry configuration created at $REGISTRY_CONFIG"
echo "Restarting k3s service..."
sudo systemctl restart k3s || sudo systemctl restart k3s-agent
echo "Done!"
