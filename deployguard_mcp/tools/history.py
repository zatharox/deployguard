from __future__ import annotations

from typing import Any

from db.database import SessionLocal
from db.models import FileHistory


def get_historical_risk(
    repository_id: str,
    paths: list[str],
    tenant_id: int | None = None,
) -> dict[str, Any]:
    """
    Retrieve historical change/failure information
    for repository files.
    """

    if not paths:
        return {
            "repository_id": repository_id,
            "paths": [],
            "file_count": 0,
            "changes": 0,
            "failed_changes": 0,
            "historical_failure_rate": 0.0,
        }

    db = SessionLocal()

    try:
        query = db.query(FileHistory).filter(
            FileHistory.file_path.in_(paths)
        )

        if tenant_id is not None:
            query = query.filter(
                FileHistory.tenant_id == tenant_id
            )

        file_history = query.all()

        changes = sum(
            item.change_count or 0
            for item in file_history
        )

        failed_changes = sum(
            item.failure_count or 0
            for item in file_history
        )

        failure_rate = (
            failed_changes / changes
            if changes > 0
            else 0.0
        )

        return {
            "repository_id": repository_id,
            "paths": paths,
            "file_count": len(file_history),
            "changes": changes,
            "failed_changes": failed_changes,
            "historical_failure_rate": round(
                failure_rate,
                4,
            ),
        }

    finally:
        db.close()
