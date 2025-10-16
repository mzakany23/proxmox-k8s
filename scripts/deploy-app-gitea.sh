#!/bin/bash
# Complete automation: Create repo in Gitea, initialize with template, deploy via ArgoCD
# Usage: ./scripts/deploy-app-gitea.sh <app-name>

set -e

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <app-name>"
    echo "Example: $0 my-api"
    exit 1
fi

APP_NAME=$1

echo "🚀 Complete GitOps deployment for: $APP_NAME"
echo ""
echo "This will:"
echo "  1. Create private repo in Gitea: $APP_NAME"
echo "  2. Initialize with basic-app template"
echo "  3. Create ArgoCD Application"
echo "  4. Add DNS entry to Pi-hole"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 0
fi

# Create and initialize repo
./scripts/gitea-setup-repo.sh $APP_NAME basic-app

# Create ArgoCD app
./scripts/create-argocd-app.sh $APP_NAME

# Add DNS
./scripts/add-dns.sh $APP_NAME

echo ""
echo "✅ Complete deployment finished!"
echo ""
echo "🌐 Repository: https://gitea.apps.homelab/homelab/$APP_NAME"
echo "🚀 ArgoCD: https://argocd.apps.homelab/applications/$APP_NAME"
echo "📱 App URL: https://$APP_NAME.apps.homelab"
echo ""
echo "⏱️  Wait ~30 seconds for ArgoCD to sync, then visit:"
echo "   https://$APP_NAME.apps.homelab"
echo ""
