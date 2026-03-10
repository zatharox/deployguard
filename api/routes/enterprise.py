from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import structlog

from db.database import get_db
from db.models import Membership, PRAnalysis, Tenant, TenantApiKey
from services.auth_service import generate_api_key, require_roles
from services.metering_service import usage_summary_for_today
from services.plan_service import get_plan_limits
from services.tenant_service import get_or_create_default_tenant

router = APIRouter()
logger = structlog.get_logger()


class TenantCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=100)
    plan: str = Field(default="startup")


class ApiKeyCreateRequest(BaseModel):
    label: str = Field(min_length=2, max_length=100)


@router.get("/tenants", summary="🏢 List Tenants")
async def list_tenants(
    auth=Depends(require_roles(["owner", "admin", "manager", "reviewer", "viewer"])),
    db: Session = Depends(get_db),
):
    get_or_create_default_tenant(db)
    memberships = db.query(Membership).filter(Membership.user_id == auth["user"].id).all()
    tenant_ids = [m.tenant_id for m in memberships]
    tenants = db.query(Tenant).filter(Tenant.id.in_(tenant_ids)).order_by(Tenant.created_at.desc()).all()
    logger.info("enterprise_tenants_listed", user_id=auth["user"].id, count=len(tenants))
    return {
        "count": len(tenants),
        "tenants": [
            {
                "id": t.id,
                "name": t.name,
                "slug": t.slug,
                "plan": t.plan,
                "status": t.status,
            }
            for t in tenants
        ],
    }


@router.post("/tenants", summary="➕ Create Tenant")
async def create_tenant(payload: TenantCreateRequest, db: Session = Depends(get_db)):
    logger.info("enterprise_tenant_create_attempt", slug=payload.slug, plan=payload.plan)
    existing = db.query(Tenant).filter(Tenant.slug == payload.slug).first()
    if existing:
        logger.warning("enterprise_tenant_create_conflict", slug=payload.slug)
        raise HTTPException(status_code=409, detail="Tenant slug already exists")

    tenant = Tenant(
        name=payload.name,
        slug=payload.slug,
        plan=payload.plan,
        status="active",
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    logger.info("enterprise_tenant_created", tenant_id=tenant.id, slug=tenant.slug, plan=tenant.plan)

    return {
        "status": "success",
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "plan": tenant.plan,
            "status": tenant.status,
        },
    }


@router.get("/usage", summary="📊 Tenant Usage")
async def get_tenant_usage(
    x_tenant_slug: str | None = Header(default=None, alias="X-Tenant-Slug"),
    auth=Depends(require_roles(["owner", "admin", "manager", "reviewer", "viewer"])),
    db: Session = Depends(get_db),
):
    tenant = auth["tenant"]
    if x_tenant_slug and tenant.slug != x_tenant_slug:
        raise HTTPException(status_code=403, detail="Tenant header mismatch")

    limits = get_plan_limits(tenant.plan)
    today_count = db.query(PRAnalysis).filter(
        PRAnalysis.tenant_id == tenant.id,
        func.date(PRAnalysis.analyzed_at) == func.date(func.now()),
    ).count()

    metering = usage_summary_for_today(db, tenant.id)
    logger.info("enterprise_usage_viewed", tenant_slug=tenant.slug, plan=tenant.plan)

    return {
        "tenant": tenant.slug,
        "plan": tenant.plan,
        "limits": limits,
        "today": {
            "analyses": today_count,
            "remaining": max(0, limits["analyses_per_day"] - today_count),
            "metering": metering,
        },
    }


@router.get("/api-keys", summary="🔑 List API Keys")
async def list_api_keys(
    auth=Depends(require_roles(["owner", "admin"])),
    db: Session = Depends(get_db),
):
    tenant = auth["tenant"]
    keys = db.query(TenantApiKey).filter(TenantApiKey.tenant_id == tenant.id).order_by(TenantApiKey.created_at.desc()).all()
    logger.info("enterprise_api_keys_listed", tenant_slug=tenant.slug, count=len(keys))
    return {
        "tenant": tenant.slug,
        "count": len(keys),
        "api_keys": [
            {
                "id": k.id,
                "label": k.label,
                "is_active": bool(k.is_active),
                "created_at": k.created_at,
                "last_used_at": k.last_used_at,
            }
            for k in keys
        ],
    }


@router.post("/api-keys", summary="➕ Create API Key")
async def create_api_key(
    payload: ApiKeyCreateRequest,
    auth=Depends(require_roles(["owner", "admin"])),
    db: Session = Depends(get_db),
):
    tenant = auth["tenant"]
    raw_key, key_hash = generate_api_key()
    key = TenantApiKey(
        tenant_id=tenant.id,
        key_hash=key_hash,
        label=payload.label,
        is_active=1,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    logger.info("enterprise_api_key_created", tenant_slug=tenant.slug, key_id=key.id, label=key.label)

    return {
        "status": "success",
        "tenant": tenant.slug,
        "api_key": {
            "id": key.id,
            "label": key.label,
            "created_at": key.created_at,
        },
        "secret": raw_key,
        "note": "Store this secret now. It will not be shown again.",
    }


@router.post("/api-keys/{key_id}/revoke", summary="🛑 Revoke API Key")
async def revoke_api_key(
    key_id: int,
    auth=Depends(require_roles(["owner", "admin"])),
    db: Session = Depends(get_db),
):
    tenant = auth["tenant"]
    key = db.query(TenantApiKey).filter(
        TenantApiKey.id == key_id,
        TenantApiKey.tenant_id == tenant.id,
    ).first()
    if not key:
        logger.warning("enterprise_api_key_revoke_missing", tenant_slug=tenant.slug, key_id=key_id)
        raise HTTPException(status_code=404, detail="API key not found")

    key.is_active = 0
    db.commit()
    logger.info("enterprise_api_key_revoked", tenant_slug=tenant.slug, key_id=key.id)
    return {"status": "success", "message": "API key revoked"}
