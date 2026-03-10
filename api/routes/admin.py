"""
Admin dashboard for tenant and system management
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import structlog

from db.database import get_db
from db.models import User, Tenant, PRAnalysis, UsageEvent, Membership
from services.auth_service import get_current_user, check_role
from db.schemas import TenantResponse

router = APIRouter()
logger = structlog.get_logger()


@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    current_user: User = Depends(get_current_user),
    _role_check = Depends(check_role(["owner", "admin"]))
):
    """
    Admin dashboard for managing tenants, users, and system metrics
    """
    
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DeployGuard Admin Dashboard</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                color: #e2e8f0;
                padding: 20px;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            h1 { 
                font-size: 32px; 
                margin-bottom: 10px;
                background: linear-gradient(90deg, #60a5fa, #a78bfa);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .subtitle { color: #94a3b8; margin-bottom: 30px; }
            .grid { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); 
                gap: 20px; 
                margin-bottom: 30px;
            }
            .card {
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                padding: 24px;
            }
            .stat-card {
                text-align: center;
            }
            .stat-number {
                font-size: 48px;
                font-weight: bold;
                background: linear-gradient(135deg, #60a5fa, #a78bfa);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin: 10px 0;
            }
            .stat-label {
                color: #94a3b8;
                font-size: 14px;
            }
            .section-title {
                font-size: 20px;
                margin: 30px 0 15px;
                color: #f1f5f9;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                background: rgba(255, 255, 255, 0.03);
                border-radius: 12px;
                overflow: hidden;
            }
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }
            th {
                background: rgba(255, 255, 255, 0.05);
                font-weight: 600;
                color: #cbd5e1;
            }
            .btn {
                background: linear-gradient(135deg, #3b82f6, #8b5cf6);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
                transition: transform 0.2s;
            }
            .btn:hover { transform: translateY(-2px); }
            .btn-small {
                padding: 6px 12px;
                font-size: 12px;
            }
            .badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 500;
            }
            .badge.active { background: #10b981; color: white; }
            .badge.inactive { background: #6b7280; color: white; }
            .topbar {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
            }
            .nav {
                display: flex;
                gap: 20px;
            }
            .nav-link {
                color: #94a3b8;
                text-decoration: none;
                padding: 8px 16px;
                border-radius: 8px;
                transition: all 0.3s;
            }
            .nav-link:hover, .nav-link.active {
                background: rgba(255, 255, 255, 0.1);
                color: #f1f5f9;
            }
            .loading {
                text-align: center;
                color: #94a3b8;
                padding: 40px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="topbar">
                <div>
                    <h1>🛡️ DeployGuard Admin</h1>
                    <p class="subtitle">System Overview & Management</p>
                </div>
                <div class="nav">
                    <a href="/" class="nav-link">Dashboard</a>
                    <a href="/docs" class="nav-link">API Docs</a>
                    <a href="/api/v1/admin/dashboard" class="nav-link active">Admin</a>
                </div>
            </div>

            <div class="grid">
                <div class="card stat-card">
                    <div class="stat-label">Total Tenants</div>
                    <div class="stat-number" id="tenant-count">-</div>
                </div>
                <div class="card stat-card">
                    <div class="stat-label">Total Users</div>
                    <div class="stat-number" id="user-count">-</div>
                </div>
                <div class="card stat-card">
                    <div class="stat-label">Total Analyses</div>
                    <div class="stat-number" id="analysis-count">-</div>
                </div>
                <div class="card stat-card">
                    <div class="stat-label">High Risk PRs</div>
                    <div class="stat-number" id="high-risk-count">-</div>
                </div>
            </div>

            <h2 class="section-title">Tenant Overview</h2>
            <div class="card">
                <table id="tenant-table">
                    <thead>
                        <tr>
                            <th>Tenant</th>
                            <th>Plan</th>
                            <th>Users</th>
                            <th>Analyses</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="6" class="loading">Loading tenant data...</td></tr>
                    </tbody>
                </table>
            </div>

            <h2 class="section-title">Recent Usage Activity</h2>
            <div class="card">
                <table id="usage-table">
                    <thead>
                        <tr>
                            <th>Tenant</th>
                            <th>Event Type</th>
                            <th>Count (Last 24h)</th>
                            <th>Quota Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="4" class="loading">Loading usage data...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <script>
            async function loadAdminData() {
                try {
                    // Get current auth (from demo bootstrap or existing session)
                    const authRes = await fetch('/api/v1/auth/demo-bootstrap', { method: 'POST' });
                    if (!authRes.ok) throw new Error('Auth failed');
                    const auth = await authRes.json();

                    // Load system stats
                    const statsRes = await fetch('/api/v1/admin/stats', {
                        headers: {
                            'Authorization': `Bearer ${auth.access_token}`,
                            'X-Tenant-Slug': auth.tenant
                        }
                    });
                    if (statsRes.ok) {
                        const stats = await statsRes.json();
                        document.getElementById('tenant-count').textContent = stats.total_tenants || 0;
                        document.getElementById('user-count').textContent = stats.total_users || 0;
                        document.getElementById('analysis-count').textContent = stats.total_analyses || 0;
                        document.getElementById('high-risk-count').textContent = stats.high_risk_count || 0;
                    }

                    // Load tenant list
                    const tenantsRes = await fetch('/api/v1/enterprise/tenants', {
                        headers: {
                            'Authorization': `Bearer ${auth.access_token}`,
                            'X-Tenant-Slug': auth.tenant
                        }
                    });
                    if (tenantsRes.ok) {
                        const tenants = await tenantsRes.json();
                        const tbody = document.querySelector('#tenant-table tbody');
                        tbody.innerHTML = tenants.map(t => `
                            <tr>
                                <td><strong>${t.name}</strong><br><small>${t.slug}</small></td>
                                <td><span class="badge ${t.plan}">${t.plan}</span></td>
                                <td>-</td>
                                <td>-</td>
                                <td>${new Date(t.created_at).toLocaleDateString()}</td>
                                <td><button class="btn btn-small">Manage</button></td>
                            </tr>
                        `).join('') || '<tr><td colspan="6">No tenants found</td></tr>';
                    }

                } catch (e) {
                    console.error('Failed to load admin data:', e);
                }
            }

            loadAdminData();
        </script>
    </body>
    </html>
    """


@router.get("/stats")
async def get_system_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _role_check = Depends(check_role(["owner", "admin"]))
):
    """Get system-wide statistics"""
    
    total_tenants = db.query(Tenant).count()
    total_users = db.query(User).count()
    total_analyses = db.query(PRAnalysis).count()
    high_risk_count = db.query(PRAnalysis).filter(PRAnalysis.risk_level == "high").count()
    
    return {
        "total_tenants": total_tenants,
        "total_users": total_users,
        "total_analyses": total_analyses,
        "high_risk_count": high_risk_count
    }
