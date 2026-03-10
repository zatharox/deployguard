# DeployGuard API Examples

## Table of Contents
- [Authentication](#authentication)
- [Running Risk Analysis](#running-risk-analysis)
- [Webhook Integration](#webhook-integration)
- [Enterprise Features](#enterprise-features)
- [Admin Operations](#admin-operations)

## Authentication

### Register New User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "full_name": "John Doe"
  }'
```

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "tenant": "default",
  "role": "owner"
}
```

## Running Risk Analysis

### Demo Scenarios

Run predefined risk scenarios:

```bash
# Low risk scenario
curl -X POST http://localhost:8000/api/v1/analysis/demo/run/low \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Tenant-Slug: default"

# High risk scenario  
curl -X POST http://localhost:8000/api/v1/analysis/demo/run/high \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Tenant-Slug: default"
```

### Manual Analysis

Analyze a specific PR:

```bash
curl -X POST http://localhost:8000/api/v1/analysis/manual \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Tenant-Slug: default" \
  -H "Content-Type: application/json" \
  -d '{
    "repository_id": "my-repo-123",
    "pr_id": 456
  }'
```

### Python Example

```python
import requests

# Authenticate
auth = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "user@example.com", "password": "password"}
).json()

token = auth["access_token"]
tenant = auth["tenant"]

# Run analysis
headers = {
    "Authorization": f"Bearer {token}",
    "X-Tenant-Slug": tenant
}

response = requests.post(
    "http://localhost:8000/api/v1/analysis/demo/run/high",
    headers=headers
)

result = response.json()
print(f"Risk Level: {result['analysis']['risk_level']}")
print(f"Risk Score: {result['analysis']['risk_score']}")
print(f"\nSignals:")
for signal in result['analysis']['signals']:
    print(f"  - {signal['name']}: {signal['score']}")
```

## Webhook Integration

### Azure DevOps Webhook

Set up webhook endpoint:

```bash
# Webhook URL
POST https://your-domain.com/api/v1/webhook/azure-devops

# Headers
X-Tenant-Slug: your-tenant
X-API-Key: your-api-key-here

# Body (sent by Azure DevOps)
{
  "eventType": "git.pullrequest.created",
  "resource": {
    "repository": { ... },
    "pullRequestId": 123,
    ...
  }
}
```

### Test Webhook Locally

```bash
curl -X POST http://localhost:8000/api/v1/webhook/azure-devops \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Slug: default" \
  -H "X-API-Key: test-api-key" \
  -d '{
    "eventType": "git.pullrequest.updated",
    "resource": {
      "repository": {
        "id": "test-repo",
        "name": "my-repository"
      },
      "pullRequestId": 123,
      "title": "Feature: Add new component"
    }
  }'
```

## Enterprise Features

### Create Tenant

```bash
curl -X POST http://localhost:8000/api/v1/enterprise/tenants \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Tenant-Slug: default" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corp",
    "slug": "acme",
    "plan": "enterprise"
  }'
```

### Create API Key

```bash
curl -X POST http://localhost:8000/api/v1/enterprise/api-keys \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Tenant-Slug: default" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Webhook Key",
    "expires_in_days": 365
  }'
```

Response:
```json
{
  "id": 1,
  "name": "Production Webhook Key",
  "key": "dgk_live_abc123xyz...",
  "created_at": "2026-03-10T10:30:00Z",
  "expires_at": "2027-03-10T10:30:00Z"
}
```

### View Usage Metrics

```bash
curl -X GET "http://localhost:8000/api/v1/enterprise/usage?days=30" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Tenant-Slug: default"
```

## Admin Operations

### Test Azure DevOps Connectivity

```bash
curl -X POST http://localhost:8000/api/v1/azure/test-connection \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Tenant-Slug: default" \
  -H "Content-Type: application/json" \
  -d '{
    "organization": "your-org",
    "project": "your-project",
    "pat": "your-personal-access-token"
  }'
```

### Get Webhook Setup Guide

```bash
curl -X GET http://localhost:8000/api/v1/azure/webhook-setup-guide \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Tenant-Slug: default"
```

### System Statistics (Admin Only)

```bash
curl -X GET http://localhost:8000/api/v1/admin/stats \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "X-Tenant-Slug: default"
```

## JavaScript/TypeScript Example

```typescript
class DeployGuardClient {
  private baseUrl: string;
  private token: string | null = null;
  private tenant: string | null = null;

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  async login(email: string, password: string) {
    const response = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    
    const data = await response.json();
    this.token = data.access_token;
    this.tenant = data.tenant;
    return data;
  }

  async runAnalysis(scenario: 'low' | 'medium' | 'high' | 'critical') {
    if (!this.token) throw new Error('Not authenticated');
    
    const response = await fetch(
      `${this.baseUrl}/api/v1/analysis/demo/run/${scenario}`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'X-Tenant-Slug': this.tenant!
        }
      }
    );
    
    return await response.json();
  }

  async getUsage(days: number = 30) {
    if (!this.token) throw new Error('Not authenticated');
    
    const response = await fetch(
      `${this.baseUrl}/api/v1/enterprise/usage?days=${days}`,
      {
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'X-Tenant-Slug': this.tenant!
        }
      }
    );
    
    return await response.json();
  }
}

// Usage
const client = new DeployGuardClient();
await client.login('user@example.com', 'password');
const analysis = await client.runAnalysis('high');
console.log(analysis);
```

## Docker Deployment

### Using Docker Compose

```bash
# Create .env file with your configuration
cp .env.example .env
# Edit .env with your Azure DevOps credentials

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

### Environment Variables

Required variables in `.env`:

```bash
# Database
DATABASE_URL=postgresql://deployguard:password@postgres:5432/deployguard

# Redis
REDIS_URL=redis://redis:6379/0

# Azure DevOps
AZURE_DEVOPS_ORG=your-organization
AZURE_DEVOPS_PROJECT=your-project
AZURE_DEVOPS_PAT=your-personal-access-token

# Security
SECRET_KEY=your-secret-key-min-32-chars

# Notifications (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

## Rate Limiting

API has rate limits per endpoint category:
- Default endpoints: 60 requests/minute
- Analysis endpoints: 30 requests/minute  
- Webhook endpoints: 100 requests/minute

Rate limit info in response headers:
```
X-RateLimit-Remaining: 45
```

## Error Handling

```python
import requests

response = requests.post(url, headers=headers, json=data)

if response.status_code == 429:
    retry_after = response.headers.get('Retry-After', 60)
    print(f"Rate limited. Retry after {retry_after} seconds")
elif response.status_code == 401:
    print("Authentication failed. Check your token")
elif response.status_code == 403:
    print("Forbidden. Check your permissions")
else:
    result = response.json()
```
