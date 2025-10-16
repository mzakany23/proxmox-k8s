#!/bin/bash
# Add Gitea repository credentials to ArgoCD
# Usage: ./scripts/gitea-add-to-argocd.sh

set -e

USERNAME="homelab"
PASSWORD="homelab123"
GITEA_URL="https://gitea.apps.homelab"

echo "Adding Gitea repository to ArgoCD..."

# Check if argocd CLI is available
if ! command -v argocd &> /dev/null; then
    echo "ArgoCD CLI not found. Installing via brew..."
    brew install argocd
fi

echo ""
echo "This will add Gitea credentials to ArgoCD."
echo "Repository: $GITEA_URL"
echo "Username: $USERNAME"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
fi

# Login to ArgoCD
echo "Logging into ArgoCD..."
echo "ArgoCD admin password:"
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 --decode)
echo $ARGOCD_PASSWORD

argocd login argocd.apps.homelab \
  --username admin \
  --password $ARGOCD_PASSWORD \
  --insecure

# Add repository credentials
echo ""
echo "Adding Gitea repository credentials..."
argocd repocreds add $GITEA_URL \
  --username $USERNAME \
  --password $PASSWORD

echo ""
echo "✅ Gitea repository credentials added to ArgoCD!"
echo ""
echo "All repos from $GITEA_URL/$USERNAME/ can now be used in ArgoCD Applications."
echo ""
echo "List repository credentials:"
echo "  argocd repocreds list"
echo ""
