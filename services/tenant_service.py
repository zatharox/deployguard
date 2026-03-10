from typing import Optional

from sqlalchemy.orm import Session

from config import get_settings
from db.models import Tenant


def get_or_create_default_tenant(db: Session) -> Tenant:
    settings = get_settings()
    tenant = db.query(Tenant).filter(Tenant.slug == settings.default_tenant_slug).first()
    if tenant:
        return tenant

    tenant = Tenant(
        name="Default Tenant",
        slug=settings.default_tenant_slug,
        plan="free",
        status="active",
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def resolve_tenant(db: Session, tenant_slug: Optional[str]) -> Tenant:
    if tenant_slug:
        tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
        if tenant:
            return tenant

    return get_or_create_default_tenant(db)
