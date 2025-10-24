# MinIO Object Storage

MinIO is a high-performance, S3-compatible object storage system deployed in your homelab cluster.

## Access Information

- **Console (Web UI)**: https://minio.home.mcztest.com
- **API (S3-compatible)**: https://minio-api.home.mcztest.com
- **Default Credentials**:
  - Username: `minioadmin`
  - Password: `minioadmin123`

⚠️ **IMPORTANT**: Change the default credentials in production! Edit `secret.yaml` and update the deployment.

## Usage for Other Apps

### S3-Compatible Configuration

Apps can connect to MinIO using standard S3 SDK libraries with these settings:

```yaml
S3_ENDPOINT: "https://minio-api.home.mcztest.com"
S3_ACCESS_KEY: "minioadmin"
S3_SECRET_KEY: "minioadmin123"
S3_BUCKET: "your-bucket-name"
S3_REGION: "us-east-1"  # MinIO default
S3_USE_SSL: "true"
```

### Internal Cluster Access

For apps running inside the cluster, use the internal service endpoint for better performance:

```yaml
S3_ENDPOINT: "http://minio-api.minio.svc.cluster.local:9000"
S3_ACCESS_KEY: "minioadmin"
S3_SECRET_KEY: "minioadmin123"
```

### Creating Buckets

**Via Console UI:**
1. Navigate to https://minio.home.mcztest.com
2. Login with credentials
3. Click "Buckets" → "Create Bucket"
4. Enter bucket name and create

**Via MinIO Client (mc):**
```bash
# Install mc client
brew install minio/stable/mc  # macOS
# or download from https://min.io/download

# Configure alias
mc alias set homelab https://minio-api.home.mcztest.com minioadmin minioadmin123

# Create bucket
mc mb homelab/my-bucket

# List buckets
mc ls homelab

# Upload file
mc cp myfile.txt homelab/my-bucket/

# Download file
mc cp homelab/my-bucket/myfile.txt ./
```

**Via kubectl exec:**
```bash
kubectl exec -n minio deployment/minio -- mc alias set local http://localhost:9000 minioadmin minioadmin123
kubectl exec -n minio deployment/minio -- mc mb local/my-bucket
kubectl exec -n minio deployment/minio -- mc ls local
```

### Example: Configuring an App to Use MinIO

**Kubernetes Secret:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-s3-config
  namespace: my-app
type: Opaque
stringData:
  S3_ENDPOINT: "http://minio-api.minio.svc.cluster.local:9000"
  S3_ACCESS_KEY: "minioadmin"
  S3_SECRET_KEY: "minioadmin123"
  S3_BUCKET: "my-app-data"
  S3_REGION: "us-east-1"
```

**Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  template:
    spec:
      containers:
      - name: app
        envFrom:
        - secretRef:
            name: app-s3-config
```

## Creating Access Keys for Apps

Instead of using root credentials, create dedicated access keys for each app:

1. Login to MinIO Console (https://minio.home.mcztest.com)
2. Go to "Access Keys" → "Create Access Key"
3. Set optional policy restrictions
4. Copy the generated Access Key and Secret Key
5. Use these in your app's configuration

## Storage

- **Storage Class**: local-path (k3s default)
- **Size**: 50Gi (adjustable in `pvc.yaml`)
- **Location**: Worker node where pod is scheduled

## Deployment

MinIO is managed via ArgoCD and will auto-sync from this repository.

To manually apply:
```bash
kubectl apply -k kubernetes/apps/minio/
```

To update DNS:
```bash
./scripts/add-dns.sh minio 192.168.68.101
./scripts/add-dns.sh minio-api 192.168.68.101
```

## Monitoring

Check MinIO status:
```bash
# Pod status
kubectl get pods -n minio

# Logs
kubectl logs -n minio -l app=minio -f

# Service endpoints
kubectl get svc -n minio

# Ingress
kubectl get ingress -n minio

# Storage
kubectl get pvc -n minio
```

## Common Use Cases

- **Static file storage** for web apps (images, PDFs, media)
- **Backup storage** for databases and applications
- **Data lake** for analytics and ML workflows
- **Shared storage** across multiple microservices
- **CI/CD artifact storage** (build outputs, container images as tar files)

## Integration Examples

### Python (boto3)
```python
import boto3

s3 = boto3.client(
    's3',
    endpoint_url='http://minio-api.minio.svc.cluster.local:9000',
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin123',
    region_name='us-east-1'
)

# Upload
s3.upload_file('local.txt', 'my-bucket', 'remote.txt')

# Download
s3.download_file('my-bucket', 'remote.txt', 'local.txt')
```

### Node.js (aws-sdk)
```javascript
const AWS = require('aws-sdk');

const s3 = new AWS.S3({
    endpoint: 'http://minio-api.minio.svc.cluster.local:9000',
    accessKeyId: 'minioadmin',
    secretAccessKey: 'minioadmin123',
    s3ForcePathStyle: true,
    signatureVersion: 'v4'
});

// Upload
s3.putObject({
    Bucket: 'my-bucket',
    Key: 'file.txt',
    Body: 'Hello World'
}, callback);
```

## Troubleshooting

**Can't access console:**
- Check ingress: `kubectl get ingress -n minio`
- Check certificate: `kubectl get certificate -n minio`
- Verify DNS resolves to ingress IP (192.168.68.101)

**Apps can't connect:**
- Verify MinIO is running: `kubectl get pods -n minio`
- Check service exists: `kubectl get svc -n minio`
- Test internal access: `kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- curl http://minio-api.minio.svc.cluster.local:9000/minio/health/live`

**Out of storage:**
- Check PVC size: `kubectl get pvc -n minio`
- Increase in `pvc.yaml` and reapply
- Delete old data via console or mc client
