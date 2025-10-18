#!/bin/bash

# Scan local network for devices
# Usage: ./scripts/scan-network.sh

set -e

# Get network from current IP
CURRENT_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "192.168.68.0")
NETWORK=$(echo $CURRENT_IP | cut -d. -f1-3)

echo "Scanning network: ${NETWORK}.0/24"
echo ""

# Check if nmap is installed
if ! command -v nmap &> /dev/null; then
    echo "nmap not found. Installing suggestions:"
    echo "  macOS: brew install nmap"
    echo "  Linux: sudo apt-get install nmap"
    echo ""
    echo "Falling back to ping scan..."
    echo ""

    # Fallback: ping sweep
    for i in {1..254}; do
        (ping -c 1 -W 1 ${NETWORK}.$i &> /dev/null && echo "${NETWORK}.$i is up") &
    done
    wait
    exit 0
fi

# Use nmap for detailed scan
echo "Running nmap scan..."
nmap -sn ${NETWORK}.0/24 | grep -E "Nmap scan report|MAC Address" | sed 's/Nmap scan report for //' | sed 's/MAC Address: /  MAC: /'

echo ""
echo "For detailed scan with ports and services:"
echo "  sudo nmap -sV ${NETWORK}.0/24"
