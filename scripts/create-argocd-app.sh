#!/bin/bash
# Create an ArgoCD Application pointing to a Gitea repository
# Usage: ./scripts/create-argocd-app.sh <app-name> [path] [namespace]

set -e

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <app-name> [path] [namespace]"
    echo "Example: $0 my-api . default"
    exit 1
fi

APP_NAME=$1
PATH_IN_REPO=${2:-.}
NAMESPACE=${3:-default}
USERNAME="homelab"
GITEA_URL="https://gitea.apps.homelab"

echo "Creating ArgoCD Application: $APP_NAME"

# Create ArgoCD Application manifest
cat > /tmp/argocd-app-$APP_NAME.yaml <<EOF
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
    repoURL: $GITEA_URL/$USERNAME/$APP_NAME.git
    targetRevision: main
    path: $PATH_IN_REPO
  destination:
    server: https://kubernetes.default.svc
    namespace: $NAMESPACE
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
      - CreateNamespace=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
EOF

# Apply to cluster
echo "Applying ArgoCD Application to cluster..."
kubectl apply -f /tmp/argocd-app-$APP_NAME.yaml

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ ArgoCD Application created!"
    echo ""
    echo "Monitor sync status:"
    echo "  kubectl get application -n argocd $APP_NAME"
    echo "  argocd app get $APP_NAME"
    echo ""
    echo "View in ArgoCD UI:"
    echo "  https://argocd.apps.homelab/applications/$APP_NAME"
    echo ""

    # Save to repo too
    mkdir -p kubernetes/infrastructure/argocd
    cp /tmp/argocd-app-$APP_NAME.yaml kubernetes/infrastructure/argocd/app-$APP_NAME.yaml
    echo "Saved to: kubernetes/infrastructure/argocd/app-$APP_NAME.yaml"
    echo ""
    echo "Commit to git:"
    echo "  git add kubernetes/infrastructure/argocd/app-$APP_NAME.yaml"
    echo "  git commit -m 'Add ArgoCD app: $APP_NAME'"
    echo "  git push"
else
    echo "❌ Failed to create ArgoCD Application"
    exit 1
fi
