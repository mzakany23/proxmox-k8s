#!/bin/bash
# Create a Gitea repo and initialize it with app manifests
# Usage: ./scripts/gitea-setup-repo.sh <repo-name> <template>

set -e

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <repo-name> <template>"
    echo ""
    echo "Templates:"
    echo "  basic-app       - Simple stateless application"
    echo "  empty           - Empty repository"
    echo ""
    echo "Example: $0 my-api basic-app"
    exit 1
fi

REPO_NAME=$1
TEMPLATE=$2
USERNAME="homelab"
GITEA_URL="https://gitea.apps.homelab"
WORK_DIR="/tmp/gitea-$REPO_NAME-$$"

# Create the repo in Gitea
echo "1. Creating repository in Gitea..."
./scripts/gitea-create-repo.sh $REPO_NAME "GitOps managed application" true

# Clone and initialize
echo ""
echo "2. Initializing repository..."
mkdir -p $WORK_DIR
cd $WORK_DIR

# Initialize git
git init
git config user.name "Homelab Admin"
git config user.email "homelab@local"

# Add content based on template
if [ "$TEMPLATE" = "basic-app" ]; then
    echo "Copying basic-app template..."
    cp -r $(dirname $0)/../templates/basic-app/* .

    # Replace placeholders
    if [[ "$OSTYPE" == "darwin"* ]]; then
        find . -type f -exec sed -i '' "s/REPLACE_APP_NAME/$REPO_NAME/g" {} +
        find . -type f -exec sed -i '' "s|REPLACE_IMAGE|nginx:alpine|g" {} +
    else
        find . -type f -exec sed -i "s/REPLACE_APP_NAME/$REPO_NAME/g" {} +
        find . -type f -exec sed -i "s|REPLACE_IMAGE|nginx:alpine|g" {} +
    fi

    # Create README
    cat > README.md <<EOF
# $REPO_NAME

GitOps managed application.

## Deploy

This app is managed by ArgoCD. Any changes pushed to this repository will be automatically deployed to the cluster.

## Structure

- \`deployment.yaml\` - Kubernetes Deployment
- \`service.yaml\` - Kubernetes Service
- \`ingress.yaml\` - Ingress with automatic HTTPS
- \`kustomization.yaml\` - Kustomize configuration

## Access

After deployment: https://$REPO_NAME.apps.homelab
EOF
elif [ "$TEMPLATE" = "empty" ]; then
    cat > README.md <<EOF
# $REPO_NAME

Private GitOps repository.
EOF
else
    echo "Unknown template: $TEMPLATE"
    cd /
    rm -rf $WORK_DIR
    exit 1
fi

# Commit and push
git add .
git commit -m "Initial commit from template: $TEMPLATE"

echo ""
echo "3. Pushing to Gitea..."
echo "   Enter username: homelab"
echo "   Enter password: homelab123"
git remote add origin $GITEA_URL/$USERNAME/$REPO_NAME.git
git push -u origin main

# Cleanup
cd /
rm -rf $WORK_DIR

echo ""
echo "✅ Repository setup complete!"
echo ""
echo "Repository: $GITEA_URL/$USERNAME/$REPO_NAME"
echo ""
echo "Next steps:"
echo "1. Create ArgoCD Application:"
echo "   ./scripts/create-argocd-app.sh $REPO_NAME"
echo ""
echo "2. Add DNS entry:"
echo "   ./scripts/add-dns.sh $REPO_NAME"
echo ""
