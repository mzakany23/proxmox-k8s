# Apache Superset API Guide

## Access Information

### Web UI Access
- **URL**: https://superset.mcztest.com
- **Username**: `admin`
- **Password**: `admin`

**⚠️ IMPORTANT**: Change the admin password after first login!

### Architecture
- **Web Server**: Superset UI and API endpoints
- **Worker**: Celery workers for async tasks
- **Celery Beat**: Task scheduler
- **PostgreSQL**: Metadata database (postgres:16-alpine)
- **Redis**: Caching and Celery message broker (redis:alpine)

## API Overview

Superset provides a comprehensive REST API for programmatic access to all features including:
- Database connections
- Datasets
- Charts
- Dashboards
- Users and permissions

### Base URL
```
https://superset.mcztest.com/api/v1
```

### API Documentation
Once logged in, visit:
```
https://superset.mcztest.com/swagger/v1
```

## Authentication

### Method 1: Username/Password Login

Get an access token:

```bash
curl -X POST 'https://superset.mcztest.com/api/v1/security/login' \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "admin",
    "password": "admin",
    "provider": "db",
    "refresh": true
  }'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLC...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLC..."
}
```

### Method 2: CSRF Token (for Web Sessions)

```bash
# Get CSRF token
curl -c cookies.txt 'https://superset.apps.homelab/api/v1/security/csrf_token/'

# Use in subsequent requests
curl -b cookies.txt \
  -H 'X-CSRFToken: <token_from_response>' \
  'https://superset.apps.homelab/api/v1/...'
```

## Common API Operations

### Using the Access Token

Include the token in the Authorization header:

```bash
TOKEN="eyJ0eXAiOiJKV1QiLC..."

curl -X GET 'https://superset.mcztest.com/api/v1/dashboard/' \
  -H "Authorization: Bearer $TOKEN"
```

### 1. Create a Database Connection

```bash
curl -X POST 'https://superset.mcztest.com/api/v1/database/' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "database_name": "my_postgres_db",
    "sqlalchemy_uri": "postgresql://user:password@host:5432/dbname",
    "expose_in_sqllab": true
  }'
```

### 2. List Databases

```bash
curl -X GET 'https://superset.mcztest.com/api/v1/database/' \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Create a Dataset

```bash
curl -X POST 'https://superset.mcztest.com/api/v1/dataset/' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "database": 1,
    "schema": "public",
    "table_name": "my_table"
  }'
```

### 4. List Datasets

```bash
curl -X GET 'https://superset.mcztest.com/api/v1/dataset/' \
  -H "Authorization: Bearer $TOKEN"
```

### 5. Create a Chart

```bash
curl -X POST 'https://superset.mcztest.com/api/v1/chart/' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "slice_name": "My Chart",
    "viz_type": "table",
    "datasource_id": 1,
    "datasource_type": "table",
    "params": "{\"metrics\":[\"count\"],\"groupby\":[]}"
  }'
```

### 6. List Charts

```bash
curl -X GET 'https://superset.mcztest.com/api/v1/chart/' \
  -H "Authorization: Bearer $TOKEN"
```

### 7. Create a Dashboard

```bash
curl -X POST 'https://superset.mcztest.com/api/v1/dashboard/' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "dashboard_title": "My Dashboard",
    "slug": "my-dashboard",
    "position_json": "{}",
    "published": true
  }'
```

### 8. List Dashboards

```bash
curl -X GET 'https://superset.mcztest.com/api/v1/dashboard/' \
  -H "Authorization: Bearer $TOKEN"
```

### 9. Execute SQL Query

```bash
curl -X POST 'https://superset.mcztest.com/api/v1/sqllab/execute/' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "database_id": 1,
    "sql": "SELECT * FROM my_table LIMIT 10",
    "schema": "public"
  }'
```

### 10. Export Dashboard

```bash
curl -X GET 'https://superset.mcztest.com/api/v1/dashboard/export/?q=!(1)' \
  -H "Authorization: Bearer $TOKEN" \
  -o dashboard_export.zip
```

## Python SDK Example

Install the Superset Python client:

```bash
pip install apache-superset-client
```

Example usage:

```python
from superset_client import SupersetClient

# Initialize client
client = SupersetClient(
    host='https://superset.mcztest.com',
    username='admin',
    password='admin'
)

# Authenticate
client.login()

# Create a database connection
database = client.databases.create(
    database_name='my_db',
    sqlalchemy_uri='postgresql://user:pass@host:5432/db'
)

# Create a dataset
dataset = client.datasets.create(
    database=database['id'],
    schema='public',
    table_name='users'
)

# Create a chart
chart = client.charts.create(
    slice_name='User Count',
    viz_type='big_number_total',
    datasource_id=dataset['id'],
    datasource_type='table',
    params={
        'metric': 'count',
        'adhoc_filters': []
    }
)

# Create a dashboard
dashboard = client.dashboards.create(
    dashboard_title='Analytics Dashboard',
    slug='analytics',
    position_json={},
    published=True
)

# Add chart to dashboard
client.dashboards.add_chart(
    dashboard_id=dashboard['id'],
    chart_id=chart['id']
)
```

## JavaScript/TypeScript Example

```typescript
// Using fetch API
const API_BASE = 'https://superset.mcztest.com/api/v1';

// Login and get token
async function login() {
  const response = await fetch(`${API_BASE}/security/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: 'admin',
      password: 'admin',
      provider: 'db',
      refresh: true
    })
  });
  const data = await response.json();
  return data.access_token;
}

// Create a dashboard
async function createDashboard(token: string) {
  const response = await fetch(`${API_BASE}/dashboard/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      dashboard_title: 'My Dashboard',
      slug: 'my-dashboard',
      position_json: '{}',
      published: true
    })
  });
  return await response.json();
}

// Usage
const token = await login();
const dashboard = await createDashboard(token);
console.log('Dashboard created:', dashboard);
```

## Important Notes

1. **Security**: Change default credentials immediately
2. **Rate Limiting**: API has rate limits (check response headers)
3. **Pagination**: List endpoints support pagination with `page` and `page_size` params
4. **Filtering**: Use `q` parameter for complex filtering (see Swagger docs)
5. **CSRF Protection**: Web sessions require CSRF token
6. **Token Expiry**: Access tokens expire; use refresh tokens to get new ones

## Troubleshooting

### Token Expired
```bash
# Use refresh token to get new access token
curl -X POST 'https://superset.mcztest.com/api/v1/security/refresh' \
  -H 'Content-Type: application/json' \
  -d '{"refresh_token": "your_refresh_token"}'
```

### Check API Health
```bash
curl 'https://superset.apps.homelab/health'
```

### View Logs
```bash
# Web server logs
kubectl logs -n superset -l app.kubernetes.io/name=superset,app.kubernetes.io/component=superset

# Worker logs
kubectl logs -n superset -l app.kubernetes.io/name=superset,app.kubernetes.io/component=worker

# Celery beat logs
kubectl logs -n superset -l app.kubernetes.io/name=superset,app.kubernetes.io/component=beat
```

## Additional Resources

- **Official API Docs**: https://superset.apache.org/docs/api
- **REST API Reference**: https://superset.apps.homelab/swagger/v1
- **Source Code**: https://github.com/apache/superset
- **Community**: https://preset.io/community/

## Deployment Details

- **Kubernetes Namespace**: `superset`
- **Helm Chart**: `superset/superset`
- **Image Version**: `apache/superset:4.0.2`
- **Database**: PostgreSQL (internal, superset-postgres:5432)
- **Cache**: Redis (internal, superset-redis:6379)
- **Ingress**: Nginx with cert-manager TLS
