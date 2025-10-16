#!/bin/bash
# Create a repository in Gitea
# Usage: ./scripts/gitea-create-repo.sh <repo-name> [description] [private]

set -e

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <repo-name> [description] [private]"
    echo "Example: $0 my-app 'My application' true"
    exit 1
fi

REPO_NAME=$1
DESCRIPTION=${2:-""}
PRIVATE=${3:-true}
USERNAME="homelab"
GITEA_POD=$(kubectl get pod -n gitea -l app=gitea -o jsonpath='{.items[0].metadata.name}')

echo "Creating repository: $REPO_NAME"
echo "Description: $DESCRIPTION"
echo "Private: $PRIVATE"

# Create repo using Gitea CLI
kubectl exec -n gitea $GITEA_POD -- su git -c "gitea admin repo create \
  --owner $USERNAME \
  --name $REPO_NAME \
  --private=$PRIVATE \
  --description '$DESCRIPTION'"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Repository created successfully!"
    echo ""
    echo "Repository URL: https://gitea.apps.homelab/$USERNAME/$REPO_NAME"
    echo ""
    echo "Clone with HTTPS:"
    echo "  git clone https://gitea.apps.homelab/$USERNAME/$REPO_NAME.git"
    echo ""
    echo "Clone with SSH:"
    echo "  git clone git@192.168.200.101:$USERNAME/$REPO_NAME.git"
    echo ""
else
    echo "❌ Failed to create repository"
    exit 1
fi
