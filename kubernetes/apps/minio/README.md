# MinIO Distributed Object Storage

MinIO deployed in **distributed mode** with 4 nodes for high availability, data protection via erasure coding, and production-grade performance.

## Architecture

### Distributed Setup
- **Nodes**: 4 StatefulSet pods across your 3-node cluster
- **Storage**: 20Gi per pod = 80Gi total raw storage
- **Usable capacity**: ~40Gi (with EC:2 erasure coding overhead)
- **Erasure Coding**: EC:2 (can lose up to 2 drives and still function)
- **High Availability**: Survives pod/node failures automatically

### Why Distributed Mode?
- ✅ **Data protection** - Erasure coding survives 2 node failures
- ✅ **High availability** - No single point of failure
- ✅ **Performance** - Distributed I/O across multiple nodes
- ✅ **Production-ready** - Same setup used in enterprise deployments

## Access Information

- **Console (Web UI)**: https://minio.home.mcztest.com
- **API (S3-compatible)**: https://minio-api.home.mcztest.com
- **Internal API**: http://minio.minio.svc.cluster.local:9000
- **Default Credentials**:
  - Username: `minioadmin`
  - Password: `minioadmin123`

⚠️ **IMPORTANT**: Change the default credentials in production! Edit `values.yaml` and upgrade the Helm release.

## Pre-Created Buckets

Three buckets are automatically created on deployment:

1. **backups** - For database and application backups
2. **static-files** - For web app assets (images, videos, CSS, JS)
3. **app-data** - For general application data storage

## Usage for Apps

### Internal Cluster Access (Recommended)

For apps running inside the cluster:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: minio-config
  namespace: my-app
type: Opaque
stringData:
  S3_ENDPOINT: "http://minio.minio.svc.cluster.local:9000"
  S3_ACCESS_KEY: "minioadmin"
  S3_SECRET_KEY: "minioadmin123"
  S3_BUCKET: "app-data"
  S3_REGION: "us-east-1"
  S3_USE_SSL: "false"
```

### External Access (HTTPS)

For external access or local development:

```yaml
S3_ENDPOINT: "https://minio-api.home.mcztest.com"
S3_USE_SSL: "true"
```

### Creating Access Keys for Apps

Instead of using root credentials, create dedicated access keys for each app:

1. Login to MinIO Console (https://minio.home.mcztest.com)
2. Go to "Access Keys" → "Create Access Key"
3. Set optional policy restrictions (read-only, specific bucket, etc.)
4. Copy the generated Access Key and Secret Key
5. Use these in your app's configuration

**Example: Read-only access to static-files bucket:**
```bash
kubectl exec -n minio minio-0 -- mc admin user add local myapp-readonly myapp-readonly-secret
kubectl exec -n minio minio-0 -- mc admin policy attach local readonly --user myapp-readonly
```

## Managing Buckets

### Via Console UI

1. Navigate to https://minio.home.mcztest.com
2. Login with credentials
3. Click "Buckets" → "Create Bucket"
4. Enter bucket name and create

### Via MinIO Client (mc)

**From your local machine:**
```bash
# Install mc client
brew install minio/stable/mc  # macOS
# or download from https://min.io/download

# Configure alias
mc alias set homelab https://minio-api.home.mcztest.com minioadmin minioadmin123

# Create bucket
mc mb homelab/my-new-bucket

# List buckets
mc ls homelab

# Upload file
mc cp myfile.txt homelab/my-new-bucket/

# Download file
mc cp homelab/my-new-bucket/myfile.txt ./

# Sync directory to bucket
mc mirror ./local-dir homelab/my-new-bucket/
```

**From inside the cluster:**
```bash
# Exec into any MinIO pod
kubectl exec -it -n minio minio-0 -- sh

# mc is pre-installed in the pod
mc alias set local http://localhost:9000 minioadmin minioadmin123
mc mb local/my-bucket
mc ls local
```

## AWS S3 Sync (Backup/Disaster Recovery)

MinIO can sync data to/from AWS S3 for backups, disaster recovery, or hybrid cloud setups.

### Option 1: One-Time Sync to AWS S3

**Backup to AWS S3:**
```bash
# Configure AWS S3 alias
mc alias set aws https://s3.amazonaws.com AWS_ACCESS_KEY AWS_SECRET_KEY

# One-time sync from MinIO to AWS S3
mc mirror homelab/backups aws/my-aws-backup-bucket

# Verify sync
mc ls aws/my-aws-backup-bucket
```

### Option 2: Automated Sync with CronJob

Create a Kubernetes CronJob to automatically sync MinIO to AWS S3:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: minio-s3-sync
  namespace: minio
spec:
  # Run daily at 2 AM
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: mc-sync
            image: minio/mc:latest
            env:
            - name: AWS_ACCESS_KEY_ID
              valueFrom:
                secretKeyRef:
                  name: aws-credentials
                  key: access-key
            - name: AWS_SECRET_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: aws-credentials
                  key: secret-key
            - name: MINIO_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: minio
                  key: rootUser
            - name: MINIO_SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: minio
                  key: rootPassword
            command:
            - /bin/sh
            - -c
            - |
              # Configure aliases
              mc alias set minio http://minio.minio.svc.cluster.local:9000 \
                $MINIO_ACCESS_KEY $MINIO_SECRET_KEY
              mc alias set aws https://s3.amazonaws.com \
                $AWS_ACCESS_KEY_ID $AWS_SECRET_ACCESS_KEY

              # Sync backups bucket to AWS S3
              mc mirror --overwrite minio/backups aws/my-homelab-backups

              echo "Sync completed at $(date)"
          restartPolicy: OnFailure
```

**Create AWS credentials secret:**
```bash
kubectl create secret generic aws-credentials \
  --from-literal=access-key=YOUR_AWS_ACCESS_KEY \
  --from-literal=secret-key=YOUR_AWS_SECRET_KEY \
  -n minio
```

### Option 3: MinIO Site Replication (Advanced)

For active-active replication between MinIO and AWS S3 (requires MinIO on both sides):

```bash
# Configure both sites
mc alias set site1 https://minio-api.home.mcztest.com minioadmin minioadmin123
mc alias set site2 https://your-other-minio.com admin password

# Enable site replication
mc admin replicate add site1 site2

# Check replication status
mc admin replicate info site1
```

### Option 4: S3 Gateway Mode (Deprecated but still works)

MinIO can run in gateway mode to proxy AWS S3:

```yaml
# Update values.yaml
gateway:
  enabled: true
  type: s3
  replicas: 4

environment:
  MINIO_GATEWAY_S3_ACCESS_KEY: "AWS_ACCESS_KEY"
  MINIO_GATEWAY_S3_SECRET_KEY: "AWS_SECRET_KEY"
  MINIO_GATEWAY_S3_ENDPOINT: "s3.amazonaws.com"
```

## Monitoring & Health

### Check Cluster Health

```bash
# Via kubectl
kubectl get pods -n minio
kubectl get pvc -n minio

# Via mc client
kubectl exec -n minio minio-0 -- mc admin info local
kubectl exec -n minio minio-0 -- mc admin heal local
```

### View Logs

```bash
# All pods
kubectl logs -n minio -l app=minio --tail=100 -f

# Specific pod
kubectl logs -n minio minio-0 -f
```

### Storage Usage

```bash
kubectl exec -n minio minio-0 -- mc du local
```

### Metrics (Prometheus Integration)

MinIO exposes Prometheus metrics at `/minio/v2/metrics/cluster`:

```yaml
# Add to Prometheus scrape config
- job_name: 'minio'
  metrics_path: /minio/v2/metrics/cluster
  scheme: http
  static_configs:
  - targets: ['minio.minio.svc.cluster.local:9000']
```

## Integration Examples

### Python (boto3)

```python
import boto3

# Internal cluster access
s3 = boto3.client(
    's3',
    endpoint_url='http://minio.minio.svc.cluster.local:9000',
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin123',
    region_name='us-east-1'
)

# Upload file
s3.upload_file('local.txt', 'app-data', 'remote.txt')

# Download file
s3.download_file('app-data', 'remote.txt', 'downloaded.txt')

# List objects
response = s3.list_objects_v2(Bucket='app-data')
for obj in response.get('Contents', []):
    print(obj['Key'])
```

### Node.js (aws-sdk)

```javascript
const AWS = require('aws-sdk');

const s3 = new AWS.S3({
    endpoint: 'http://minio.minio.svc.cluster.local:9000',
    accessKeyId: 'minioadmin',
    secretAccessKey: 'minioadmin123',
    s3ForcePathStyle: true,
    signatureVersion: 'v4'
});

// Upload
const params = {
    Bucket: 'app-data',
    Key: 'file.txt',
    Body: 'Hello World'
};
s3.putObject(params, (err, data) => {
    if (err) console.error(err);
    else console.log('Upload success');
});

// Download
s3.getObject({Bucket: 'app-data', Key: 'file.txt'}, (err, data) => {
    if (err) console.error(err);
    else console.log(data.Body.toString());
});
```

### Go (minio-go)

```go
package main

import (
    "context"
    "log"
    "github.com/minio/minio-go/v7"
    "github.com/minio/minio-go/v7/pkg/credentials"
)

func main() {
    client, err := minio.New("minio.minio.svc.cluster.local:9000", &minio.Options{
        Creds:  credentials.NewStaticV4("minioadmin", "minioadmin123", ""),
        Secure: false,
    })
    if err != nil {
        log.Fatal(err)
    }

    // Upload
    _, err = client.FPutObject(context.Background(), "app-data", "file.txt",
        "/path/to/file.txt", minio.PutObjectOptions{})
    if err != nil {
        log.Fatal(err)
    }
}
```

## Upgrading MinIO

### Update via Helm

```bash
# Update values.yaml with new configuration
vim kubernetes/apps/minio/values.yaml

# Upgrade release
export KUBECONFIG=/path/to/kubeconfig.yaml
helm upgrade minio minio/minio \
  --namespace minio \
  --values kubernetes/apps/minio/values.yaml

# Watch rollout
kubectl rollout status statefulset/minio -n minio
```

### Increase Storage Size

```bash
# Edit values.yaml
persistence:
  size: 50Gi  # Increase from 20Gi to 50Gi

# Upgrade Helm release
helm upgrade minio minio/minio -n minio -f values.yaml

# Manually resize PVCs (k3s local-path provisioner)
for i in 0 1 2 3; do
  kubectl patch pvc export-minio-$i -n minio \
    -p '{"spec":{"resources":{"requests":{"storage":"50Gi"}}}}'
done
```

## Disaster Recovery

### Backup Strategy

1. **Regular snapshots** of MinIO data to AWS S3 (via CronJob above)
2. **PVC backups** using Velero or manual snapshots
3. **Configuration backup** in Git (values.yaml)

### Restore from AWS S3

```bash
# Restore from AWS S3 to new MinIO cluster
mc alias set aws https://s3.amazonaws.com AWS_KEY AWS_SECRET
mc alias set minio http://minio.minio.svc.cluster.local:9000 admin password
mc mirror aws/my-homelab-backups minio/backups
```

## Troubleshooting

**Pods not starting:**
```bash
kubectl describe pod -n minio minio-0
kubectl logs -n minio minio-0
```

**Can't access console:**
```bash
# Check ingress
kubectl get ingress -n minio
kubectl describe ingress minio-console -n minio

# Check certificate
kubectl get certificate -n minio
kubectl describe certificate minio-console-tls -n minio
```

**Erasure coding errors:**
```bash
# Check cluster health
kubectl exec -n minio minio-0 -- mc admin heal local

# View detailed drive status
kubectl exec -n minio minio-0 -- mc admin info local
```

**Out of storage:**
```bash
# Check current usage
kubectl exec -n minio minio-0 -- mc du local

# Increase PVC size (see Upgrading section)
# Or delete old data
kubectl exec -n minio minio-0 -- mc rm --recursive --force local/old-bucket
```

## Security Best Practices

1. **Change default credentials** immediately after deployment
2. **Create dedicated access keys** for each application
3. **Use least-privilege policies** (read-only, specific buckets)
4. **Enable TLS** for production (already configured via ingress)
5. **Rotate credentials** periodically
6. **Enable bucket versioning** for critical data
7. **Set up bucket lifecycle policies** for automatic cleanup
8. **Monitor access logs** via MinIO console

## Common Use Cases

- ✅ **Static file storage** for web apps (images, videos, PDFs, CSS, JS)
- ✅ **Database backups** (PostgreSQL, MySQL dumps)
- ✅ **Application backups** (config files, state)
- ✅ **Data lake** for analytics and ML workflows
- ✅ **Shared storage** across multiple microservices
- ✅ **CI/CD artifact storage** (build outputs, test reports)
- ✅ **Log archival** (long-term log storage)
- ✅ **Disaster recovery** (sync to AWS S3 for offsite backup)

## Resources

- **MinIO Documentation**: https://min.io/docs/minio/linux/index.html
- **mc Client Guide**: https://min.io/docs/minio/linux/reference/minio-mc.html
- **S3 API Compatibility**: https://min.io/docs/minio/linux/developers/s3-api-compatibility.html
- **Erasure Coding**: https://min.io/docs/minio/linux/operations/concepts/erasure-coding.html
