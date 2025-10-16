#!/bin/bash
# Create a new Kubernetes application from template
# Usage: ./scripts/create-app.sh my-app nginx:alpine

set -e

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <app-name> <image>"
    echo "Example: $0 my-api nginx:alpine"
    exit 1
fi

APP_NAME=$1
IMAGE=$2
REPO_URL="https://github.com/mzakany23/proxmox-k8s.git"

echo "Creating new app: $APP_NAME"

# Copy template
cp -r templates/basic-app kubernetes/apps/$APP_NAME

# Replace placeholders (macOS sed syntax)
if [[ "$OSTYPE" == "darwin"* ]]; then
    find kubernetes/apps/$APP_NAME -type f -exec sed -i '' "s/REPLACE_APP_NAME/$APP_NAME/g" {} +
    find kubernetes/apps/$APP_NAME -type f -exec sed -i '' "s|REPLACE_IMAGE|$IMAGE|g" {} +
else
    find kubernetes/apps/$APP_NAME -type f -exec sed -i "s/REPLACE_APP_NAME/$APP_NAME/g" {} +
    find kubernetes/apps/$APP_NAME -type f -exec sed -i "s|REPLACE_IMAGE|$IMAGE|g" {} +
fi

# Create ArgoCD Application
cat > kubernetes/infrastructure/argocd/app-$APP_NAME.yaml <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: $APP_NAME
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: $REPO_URL
    targetRevision: main
    path: kubernetes/apps/$APP_NAME
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
      - CreateNamespace=true
EOF

echo ""
echo "✅ Created app structure:"
echo "   - kubernetes/apps/$APP_NAME/"
echo "   - kubernetes/infrastructure/argocd/app-$APP_NAME.yaml"
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Review and customize the manifests:"
echo "   cd kubernetes/apps/$APP_NAME"
echo "   # Edit deployment.yaml, service.yaml, ingress.yaml as needed"
echo ""
echo "2. Commit and push to git:"
echo "   git add ."
echo "   git commit -m \"Add $APP_NAME application\""
echo "   git push origin main"
echo ""
echo "3. Deploy via ArgoCD:"
echo "   kubectl apply -f kubernetes/infrastructure/argocd/app-$APP_NAME.yaml"
echo ""
echo "4. Add DNS entry to Pi-hole:"
echo "   ./scripts/add-dns.sh $APP_NAME"
echo ""
echo "5. Access your app:"
echo "   https://$APP_NAME.apps.homelab"
echo ""
