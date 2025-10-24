# Kubernetes Monitoring Stack

This directory contains the infrastructure components for comprehensive Kubernetes monitoring.

## Components Installed

### 1. kube-state-metrics
- **Purpose**: Exposes Kubernetes object metrics (pods, nodes, deployments, services, etc.)
- **Deployment**: Single replica deployment in `monitoring` namespace
- **Metrics Port**: 8080
- **Telemetry Port**: 8081
- **Resource Requests**: 100m CPU, 128Mi memory
- **RBAC**: ClusterRole with read-only access to Kubernetes resources

### 2. node-exporter
- **Purpose**: Exposes node hardware and OS metrics (CPU, memory, disk, network)
- **Deployment**: DaemonSet (runs on all nodes)
- **Metrics Port**: 9100
- **Host Access**: Uses hostNetwork, hostPID for system metrics
- **Mounted Paths**: /proc, /sys, /root from host
- **Resource Requests**: 50m CPU, 64Mi memory

## Integration with Prometheus

The Prometheus configuration has been updated to scrape these new exporters:

```yaml
# kube-state-metrics
- job_name: 'kube-state-metrics'
  static_configs:
    - targets: ['kube-state-metrics.monitoring.svc.cluster.local:8080']

# node-exporter
- job_name: 'node-exporter'
  kubernetes_sd_configs:
    - role: endpoints
      namespaces:
        names:
          - monitoring
```

## Grafana Dashboards

Three comprehensive dashboards have been added to Grafana:

### 1. Kubernetes Cluster Overview (uid: k8s-cluster-overview)
- **Stats**: Total Nodes, Ready Nodes, Total Pods, Running Pods, Failed/Pending Pods, Namespaces
- **Metrics**:
  - CPU Usage by Node (with thresholds at 70%, 90%)
  - Memory Usage by Node (with thresholds at 70%, 90%)
  - Network Traffic by Node (RX/TX)
  - Disk Usage by Node (with thresholds at 70%, 90%)
- **Refresh**: 30 seconds
- **Time Range**: Last 1 hour

### 2. Kubernetes Pods Overview (uid: k8s-pods-overview)
- **Tables**: All pods with namespace, node, and pod name
- **Metrics**:
  - Running Pods by Namespace
  - Container Restarts by Namespace
  - Memory Usage by Namespace
  - CPU Usage by Namespace
- **Refresh**: 30 seconds
- **Time Range**: Last 1 hour

### 3. Kubernetes Applications Overview (uid: k8s-apps-overview)
- **Tables**:
  - Deployments (with available replicas)
  - Services (with namespace and service name)
  - Ingresses (with namespace and ingress name)
- **Metrics**:
  - Deployment Availability Over Time
- **Refresh**: 30 seconds
- **Time Range**: Last 1 hour

## Accessing Grafana

- **URL**: https://grafana.mcztest.com
- **Username**: admin
- **Password**: homelab123

## Verifying Metrics

To verify that Prometheus is collecting metrics:

```bash
# Check all Prometheus targets
kubectl exec -n monitoring deployment/prometheus -- wget -qO- http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'

# Check kube-state-metrics
kubectl exec -n monitoring deployment/prometheus -- wget -qO- 'http://localhost:9090/api/v1/query?query=kube_node_info'

# Check node-exporter
kubectl exec -n monitoring deployment/prometheus -- wget -qO- 'http://localhost:9090/api/v1/query?query=node_memory_MemTotal_bytes'

# Check pod metrics
kubectl exec -n monitoring deployment/prometheus -- wget -qO- 'http://localhost:9090/api/v1/query?query=kube_pod_info'
```

## Troubleshooting

### Dashboards showing "No data"

1. Check that kube-state-metrics and node-exporter are running:
```bash
kubectl get pods -n monitoring
```

2. Verify Prometheus is scraping the exporters:
```bash
kubectl exec -n monitoring deployment/prometheus -- wget -qO- http://localhost:9090/api/v1/targets
```

3. Check if metrics are available in Prometheus:
```bash
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Open http://localhost:9090 and query for kube_node_info or node_cpu_seconds_total
```

### Node-exporter not running on a node

Node-exporter is a DaemonSet and should run on all nodes. If it's not running:

```bash
kubectl describe daemonset node-exporter -n monitoring
kubectl logs -n monitoring -l app=node-exporter
```

### kube-state-metrics not collecting data

Check the logs:
```bash
kubectl logs -n monitoring deployment/kube-state-metrics
```

Verify RBAC permissions:
```bash
kubectl describe clusterrole kube-state-metrics
kubectl describe clusterrolebinding kube-state-metrics
```

## Resource Usage

Approximate resource usage for the monitoring stack:

- **kube-state-metrics**: 100-200m CPU, 128-256Mi memory
- **node-exporter** (per node): 50m CPU, 64Mi memory
- **Prometheus**: 200-500m CPU, 1-2Gi memory
- **Grafana**: 100-500m CPU, 256Mi-1Gi memory

Total for 3-node cluster: ~600m-1.5 CPU cores, ~2-4Gi memory

## Metrics Retention

Prometheus is configured with default retention (15 days). To change this, update the Prometheus deployment args:

```yaml
args:
  - '--storage.tsdb.retention.time=30d'  # Increase to 30 days
  - '--storage.tsdb.retention.size=10GB'  # Or limit by size
```
