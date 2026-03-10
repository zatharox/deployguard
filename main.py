import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import structlog

from config import get_settings
from api.routes import webhook, analysis, health, enterprise, auth
from db.database import engine, Base
from services.logging_utils import bind_log_context, clear_log_context, get_request_id

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app with enhanced styling
app = FastAPI(
    title="🛡️ DeployGuard",
    description="""
    ## Azure DevOps Deployment Risk Predictor
    
    Predict deployment failures **before** they happen using advanced risk analysis.
    
    ### Features
    * 🎯 **4-Signal Risk Analysis** - Comprehensive risk scoring
    * 🔔 **Automatic PR Comments** - Get insights directly in your PRs
    * 📊 **Analytics Dashboard** - Track trends and patterns
    * ⚡ **Real-time Processing** - Instant risk assessments
    
    ### Quick Links
    * [GitHub Profile](https://github.com/zatharox)
    * [Documentation](https://docs.deployguard.dev)
    * [Support](mailto:support@deployguard.dev)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "DeployGuard Team",
        "email": "support@deployguard.dev",
        "url": "https://deployguard.dev"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    openapi_tags=[
        {
            "name": "health",
            "description": "🏥 Health check and system status endpoints"
        },
        {
            "name": "webhook",
            "description": "🔗 Azure DevOps webhook handlers for PR events"
        },
        {
            "name": "analysis",
            "description": "📊 Risk analysis and analytics endpoints"
        },
        {
            "name": "enterprise",
            "description": "🏢 Enterprise tenant and account management"
        },
        {
            "name": "auth",
            "description": "🔐 Authentication and access control"
        }
    ]
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = get_request_id(request.headers.get("X-Request-ID"))
    start = time.perf_counter()
    bind_log_context(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        tenant_slug=request.headers.get("X-Tenant-Slug"),
    )
    logger.info("request_started")

    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.error("request_failed", duration_ms=duration_ms, error=str(exc))
        clear_log_context()
        raise

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info("request_completed", status_code=response.status_code, duration_ms=duration_ms)
    clear_log_context()
    return response

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(webhook.router, prefix="/api/v1/webhook", tags=["webhook"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])
app.include_router(enterprise.router, prefix="/api/v1/enterprise", tags=["enterprise"])

# Custom landing page
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing_page():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DeployGuard - Azure DevOps Risk Predictor</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: radial-gradient(1200px 500px at 90% -10%, #dbeafe 0%, transparent 60%), linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
                min-height: 100vh;
                display: flex;
                align-items: flex-start;
                justify-content: center;
                color: #0f172a;
                padding: 28px 20px;
            }
            .container {
                max-width: 1180px;
                width: 100%;
                padding: 28px;
                text-align: center;
                background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
                border: 1px solid #dbe4ef;
                border-radius: 24px;
                box-shadow: 0 12px 30px rgba(2, 6, 23, 0.05), 0 28px 90px rgba(2, 6, 23, 0.09);
            }
            .topbar {
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 12px;
                padding: 8px 10px 20px;
                border-bottom: 1px solid #e2e8f0;
                margin-bottom: 22px;
            }
            .brand {
                display: flex;
                align-items: center;
                gap: 10px;
                font-weight: 700;
                color: #0f172a;
            }
            .topbar-actions { display: flex; align-items: center; gap: 10px; }
            .theme-toggle {
                border: 1px solid #cbd5e1;
                background: #ffffff;
                color: #0f172a;
                border-radius: 10px;
                padding: 8px 10px;
                font-size: 12px;
                font-weight: 700;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            .theme-toggle:hover { background: #f8fafc; }
            .brand-dot {
                width: 10px;
                height: 10px;
                border-radius: 999px;
                background: #22c55e;
                box-shadow: 0 0 0 6px rgba(34, 197, 94, 0.15);
            }
            .logo {
                font-size: 44px;
                margin-bottom: 8px;
            }
            @keyframes pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.05); }
            }
            h1 {
                font-size: 42px;
                font-weight: 800;
                margin-bottom: 8px;
                letter-spacing: -0.02em;
                line-height: 1.1;
            }
            .subtitle {
                font-size: 17px;
                margin-bottom: 28px;
                color: #475569;
            }
            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 16px;
                margin: 30px 0;
            }
            .feature {
                background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
                border: 1px solid #e5edf5;
                border-radius: 14px;
                padding: 22px;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                text-align: left;
            }
            .feature:hover {
                transform: translateY(-2px);
                box-shadow: 0 14px 30px rgba(15,23,42,0.08);
            }
            .feature-icon {
                width: 42px;
                height: 42px;
                border-radius: 10px;
                background: #eef2ff;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                font-size: 20px;
                margin-bottom: 12px;
            }
            .feature h3 {
                font-size: 17px;
                margin-bottom: 8px;
            }
            .feature p {
                color: #475569;
                line-height: 1.6;
                font-size: 14px;
            }
            .cta-buttons {
                display: flex;
                gap: 12px;
                justify-content: center;
                flex-wrap: wrap;
            }
            .btn {
                padding: 12px 22px;
                font-size: 14px;
                border-radius: 10px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                transition: all 0.3s ease;
                font-weight: 700;
            }
            .btn-primary {
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                color: #ffffff;
                box-shadow: 0 6px 16px rgba(15,23,42,0.2);
            }
            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(15,23,42,0.26);
            }
            .btn-secondary {
                background: #ffffff;
                color: #0f172a;
                border: 1px solid #cbd5e1;
            }
            .btn-secondary:hover {
                background: #f8fafc;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(3, minmax(160px, 1fr));
                gap: 12px;
                margin-top: 24px;
            }
            .stat {
                text-align: left;
                padding: 14px;
                border: 1px solid #e5edf5;
                background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
                border-radius: 12px;
            }
            .stat-number {
                font-size: 30px;
                font-weight: 700;
                display: block;
            }
            .stat-label {
                font-size: 11px;
                color: #64748b;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .status-badge {
                display: inline-block;
                background: #eef2ff;
                color: #3730a3;
                padding: 7px 14px;
                border-radius: 999px;
                border: 1px solid #c7d2fe;
                font-size: 12px;
                font-weight: 600;
                margin-bottom: 10px;
            }
            .section-title {
                font-size: 24px;
                margin: 34px 0 12px;
                text-align: left;
            }
            .scenario-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                gap: 12px;
                margin-top: 20px;
            }
            .scenario-btn {
                border: 1px solid #cbd5e1;
                background: #ffffff;
                color: #0f172a;
                border-radius: 10px;
                padding: 12px 10px;
                cursor: pointer;
                font-weight: 700;
                letter-spacing: 0.3px;
                transition: all 0.2s ease;
            }
            .scenario-btn:hover { transform: translateY(-2px); }
            .scenario-btn.low { border-color: #86efac; }
            .scenario-btn.medium { border-color: #fcd34d; }
            .scenario-btn.high { border-color: #fca5a5; }
            .scenario-btn.critical { border-color: #f9a8d4; }
            .scenario-btn:disabled { opacity: 0.5; cursor: wait; }
            .result-card {
                margin-top: 22px;
                background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
                border: 1px solid #e5edf5;
                border-radius: 14px;
                padding: 18px;
                text-align: left;
            }
            .result-grid {
                display: grid;
                grid-template-columns: 190px 1fr;
                gap: 16px;
                align-items: center;
                margin: 10px 0 16px;
            }
            .gauge-wrap {
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .gauge {
                width: 130px;
                height: 130px;
                border-radius: 50%;
                background: conic-gradient(#10b981 0deg, #10b981 0deg, #e2e8f0 0deg, #e2e8f0 360deg);
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
            }
            .gauge::after {
                content: '';
                width: 92px;
                height: 92px;
                border-radius: 50%;
                background: #ffffff;
                border: 1px solid #e2e8f0;
                position: absolute;
            }
            .gauge-label {
                position: relative;
                z-index: 1;
                text-align: center;
                line-height: 1.1;
            }
            .gauge-value {
                font-weight: 800;
                font-size: 24px;
                color: #0f172a;
            }
            .gauge-sub {
                font-size: 11px;
                color: #64748b;
                text-transform: uppercase;
                letter-spacing: 0.8px;
            }
            .result-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 10px;
                flex-wrap: wrap;
                margin-bottom: 14px;
            }
            .pill {
                padding: 6px 12px;
                border-radius: 999px;
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 0.4px;
            }
            .pill.low { background: rgba(16,185,129,0.16); color: #047857; }
            .pill.medium { background: rgba(245,158,11,0.16); color: #a16207; }
            .pill.high { background: rgba(239,68,68,0.16); color: #b91c1c; }
            .meter-wrap {
                margin: 10px 0 16px;
            }
            .meter {
                width: 100%;
                height: 12px;
                background: #e2e8f0;
                border-radius: 999px;
                overflow: hidden;
            }
            .meter-fill {
                height: 100%;
                width: 0%;
                border-radius: 999px;
                background: linear-gradient(90deg, #10b981 0%, #f59e0b 55%, #ef4444 100%);
                transition: width 0.35s ease;
            }
            .signal-list {
                list-style: none;
                display: grid;
                gap: 10px;
                margin-top: 12px;
            }
            .signal-item {
                padding: 10px;
                border-radius: 10px;
                background: #ffffff;
                border: 1px solid #e2e8f0;
            }
            .skeleton {
                position: relative;
                overflow: hidden;
                background: #e2e8f0 !important;
                color: transparent !important;
                border-color: #e2e8f0 !important;
            }
            .skeleton::before {
                content: '';
                position: absolute;
                inset: 0;
                transform: translateX(-100%);
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.7), transparent);
                animation: shimmer 1.1s infinite;
            }
            @keyframes shimmer { 100% { transform: translateX(100%); } }
            .mini {
                color: #64748b;
                font-size: 13px;
            }
            pre {
                margin-top: 14px;
                max-height: 220px;
                overflow: auto;
                border-radius: 10px;
                padding: 12px;
                background: #0f172a;
                color: #cbd5e1;
                font-size: 12px;
                white-space: pre-wrap;
            }
            .comment-preview {
                margin-top: 14px;
                max-height: 360px;
                overflow: auto;
                border-radius: 10px;
                padding: 14px;
                background: #0f172a;
                color: #cbd5e1;
                font-size: 13px;
                border: 1px solid #1e293b;
            }
            .comment-preview h2,
            .comment-preview h3,
            .comment-preview h4 {
                margin: 10px 0 8px;
                color: #f8fafc;
                font-size: 14px;
            }
            .comment-preview ul {
                margin: 8px 0 8px 18px;
            }
            .comment-preview li {
                margin: 3px 0;
            }
            .comment-preview table {
                width: 100%;
                border-collapse: collapse;
                margin: 10px 0;
                font-size: 12px;
            }
            .comment-preview th,
            .comment-preview td {
                border: 1px solid #334155;
                padding: 6px 8px;
                text-align: left;
            }
            .comment-preview th {
                color: #e2e8f0;
                background: #111827;
            }
            @media (max-width: 860px) {
                .container { padding: 24px; }
                h1 { font-size: 32px; }
                .stats { grid-template-columns: 1fr; }
                .topbar { justify-content: center; }
                .result-grid { grid-template-columns: 1fr; }
            }

            body.dark {
                background: radial-gradient(900px 500px at 90% -10%, #1e293b 0%, transparent 60%), linear-gradient(180deg, #0b1220 0%, #0f172a 100%);
                color: #e2e8f0;
            }
            body.dark .container {
                background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
                border-color: #1f2937;
                box-shadow: 0 20px 50px rgba(0,0,0,0.45);
            }
            body.dark .topbar { border-bottom-color: #1f2937; }
            body.dark .brand,
            body.dark h1,
            body.dark .gauge-value,
            body.dark .scenario-btn,
            body.dark .btn-secondary { color: #e2e8f0; }
            body.dark .subtitle,
            body.dark .mini,
            body.dark .stat-label,
            body.dark .gauge-sub { color: #94a3b8; }
            body.dark .feature,
            body.dark .stat,
            body.dark .result-card,
            body.dark .signal-item,
            body.dark .scenario-btn,
            body.dark .btn-secondary,
            body.dark .theme-toggle {
                background: #111827;
                border-color: #1f2937;
            }
            body.dark .feature-icon { background: #1e293b; }
            body.dark .theme-toggle:hover,
            body.dark .btn-secondary:hover { background: #0f172a; }
            body.dark .meter { background: #1f2937; }
            body.dark .gauge::after { background: #111827; border-color: #1f2937; }
            body.dark pre { background: #020617; color: #cbd5e1; }
            body.dark .comment-preview { background: #020617; color: #cbd5e1; border-color: #1e293b; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="topbar">
                <div class="brand"><span class="brand-dot"></span> DeployGuard Enterprise</div>
                <div class="topbar-actions">
                    <button class="theme-toggle" id="theme-toggle">🌙 Dark</button>
                    <div class="status-badge">Production Monitoring Active</div>
                </div>
            </div>
            <div class="logo">🛡️</div>
            <h1>DeployGuard</h1>
            <p class="subtitle">Enterprise-grade deployment risk intelligence for Azure DevOps teams</p>
            
            <div class="cta-buttons">
                <a href="/docs" class="btn btn-primary">API Documentation</a>
                <a href="/redoc" class="btn btn-secondary">Technical Reference</a>
            </div>
            
            <div class="features">
                <div class="feature">
                    <div class="feature-icon">🎯</div>
                    <h3>4-Signal Analysis</h3>
                    <p>Comprehensive risk scoring using commit size, file stability, pipeline history, and critical paths</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">🔔</div>
                    <h3>Auto PR Comments</h3>
                    <p>Get risk assessments posted directly to your Azure DevOps pull requests</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">📊</div>
                    <h3>Analytics Dashboard</h3>
                    <p>Track deployment trends and identify high-risk patterns</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">⚡</div>
                    <h3>Real-time Processing</h3>
                    <p>Instant risk analysis with webhook-based automation</p>
                </div>
            </div>
            
            <div class="stats">
                <div class="stat">
                    <span class="stat-number" id="analyses">0</span>
                    <span class="stat-label">Analyses Completed</span>
                </div>
                <div class="stat">
                    <span class="stat-number" id="risk-detected">0</span>
                    <span class="stat-label">High Risks Detected</span>
                </div>
                <div class="stat">
                    <span class="stat-number" id="files-tracked">0</span>
                    <span class="stat-label">Files Tracked</span>
                </div>
            </div>

            <h2 class="section-title">Scenario Validation Lab</h2>
            <p class="mini">Execute controlled scenarios and inspect model outputs in real time.</p>
            <div class="scenario-grid" id="scenario-grid">
                <button class="scenario-btn low" data-scenario="low">Run LOW</button>
                <button class="scenario-btn medium" data-scenario="medium">Run MEDIUM</button>
                <button class="scenario-btn high" data-scenario="high">Run HIGH</button>
                <button class="scenario-btn critical" data-scenario="critical">Run CRITICAL</button>
            </div>

            <div class="result-card" id="result-card" style="display:none;">
                <div class="result-header">
                    <h3 id="result-title">Scenario Result</h3>
                    <span id="result-level" class="pill">LEVEL</span>
                </div>

                <div class="result-grid">
                    <div class="gauge-wrap">
                        <div class="gauge" id="risk-gauge">
                            <div class="gauge-label">
                                <div class="gauge-value" id="result-score">0.0</div>
                                <div class="gauge-sub">risk / 10</div>
                            </div>
                        </div>
                    </div>
                    <div class="meter-wrap">
                        <div class="mini">Risk Score Trend</div>
                        <div class="meter"><div class="meter-fill" id="meter-fill"></div></div>
                    </div>
                </div>

                <div>
                    <strong>Signals</strong>
                    <ul class="signal-list" id="signal-list"></ul>
                </div>

                <div style="margin-top: 14px;">
                    <strong>PR Comment Preview</strong>
                    <div id="comment-preview" class="comment-preview"></div>
                </div>
            </div>
        </div>
        
        <script>
            let demoAuth = null;

            function setTheme(theme) {
                const dark = theme === 'dark';
                document.body.classList.toggle('dark', dark);
                const toggle = document.getElementById('theme-toggle');
                if (toggle) toggle.textContent = dark ? '☀️ Light' : '🌙 Dark';
                localStorage.setItem('dg-theme', dark ? 'dark' : 'light');
            }

            function initTheme() {
                const saved = localStorage.getItem('dg-theme');
                if (saved) {
                    setTheme(saved);
                } else {
                    setTheme(window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
                }

                const toggle = document.getElementById('theme-toggle');
                if (toggle) {
                    toggle.addEventListener('click', () => {
                        setTheme(document.body.classList.contains('dark') ? 'light' : 'dark');
                    });
                }
            }

            function setLoadingState(isLoading) {
                const card = document.getElementById('result-card');
                if (!card) return;

                if (isLoading) {
                    card.style.display = 'block';
                    document.getElementById('result-title').textContent = 'Running scenario...';
                    document.getElementById('result-level').textContent = 'PROCESSING';
                    document.getElementById('result-level').className = 'pill';
                    document.getElementById('comment-preview').textContent = 'Generating analysis...';
                    ['result-score', 'meter-fill', 'comment-preview'].forEach(id => {
                        const el = document.getElementById(id);
                        if (el) el.classList.add('skeleton');
                    });
                    document.getElementById('signal-list').innerHTML = '<li class="signal-item skeleton">Loading...</li><li class="signal-item skeleton">Loading...</li>';
                } else {
                    ['result-score', 'meter-fill', 'comment-preview'].forEach(id => {
                        const el = document.getElementById(id);
                        if (el) el.classList.remove('skeleton');
                    });
                }
            }

            async function getDemoAuth() {
                if (demoAuth && demoAuth.access_token && demoAuth.tenant) return demoAuth;

                const res = await fetch('/api/v1/auth/demo-bootstrap', { method: 'POST' });
                if (!res.ok) {
                    const text = await res.text();
                    throw new Error(`Demo bootstrap failed: ${text}`);
                }
                demoAuth = await res.json();
                return demoAuth;
            }

            async function refreshStats() {
                try {
                    const auth = await getDemoAuth();
                    const res = await fetch('/api/v1/analysis/stats/summary', {
                        headers: {
                            'Authorization': `Bearer ${auth.access_token}`,
                            'X-Tenant-Slug': auth.tenant,
                        }
                    });
                    if (!res.ok) throw new Error('Stats API failed');
                    const data = await res.json();
                    document.getElementById('analyses').textContent = data.total_analyses || 0;
                    document.getElementById('risk-detected').textContent = data.high_risk_prs || 0;
                    document.getElementById('files-tracked').textContent = data.total_tracked_files || 0;
                } catch (e) {
                    console.log('Stats unavailable', e);
                }
            }

            function renderResult(scenario, analysis, commentPreview) {
                const card = document.getElementById('result-card');
                const level = (analysis.risk_level || 'low').toLowerCase();
                const score = Number(analysis.risk_score || 0);

                document.getElementById('result-title').textContent = `Scenario: ${scenario.toUpperCase()}`;

                const levelPill = document.getElementById('result-level');
                levelPill.textContent = level.toUpperCase();
                levelPill.className = `pill ${level}`;

                document.getElementById('result-score').textContent = score.toFixed(1);
                document.getElementById('meter-fill').style.width = `${Math.max(0, Math.min(100, score * 10))}%`;
                const deg = Math.max(0, Math.min(360, score * 36));
                document.getElementById('risk-gauge').style.background = `conic-gradient(#10b981 0deg, #f59e0b ${Math.min(200, deg)}deg, #ef4444 ${deg}deg, #e2e8f0 ${deg}deg 360deg)`;

                const signalList = document.getElementById('signal-list');
                signalList.innerHTML = '';
                (analysis.signals || []).forEach(s => {
                    const li = document.createElement('li');
                    li.className = 'signal-item';
                    li.innerHTML = `<strong>${s.name}</strong> — ${s.score.toFixed(1)} pts<br><span class='mini'>${s.description}</span>`;
                    signalList.appendChild(li);
                });

                const commentEl = document.getElementById('comment-preview');
                commentEl.innerHTML = renderMarkdown(commentPreview || 'No preview available');
                commentEl.scrollTop = 0;
                card.style.display = 'block';
            }

            function escapeHtml(text) {
                return String(text)
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#39;');
            }

            function renderMarkdown(mdText) {
                const lines = String(mdText || '').split('\\n');
                let html = '';
                let inList = false;
                let inTable = false;

                const closeList = () => {
                    if (inList) {
                        html += '</ul>';
                        inList = false;
                    }
                };

                const closeTable = () => {
                    if (inTable) {
                        html += '</tbody></table>';
                        inTable = false;
                    }
                };

                for (let i = 0; i < lines.length; i++) {
                    const raw = lines[i];
                    const line = raw.trim();

                    if (!line) {
                        closeList();
                        closeTable();
                        continue;
                    }

                    if (/^\|.+\|$/.test(line)) {
                        const isDivider = /^\|\s*[-:]+\s*\|/.test(line.replace(/\|\s*[-:]+\s*/g, '|'));
                        if (isDivider) continue;

                        const cells = line.split('|').slice(1, -1).map(c => escapeHtml(c.trim()));
                        if (!inTable) {
                            closeList();
                            html += '<table><tbody>';
                            inTable = true;
                        }
                        html += `<tr>${cells.map(c => `<td>${c}</td>`).join('')}</tr>`;
                        continue;
                    }

                    closeTable();

                    if (line.startsWith('### ')) {
                        closeList();
                        html += `<h4>${escapeHtml(line.substring(4))}</h4>`;
                    } else if (line.startsWith('## ')) {
                        closeList();
                        html += `<h3>${escapeHtml(line.substring(3))}</h3>`;
                    } else if (line.startsWith('# ')) {
                        closeList();
                        html += `<h2>${escapeHtml(line.substring(2))}</h2>`;
                    } else if (line.startsWith('• ')) {
                        if (!inList) {
                            html += '<ul>';
                            inList = true;
                        }
                        html += `<li>${escapeHtml(line.substring(2))}</li>`;
                    } else if (line.startsWith('---')) {
                        closeList();
                        html += '<hr />';
                    } else {
                        closeList();
                        html += `<p>${escapeHtml(line)}</p>`;
                    }
                }

                closeList();
                closeTable();
                return html || '<p>No preview available</p>';
            }

            async function runScenario(scenario) {
                const buttons = document.querySelectorAll('.scenario-btn');
                buttons.forEach(b => b.disabled = true);
                setLoadingState(true);

                try {
                    const auth = await getDemoAuth();
                    const res = await fetch(`/api/v1/analysis/demo/run/${scenario}`, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${auth.access_token}`,
                            'X-Tenant-Slug': auth.tenant,
                        }
                    });
                    if (!res.ok) {
                        throw new Error('Scenario API failed');
                    }
                    const data = await res.json();
                    setLoadingState(false);
                    renderResult(scenario, data.analysis || {}, data.comment_preview || '');
                    await refreshStats();
                } catch (e) {
                    setLoadingState(false);
                    alert('Unable to run demo scenario. Ensure server is running and DEMO_MODE=True in .env.');
                    console.error(e);
                } finally {
                    buttons.forEach(b => b.disabled = false);
                }
            }

            document.querySelectorAll('.scenario-btn').forEach(btn => {
                btn.addEventListener('click', () => runScenario(btn.dataset.scenario));
            });

            initTheme();
            refreshStats();
        </script>
    </body>
    </html>
    """


@app.on_event("startup")
async def startup_event():
    settings = get_settings()
    logger.info("starting_deployguard", 
                org=settings.azure_devops_org,
                project=settings.azure_devops_project)


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("shutting_down_deployguard")


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
