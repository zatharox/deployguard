# Setup Guide

This guide will walk you through setting up DeployGuard from scratch.

## 1. Development Environment Setup

### 1.1 Install Python 3.9+

**macOS:**
```bash
brew install python@3.11
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

**Windows:**
Download from [python.org](https://www.python.org/downloads/)

### 1.2 Install PostgreSQL

**macOS:**
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Ubuntu/Debian:**
```bash
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows:**
Download from [postgresql.org](https://www.postgresql.org/download/windows/)

### 1.3 Install Redis (Optional, for Celery)

**macOS:**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt install redis-server
sudo systemctl start redis
```

---

## 2. Project Setup

### 2.1 Clone and Install

```bash
git clone https://github.com/yourusername/deployguard.git
cd deployguard

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2.2 Configure Environment

```bash
cp .env.example .env
```

Edit `.env` file with your credentials.

### 2.3 Create Database

```bash
# Using psql
psql -U postgres
CREATE DATABASE deployguard;
CREATE USER deployguard_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE deployguard TO deployguard_user;
\q

# Or using createdb
createdb -U postgres deployguard
```

Update `DATABASE_URL` in `.env`:
```
DATABASE_URL=postgresql://deployguard_user:your_password@localhost:5432/deployguard
```

---

## 3. Azure DevOps Configuration

### 3.1 Create Personal Access Token

1. Sign in to Azure DevOps
2. Click user icon → Personal access tokens
3. Click "New Token"
4. Configure:
   - **Name**: DeployGuard
   - **Organization**: Select your org
   - **Expiration**: 90 days (or custom)
   - **Scopes**: Custom defined
     - ✅ Code: Read
     - ✅ Pull Request Threads: Read & Write
     - ✅ Build: Read
5. Click "Create"
6. **Copy the token** (you won't see it again!)

Add to `.env`:
```env
AZURE_DEVOPS_PAT=your_pat_token_here
```

### 3.2 Get Organization and Project Names

Your Azure DevOps URL looks like:
```
https://dev.azure.com/{organization}/{project}
```

Example: `https://dev.azure.com/contoso/MyProject`
- Organization: `contoso`
- Project: `MyProject`

Add to `.env`:
```env
AZURE_DEVOPS_ORG=contoso
AZURE_DEVOPS_PROJECT=MyProject
```

---

## 4. Run the Application

### 4.1 Start the Server

```bash
python main.py
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 4.2 Verify Installation

Open browser to:
- API: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

---

## 5. Configure Webhooks

### 5.1 For Local Development (ngrok)

```bash
# Install ngrok
brew install ngrok  # or download from ngrok.com

# Start tunnel
ngrok http 8000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
```

### 5.2 Create Service Hook in Azure DevOps

1. Go to Project Settings
2. Click "Service hooks"
3. Click "+" to create subscription
4. Select "Web Hooks"
5. Configure trigger:
   - **Event**: Pull request created
   - **Repository**: (select your repo or "Any")
6. Click "Next"
7. Configure action:
   - **URL**: `https://your-domain.com/api/v1/webhook/azure-devops`
     - For local dev: `https://abc123.ngrok.io/api/v1/webhook/azure-devops`
   - **Resource details to send**: All
8. Test the webhook
9. Click "Finish"

**Repeat for "Pull request updated" event.**

---

## 6. Test the Integration

### 6.1 Create a Test PR

1. Create a branch in Azure DevOps
2. Make some changes
3. Create a Pull Request

### 6.2 Check Logs

You should see in the terminal:
```
webhook_received event_type=git.pullrequest.created
starting_pr_analysis pr_id=123
pr_analysis_completed pr_id=123 risk_score=4.5
```

### 6.3 Check PR Comment

A comment should appear in the PR with:
- Risk score
- Risk signals
- Recommendations

---

## 7. Troubleshooting

### Issue: Can't connect to database

**Solution:**
```bash
# Check if PostgreSQL is running
pg_isready -U postgres

# Restart PostgreSQL
brew services restart postgresql@15  # macOS
sudo systemctl restart postgresql    # Linux
```

### Issue: Azure DevOps 401 Unauthorized

**Solution:**
- Verify PAT is correct in `.env`
- Check PAT hasn't expired
- Verify PAT has correct scopes
- Try creating a new PAT

### Issue: Webhook not receiving events

**Solution:**
- Check webhook URL is correct
- Verify ngrok is running (for local dev)
- Check service hook status in Azure DevOps
- Look for errors in Service Hooks history

### Issue: Import errors

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

## 8. Next Steps

### 8.1 Collect Historical Data

Run a script to backfill pipeline history:

```bash
python scripts/backfill_pipeline_data.py
```

### 8.2 Customize Risk Thresholds

Edit `.env`:
```env
HIGH_RISK_THRESHOLD=7.0
MEDIUM_RISK_THRESHOLD=4.0
MAX_LINES_LOW_RISK=300
```

### 8.3 Deploy to Production

See [README.md](README.md) deployment section for:
- Railway deployment
- Render deployment
- Docker deployment

---

## 9. Development Tips

### Run in Debug Mode

```bash
# Set in .env
DEBUG=True

# Run with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### View Database

```bash
psql -U deployguard_user -d deployguard

# List tables
\dt

# Query data
SELECT * FROM pr_analysis ORDER BY analyzed_at DESC LIMIT 10;
```

### Run Tests

```bash
pytest
pytest -v  # verbose
pytest --cov=.  # with coverage
```

---

## 10. Need Help?

- **Documentation**: Check [README.md](README.md)
- **Issues**: [GitHub Issues](https://github.com/yourusername/deployguard/issues)
- **Email**: support@deployguard.dev

---

**You're all set! Happy deploying! 🚀**
