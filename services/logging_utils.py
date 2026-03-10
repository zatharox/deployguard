import uuid
from typing import Optional

import structlog


def mask_email(email: Optional[str]) -> str:
    if not email or "@" not in email:
        return "<unknown>"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = "*" * len(local)
    else:
        masked_local = local[:2] + "***"
    return f"{masked_local}@{domain}"


def get_request_id(incoming_request_id: Optional[str] = None) -> str:
    return incoming_request_id.strip() if incoming_request_id else str(uuid.uuid4())


def bind_log_context(**kwargs):
    clean = {k: v for k, v in kwargs.items() if v is not None}
    structlog.contextvars.bind_contextvars(**clean)


def clear_log_context():
    structlog.contextvars.clear_contextvars()
