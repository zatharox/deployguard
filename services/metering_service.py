import json
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import UsageEvent


def record_usage_event(
    db: Session,
    tenant_id: int,
    event_type: str,
    quantity: int = 1,
    api_key_id: int | None = None,
    metadata: dict | None = None,
):
    event = UsageEvent(
        tenant_id=tenant_id,
        api_key_id=api_key_id,
        event_type=event_type,
        quantity=quantity,
        event_metadata=json.dumps(metadata or {}),
    )
    db.add(event)
    db.commit()


def usage_summary_for_today(db: Session, tenant_id: int) -> dict:
    today = datetime.utcnow().date().isoformat()
    rows = db.query(
        UsageEvent.event_type,
        func.sum(UsageEvent.quantity),
    ).filter(
        UsageEvent.tenant_id == tenant_id,
        func.date(UsageEvent.created_at) == today,
    ).group_by(UsageEvent.event_type).all()

    return {event_type: int(total or 0) for event_type, total in rows}
