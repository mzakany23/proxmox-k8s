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
PASSWORD="homelab123"
GITEA_URL="https://gitea.apps.homelab"

echo "Creating repository: $REPO_NAME"
echo "Description: $DESCRIPTION"
echo "Private: $PRIVATE"

# Create repo using Gitea API
RESPONSE=$(curl -X POST "$GITEA_URL/api/v1/user/repos" \
  -u "$USERNAME:$PASSWORD" \
  -k \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$REPO_NAME\",
    \"description\": \"$DESCRIPTION\",
    \"private\": $PRIVATE,
    \"auto_init\": false
  }" \
  -w "\n%{http_code}" \
  -s)

HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "201" ]; then
    echo ""
    echo "✅ Repository created successfully!"
    echo ""
    echo "Repository URL: $GITEA_URL/$USERNAME/$REPO_NAME"
    echo ""
    echo "Clone with HTTPS:"
    echo "  git clone $GITEA_URL/$USERNAME/$REPO_NAME.git"
    echo ""
    echo "Clone with SSH:"
    echo "  git clone git@192.168.200.101:$USERNAME/$REPO_NAME.git"
    echo ""
elif [ "$HTTP_CODE" = "409" ]; then
    echo ""
    echo "⚠️  Repository already exists"
    echo ""
    echo "Repository URL: $GITEA_URL/$USERNAME/$REPO_NAME"
    echo ""
else
    echo ""
    echo "❌ Failed to create repository (HTTP $HTTP_CODE)"
    echo "$BODY"
    exit 1
fi
