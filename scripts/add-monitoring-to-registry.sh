#!/bin/bash
set -e

REGISTRY_API_URL="https://registry-api.home.mcztest.com/api/v1/apps"

echo "Adding Grafana to app registry..."
curl -X POST "$REGISTRY_API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Grafana",
    "url": "https://grafana.mcztest.com",
    "description": "Metrics visualization and monitoring dashboards",
    "category": "kubernetes"
  }' -k

echo ""
echo "Adding Prometheus to app registry..."
curl -X POST "$REGISTRY_API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Prometheus",
    "url": "https://prometheus.mcztest.com",
    "description": "Metrics collection and time-series database",
    "category": "kubernetes"
  }' -k

echo ""
echo "Done! Grafana and Prometheus added to registry."
echo "Visit https://home.mcztest.com to see them on the dashboard."
