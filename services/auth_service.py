from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import secrets

from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from config import get_settings
from db.database import get_db
from db.models import Membership, Tenant, TenantApiKey, User
from services.tenant_service import resolve_tenant

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: Optional[str]) -> bool:
    if not password_hash:
        return False
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(user_id: int, tenant_slug: str, role: str, expires_minutes: int = 60) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {
        "sub": str(user_id),
        "tenant": tenant_slug,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")


async def get_current_user(
    authorization: str = Header(default="", alias="Authorization"),
    db: Session = Depends(get_db),
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing subject")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_roles(allowed_roles: list[str]):
    async def _dependency(
        user: User = Depends(get_current_user),
        x_tenant_slug: str | None = Header(default=None, alias="X-Tenant-Slug"),
        db: Session = Depends(get_db),
    ):
        tenant: Tenant = resolve_tenant(db, x_tenant_slug)
        membership = db.query(Membership).filter(
            Membership.user_id == user.id,
            Membership.tenant_id == tenant.id,
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="No tenant membership")
        if membership.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return {"user": user, "tenant": tenant, "membership": membership}

    return _dependency


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str]:
    raw_key = f"dg_{secrets.token_urlsafe(32)}"
    return raw_key, hash_api_key(raw_key)


async def require_api_key(
    x_api_key: str = Header(default="", alias="X-API-Key"),
    x_tenant_slug: str | None = Header(default=None, alias="X-Tenant-Slug"),
    db: Session = Depends(get_db),
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key")

    tenant: Tenant = resolve_tenant(db, x_tenant_slug)
    key_hash = hash_api_key(x_api_key)
    api_key = db.query(TenantApiKey).filter(
        TenantApiKey.key_hash == key_hash,
        TenantApiKey.tenant_id == tenant.id,
        TenantApiKey.is_active == 1,
    ).first()
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()

    return {"tenant": tenant, "api_key": api_key}
