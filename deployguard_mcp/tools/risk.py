from __future__ import annotations

import json
from typing import Any

from db.database import SessionLocal
from db.models import PRAnalysis


def get_risk_score(
    analysis_id: int,
    tenant_id: int | None = None,
) -> dict[str, Any]:
    """
    Retrieve a previously stored risk analysis.
    """

    db = SessionLocal()

    try:
        query = db.query(PRAnalysis).filter(PRAnalysis.id == analysis_id)

        if tenant_id is not None:
            query = query.filter(PRAnalysis.tenant_id == tenant_id)

        analysis = query.first()

        if analysis is None:
            return {
                "found": False,
                "analysis_id": analysis_id,
            }

        return {
            "found": True,
            "analysis_id": analysis.id,
            "repository_id": analysis.repository_id,
            "pr_id": analysis.pr_id,
            "risk_score": analysis.risk_score,
            "risk_level": analysis.risk_level,
            "analyzed_at": (
                analysis.analyzed_at.isoformat() if analysis.analyzed_at else None
            ),
        }

    finally:
        db.close()


def get_risk_explanation(
    analysis_id: int,
    tenant_id: int | None = None,
) -> dict[str, Any]:
    """
    Return the evidence behind a risk analysis.
    """

    db = SessionLocal()

    try:
        query = db.query(PRAnalysis).filter(PRAnalysis.id == analysis_id)

        if tenant_id is not None:
            query = query.filter(PRAnalysis.tenant_id == tenant_id)

        analysis = query.first()

        if analysis is None:
            return {
                "found": False,
                "analysis_id": analysis_id,
            }

        try:
            signals = json.loads(analysis.signals or "[]")
        except json.JSONDecodeError:
            signals = []

        try:
            recommendations = json.loads(analysis.recommendations or "[]")
        except json.JSONDecodeError:
            recommendations = []

        return {
            "found": True,
            "analysis_id": analysis.id,
            "repository_id": analysis.repository_id,
            "pr_id": analysis.pr_id,
            "risk_score": analysis.risk_score,
            "risk_level": analysis.risk_level,
            "signals": signals,
            "recommendations": recommendations,
        }

    finally:
        db.close()
