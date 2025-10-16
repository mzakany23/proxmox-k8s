#!/bin/bash
# Add DNS entry to Pi-hole for a new app
# Usage: ./scripts/add-dns.sh my-app

set -e

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <app-name>"
    echo "Example: $0 my-api"
    exit 1
fi

APP_NAME=$1
PIHOLE_HOST="pi"
INGRESS_IP="192.168.200.100"

echo "Adding DNS entry for $APP_NAME.apps.homelab..."

ssh $PIHOLE_HOST "echo '$INGRESS_IP $APP_NAME.apps.homelab' | sudo tee -a /etc/hosts && sudo pihole reloaddns" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ DNS entry added: $APP_NAME.apps.homelab → $INGRESS_IP"
    echo ""
    echo "Test DNS resolution:"
    echo "  dig +short $APP_NAME.apps.homelab @192.168.200.62"
    echo ""
    echo "Access your app:"
    echo "  https://$APP_NAME.apps.homelab"
else
    echo "❌ Failed to add DNS entry"
    echo ""
    echo "Manual steps:"
    echo "1. SSH to Pi-hole: ssh pi"
    echo "2. Run: echo '$INGRESS_IP $APP_NAME.apps.homelab' | sudo tee -a /etc/hosts"
    echo "3. Run: sudo pihole reloaddns"
    exit 1
fi
