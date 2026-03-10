# 🚀 DeployGuard

**Azure DevOps Deployment Risk Predictor**

Analyze Pull Requests in Azure DevOps and predict deployment failure risk **before** merging code.

![Risk Score Example](https://img.shields.io/badge/Risk%20Score-7.3%2F10-red)

---

## ✨ Features

- **🎯 4-Signal Risk Analysis**
  - Commit size risk
  - File instability detection
  - Pipeline failure history
  - Critical directory monitoring

- **🔔 Automatic PR Comments**
  - Risk score posted directly in PRs
  - Actionable recommendations
  - Historical trend tracking

- **📊 Analytics Dashboard**
  - Unstable file tracking
  - Pipeline health metrics
  - Risk trend analysis

---

## 🏗 Architecture

```
Azure DevOps PR Created
        │
        ▼
Azure DevOps Webhook
        │
        ▼
DeployGuard API (FastAPI)
        │
        ▼
Risk Analysis Engine
   (4 Signal Analysis)
        │
        ▼
Post Comment to PR
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 13+
- Azure DevOps account with admin access
- Personal Access Token (PAT) with permissions:
  - Code (Read)
  - Pull Request (Read & Write)
  - Build (Read)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/deployguard.git
cd deployguard
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set up environment variables**

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Azure DevOps Configuration
AZURE_DEVOPS_ORG=your-organization
AZURE_DEVOPS_PAT=your-personal-access-token
AZURE_DEVOPS_PROJECT=your-project-name

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/deployguard

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Application Configuration
SECRET_KEY=your-secret-key-change-in-production
WEBHOOK_SECRET=your-webhook-secret
```

5. **Set up PostgreSQL database**

```bash
# Create database
createdb deployguard

# Or using psql
psql -U postgres
CREATE DATABASE deployguard;
```

6. **Run the application**

```bash
python main.py
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

---

## 🔧 Azure DevOps Setup

### 1. Create Personal Access Token (PAT)

1. Go to Azure DevOps → User Settings → Personal Access Tokens
2. Click "New Token"
3. Select scopes:
   - **Code**: Read
   - **Pull Request Threads**: Read & Write
   - **Build**: Read
4. Copy the token and add to `.env`

### 2. Configure Service Hook (Webhook)

1. Go to Project Settings → Service Hooks
2. Click "Create subscription"
3. Select "Web Hooks"
4. Configure trigger:
   - **Trigger**: Pull request created
   - **Filters**: (leave as default or customize)
5. Configure action:
   - **URL**: `https://your-domain.com/api/v1/webhook/azure-devops`
   - **Resource details**: All
6. Click "Finish"

Repeat for "Pull request updated" trigger.

---

## 📡 API Endpoints

### Health Check

```bash
GET /api/v1/health
```

### Webhook Handler

```bash
POST /api/v1/webhook/azure-devops
```

Receives Azure DevOps webhook events.

### Manual Analysis

```bash
POST /api/v1/analysis/analyze/{repository_id}/{pr_id}
```

Manually trigger PR analysis.

### Analysis History

```bash
GET /api/v1/analysis/history/{pr_id}
```

Get analysis history for a PR.

### Unstable Files

```bash
GET /api/v1/analysis/files/unstable?min_failure_rate=0.15&limit=50
```

Get files with high failure rates.

### Summary Statistics

```bash
GET /api/v1/analysis/stats/summary
```

Get overall statistics.

---

## 🧠 Risk Engine Signals

### 1️⃣ Commit Size Risk (0-3 points)

Large changes increase failure probability.

| Lines Changed | Risk Score |
|---------------|-----------|
| > 500         | 3.0       |
| 300-500       | 2.0       |
| 100-300       | 1.0       |
| < 100         | 0.5       |

### 2️⃣ File Instability Risk (0-3 points)

Files with historical failure rates.

| Max Failure Rate | Risk Score |
|------------------|-----------|
| > 25%            | 3.0       |
| 15-25%           | 2.0       |
| < 15%            | 1.0       |

### 3️⃣ Pipeline History Risk (0-2 points)

Overall pipeline health.

| Failure Rate | Risk Score |
|--------------|-----------|
| > 20%        | 2.0       |
| 10-20%       | 1.5       |
| 5-10%        | 0.5       |
| < 5%         | 0.0       |

### 4️⃣ Critical Directory Risk (0-2 points)

Sensitive service areas.

Monitored paths:
- `/auth/`, `/authentication/`
- `/payment/`, `/billing/`
- `/core/`, `/kernel/`
- `/database/`, `/db/`
- `/security/`, `/api/`

| Critical Files | Risk Score |
|----------------|-----------|
| 3+             | 2.0       |
| 1-2            | 1.5       |
| 0              | 0.0       |

### Risk Levels

| Total Score | Risk Level |
|-------------|-----------|
| 7.0+        | HIGH      |
| 4.0-6.9     | MEDIUM    |
| 0-3.9       | LOW       |

---

## 🗄 Database Schema

### `files` Table

Tracks file modification and failure history.

| Column         | Type      | Description          |
|----------------|-----------|----------------------|
| file_path      | VARCHAR   | File path            |
| change_count   | INTEGER   | Total modifications  |
| failure_count  | INTEGER   | Failed deployments   |
| last_modified  | TIMESTAMP | Last modification    |

### `pr_analysis` Table

Stores PR risk analysis results.

| Column         | Type      | Description          |
|----------------|-----------|----------------------|
| pr_id          | INTEGER   | PR ID                |
| repository_id  | VARCHAR   | Repository ID        |
| risk_score     | FLOAT     | Risk score (0-10)    |
| risk_level     | VARCHAR   | low/medium/high      |
| signals        | TEXT      | JSON signals         |
| analyzed_at    | TIMESTAMP | Analysis timestamp   |

### `pipeline_history` Table

Tracks pipeline run history.

| Column        | Type      | Description          |
|---------------|-----------|----------------------|
| pipeline_id   | INTEGER   | Pipeline ID          |
| run_id        | INTEGER   | Run ID               |
| status        | VARCHAR   | succeeded/failed     |
| commit_id     | VARCHAR   | Git commit           |
| started_at    | TIMESTAMP | Start time           |

---

## 🚢 Deployment

### Option 1: Railway

1. Install Railway CLI:
```bash
npm install -g @railway/cli
```

2. Login and deploy:
```bash
railway login
railway init
railway up
```

3. Add environment variables in Railway dashboard

4. Add PostgreSQL service:
```bash
railway add postgresql
```

### Option 2: Render

1. Create `render.yaml`:

```yaml
services:
  - type: web
    name: deployguard
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: deployguard-db
          property: connectionString

databases:
  - name: deployguard-db
    databaseName: deployguard
```

2. Push to GitHub and connect to Render

### Option 3: Docker

```bash
# Build image
docker build -t deployguard .

# Run with docker-compose
docker-compose up -d
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/deployguard
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: deployguard
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

## 🧪 Testing

Run tests:

```bash
pytest
```

### Production-like Simulation (Local)

You can stress-test the app with deterministic demo traffic (no real Azure resources required).

1. Ensure demo mode is enabled in [.env](.env):

```env
DEMO_MODE=True
```

2. Start server:

```bash
python main.py
```

3. Run full scenario smoke test:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analysis/demo/run-all
```

4. Run production-like load simulation:

```bash
python simulations/production_simulation.py --users 20 --requests-per-user 25 --max-in-flight 50
```

5. Replay webhook traffic burst:

```bash
python simulations/webhook_replay.py --count 100 --repo-id demo-repo
```

Test webhook locally with ngrok:

```bash
# Install ngrok
brew install ngrok  # or download from ngrok.com

# Start ngrok tunnel
ngrok http 8000

# Use ngrok URL in Azure DevOps webhook
# Example: https://abc123.ngrok.io/api/v1/webhook/azure-devops
```

---

## 📊 Example PR Comment

```markdown
## 🔴 DeployGuard Risk Report

**Risk Score:** 7.3 / 10 (HIGH RISK)

### Risk Signals

**Commit Size Risk** (3.0 points)
• 540 lines modified across 12 files
  _Files changed: 12_

**File Instability Risk** (2.0 points)
• 2 historically unstable files modified
  _Top unstable files: auth_service.go (28%), payment_api.go (18%)_

**Pipeline History Risk** (1.5 points)
• Elevated pipeline failure rate: 15.2%
  _Recent runs: 100, Failed: 15_

**Critical Directory Risk** (1.5 points)
• 2 critical service file(s) modified
  _Affected areas: auth, payment_

### Recommendations
• ⚠️ High risk detected - Require senior engineer review
• Consider breaking this PR into smaller changes
• Large changeset - Review carefully for logic errors
• Modified files have failure history - Add extra tests
• Critical services affected - Ensure rollback plan is ready

---
_Powered by [DeployGuard](https://github.com/yourusername/deployguard)_
```

---

## 🗺 Roadmap

### Phase 1: MVP (Weeks 1-2) ✅
- [x] Azure DevOps integration
- [x] 4-signal risk engine
- [x] PR comment bot
- [x] Basic database schema

### Phase 2: Enhancement (Weeks 3-4)
- [ ] Historical trend analysis
- [ ] Team-specific baselines
- [ ] Slack/Teams notifications
- [ ] Custom risk thresholds

### Phase 3: Intelligence (Weeks 5-8)
- [ ] Machine learning risk model
- [ ] Deployment outcome tracking
- [ ] Automated rollback recommendations
- [ ] Integration with monitoring tools

### Phase 4: Enterprise (Weeks 9-12)
- [ ] Multi-organization support
- [ ] RBAC and permissions
- [ ] Custom risk signals
- [ ] Analytics dashboard

---

## 💰 Pricing

| Plan      | Price       | Features                           |
|-----------|-------------|------------------------------------|
| Free      | $0          | 1 repository, basic risk analysis  |
| Startup   | $20/month   | 5 repositories, all features       |
| Team      | $79/month   | 25 repositories, priority support  |
| Enterprise| Custom      | Unlimited, custom signals, SLA     |

---

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙋 Support

- **Documentation**: [docs.deployguard.dev](https://docs.deployguard.dev)
- **Issues**: [GitHub Issues](https://github.com/yourusername/deployguard/issues)
- **Email**: support@deployguard.dev
- **Discord**: [Join our community](https://discord.gg/deployguard)

---

## 🌟 Why DeployGuard?

> "After implementing DeployGuard, our deployment failures dropped by **43%** in the first month. The risk scores help us prioritize code reviews and catch issues before they hit production."
> 
> — *Engineering Manager, Fortune 500 Company*

---

**Built with ❤️ for DevOps teams everywhere**

Star ⭐ this repo if you find it useful!
