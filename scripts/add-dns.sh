#!/bin/bash
set -e

# Add DNS record to Cloudflare
# Usage: ./scripts/add-dns.sh <subdomain> <ip>
# Example: ./scripts/add-dns.sh home 192.168.68.100

if [ $# -lt 2 ]; then
    echo "Usage: $0 <subdomain> <ip>"
    echo ""
    echo "Examples:"
    echo "  $0 home 192.168.68.100        # Creates home.mcztest.com"
    echo "  $0 proxmox 192.168.68.2       # Creates proxmox.mcztest.com"
    echo "  $0 test 192.168.68.50         # Creates test.mcztest.com"
    exit 1
fi

SUBDOMAIN=$1
IP=$2

# Load configuration from .env
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

if [ -z "$CLOUDFLARE_API_TOKEN" ]; then
    echo "Error: CLOUDFLARE_API_TOKEN not found in .env"
    exit 1
fi

# Extract base domain from APP_DOMAIN
# If APP_DOMAIN is home.mcztest.com, we want mcztest.com
BASE_DOMAIN=$(echo "$APP_DOMAIN" | awk -F. '{print $(NF-1)"."$NF}')
FULL_DOMAIN="${SUBDOMAIN}.${BASE_DOMAIN}"

echo "Adding DNS record..."
echo "  Domain: ${FULL_DOMAIN}"
echo "  IP: ${IP}"
echo ""

# Get Zone ID
echo "Looking up zone ID for ${BASE_DOMAIN}..."
ZONE_ID=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones?name=${BASE_DOMAIN}" \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" | \
  grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "$ZONE_ID" ]; then
    echo "Error: Could not find zone for ${BASE_DOMAIN}"
    echo "Make sure your Cloudflare API token has access to this domain"
    exit 1
fi

echo "Zone ID: ${ZONE_ID}"
echo ""

# Check if record already exists
echo "Checking if record already exists..."
EXISTING_RECORD=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records?name=${FULL_DOMAIN}" \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" | \
  grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -n "$EXISTING_RECORD" ]; then
    echo "Record exists, updating..."
    RESPONSE=$(curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records/${EXISTING_RECORD}" \
      -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
      -H "Content-Type: application/json" \
      --data "{\"type\":\"A\",\"name\":\"${FULL_DOMAIN}\",\"content\":\"${IP}\",\"ttl\":1,\"proxied\":false}")
else
    echo "Creating new record..."
    RESPONSE=$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records" \
      -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
      -H "Content-Type: application/json" \
      --data "{\"type\":\"A\",\"name\":\"${FULL_DOMAIN}\",\"content\":\"${IP}\",\"ttl\":1,\"proxied\":false}")
fi

# Check if successful
if echo "$RESPONSE" | grep -q '"success":true'; then
    echo ""
    echo "DNS record added successfully!"
    echo ""
    echo "Record details:"
    echo "  ${FULL_DOMAIN} -> ${IP}"
    echo ""
    echo "DNS propagation may take a few minutes."
    echo "Test with: dig ${FULL_DOMAIN}"
else
    echo ""
    echo "Error adding DNS record:"
    echo "$RESPONSE" | grep -o '"message":"[^"]*"' | cut -d'"' -f4
    exit 1
fi
