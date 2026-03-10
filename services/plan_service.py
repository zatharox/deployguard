from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import PRAnalysis, Tenant

PLAN_LIMITS = {
    "free": {"analyses_per_day": 50, "repos": 1, "members": 3},
    "startup": {"analyses_per_day": 500, "repos": 10, "members": 20},
    "team": {"analyses_per_day": 3000, "repos": 50, "members": 100},
    "enterprise": {"analyses_per_day": 100000, "repos": 1000, "members": 5000},
}


def get_plan_limits(plan: str) -> dict:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])


def enforce_analysis_quota(db: Session, tenant: Tenant):
    limits = get_plan_limits(tenant.plan)
    daily_limit = limits["analyses_per_day"]

    today = datetime.utcnow().date().isoformat()
    today_count = db.query(PRAnalysis).filter(
        PRAnalysis.tenant_id == tenant.id,
        func.date(PRAnalysis.analyzed_at) == today,
    ).count()

    if today_count >= daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily analysis quota exceeded for plan '{tenant.plan}' ({daily_limit}/day)",
        )

    return {
        "daily_limit": daily_limit,
        "today_count": today_count,
        "remaining": max(0, daily_limit - today_count),
    }
