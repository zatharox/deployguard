from __future__ import annotations

from typing import Any

from db.database import SessionLocal
from deployguard_mcp.schemas.responses import RiskAnalysisResponse
from services.analysis_service import AnalysisService


async def analyze_pr(
    repository_id: str,
    pr_id: int,
    tenant_id: int | None = None,
) -> dict[str, Any]:
    """
    Analyze a pull request using DeployGuard.
    """

    db = SessionLocal()

    try:
        service = AnalysisService(
            db=db,
            tenant_id=tenant_id,
        )

        result = await service.analyze_pr(
            repository_id=repository_id,
            pr_id=pr_id,
        )

        response = RiskAnalysisResponse(
            analysis_id=result.analysis_id,
            risk_score=result.risk_score,
            risk_level=result.risk_level,
            signals=[
                {
                    "name": signal.name,
                    "score": signal.score,
                    "description": signal.description,
                    "details": signal.details,
                }
                for signal in result.signals
            ],
            recommendations=result.recommendations,
        )

        return response.model_dump()

    finally:
        db.close()
