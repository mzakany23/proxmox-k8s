#!/bin/bash
# Bootstrap GitOps on the Kubernetes cluster
# This script:
# 1. Applies infrastructure manifests (MetalLB, Ingress, cert-manager)
# 2. Installs ArgoCD
# 3. Configures ArgoCD to watch Gitea for application deployments

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
KUBECONFIG_PATH="${KUBECONFIG:-$PROJECT_ROOT/terraform/kubeconfig.yaml}"

echo "🚀 Bootstrapping GitOps on Kubernetes cluster..."
echo "Using kubeconfig: $KUBECONFIG_PATH"

export KUBECONFIG="$KUBECONFIG_PATH"

# Wait for cluster to be ready
echo "⏳ Waiting for cluster to be ready..."
kubectl wait --for=condition=Ready nodes --all --timeout=300s

# Apply infrastructure in order
echo "📦 Applying infrastructure components..."

# 1. MetalLB (needed for LoadBalancer services)
echo "  - Installing MetalLB..."
kubectl apply -k "$PROJECT_ROOT/kubernetes/infrastructure/metallb/"
kubectl wait --namespace metallb-system --for=condition=ready pod --selector=app=metallb --timeout=120s

# 2. Ingress Nginx
echo "  - Installing Ingress Nginx..."
kubectl apply -f "$PROJECT_ROOT/kubernetes/infrastructure/ingress-nginx/install.yaml"
kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=180s

# 3. cert-manager
echo "  - Installing cert-manager..."
kubectl apply -k "$PROJECT_ROOT/kubernetes/infrastructure/cert-manager/"
kubectl wait --namespace cert-manager --for=condition=ready pod --selector=app=cert-manager --timeout=120s

# Wait a bit for CRDs to be fully ready
sleep 10

# Install ArgoCD
echo "🔧 Installing ArgoCD..."
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

echo "⏳ Waiting for ArgoCD to be ready..."
kubectl wait --namespace argocd --for=condition=ready pod --selector=app.kubernetes.io/name=argocd-server --timeout=300s

# Get ArgoCD admin password
echo ""
echo "✅ Bootstrap complete!"
echo ""
echo "📝 ArgoCD Details:"
echo "  Namespace: argocd"
echo "  Admin Password:"
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d && echo
echo ""
echo "🌐 Next steps:"
echo "  1. Port-forward to access ArgoCD UI:"
echo "     kubectl port-forward svc/argocd-server -n argocd 8080:443"
echo "  2. Login at https://localhost:8080 with username 'admin'"
echo "  3. Or use the CLI:"
echo "     argocd login localhost:8080"
echo ""
echo "  4. Set up Gitea repository in ArgoCD and deploy applications"
echo ""
