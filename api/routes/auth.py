from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
import structlog

from config import get_settings
from db.database import get_db
from db.models import Membership, User
from services.auth_service import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from services.logging_utils import mask_email
from services.tenant_service import resolve_tenant

router = APIRouter()
logger = structlog.get_logger()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None
    tenant_slug: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: str | None = None


@router.post("/register", summary="🧾 Register User")
async def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    logger.info("auth_register_attempt", email=mask_email(payload.email), tenant_slug=payload.tenant_slug)
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        logger.warning("auth_register_conflict", email=mask_email(payload.email))
        raise HTTPException(status_code=409, detail="Email already registered")

    tenant = resolve_tenant(db, payload.tenant_slug)
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        auth_provider="local",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    membership = Membership(
        tenant_id=tenant.id,
        user_id=user.id,
        role="owner",
    )
    db.add(membership)
    db.commit()

    token = create_access_token(user.id, tenant.slug, membership.role)
    logger.info("auth_register_success", user_id=user.id, tenant_slug=tenant.slug, role=membership.role)
    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "tenant": tenant.slug,
        "role": membership.role,
    }


@router.post("/login", summary="🔐 Login")
async def login(payload: LoginRequest, db: Session = Depends(get_db)):
    logger.info("auth_login_attempt", email=mask_email(payload.email), tenant_slug=payload.tenant_slug)
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        logger.warning("auth_login_failed", email=mask_email(payload.email))
        raise HTTPException(status_code=401, detail="Invalid credentials")

    tenant = resolve_tenant(db, payload.tenant_slug)
    membership = db.query(Membership).filter(
        Membership.user_id == user.id,
        Membership.tenant_id == tenant.id,
    ).first()
    if not membership:
        logger.warning("auth_login_no_membership", user_id=user.id, tenant_slug=tenant.slug)
        raise HTTPException(status_code=403, detail="No membership in tenant")

    token = create_access_token(user.id, tenant.slug, membership.role)
    logger.info("auth_login_success", user_id=user.id, tenant_slug=tenant.slug, role=membership.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "tenant": tenant.slug,
        "role": membership.role,
    }


@router.get("/me", summary="👤 Current User")
async def me(
    user: User = Depends(get_current_user),
    x_tenant_slug: str | None = Header(default=None, alias="X-Tenant-Slug"),
    db: Session = Depends(get_db),
):
    tenant = resolve_tenant(db, x_tenant_slug)
    membership = db.query(Membership).filter(
        Membership.user_id == user.id,
        Membership.tenant_id == tenant.id,
    ).first()

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "auth_provider": user.auth_provider,
        },
        "tenant": tenant.slug,
        "role": membership.role if membership else None,
    }


@router.post("/demo-bootstrap", summary="🧪 Demo Bootstrap Token")
async def demo_bootstrap(db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.demo_mode:
        raise HTTPException(status_code=403, detail="Demo mode is disabled")

    tenant = resolve_tenant(db, settings.default_tenant_slug)
    demo_email = "demo.owner@deployguard.local"

    user = db.query(User).filter(User.email == demo_email).first()
    if not user:
        user = User(
            email=demo_email,
            full_name="Demo Owner",
            password_hash=hash_password("DemoPass123!"),
            auth_provider="local",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    membership = db.query(Membership).filter(
        Membership.user_id == user.id,
        Membership.tenant_id == tenant.id,
    ).first()
    if not membership:
        membership = Membership(
            tenant_id=tenant.id,
            user_id=user.id,
            role="owner",
        )
        db.add(membership)
        db.commit()

    token = create_access_token(user.id, tenant.slug, membership.role)
    logger.info("auth_demo_bootstrap", user_id=user.id, tenant_slug=tenant.slug, role=membership.role)
    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "tenant": tenant.slug,
        "role": membership.role,
    }
