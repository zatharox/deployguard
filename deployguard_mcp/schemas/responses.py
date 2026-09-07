from __future__ import annotations

from pydantic import BaseModel, Field


class RiskSignalResponse(BaseModel):
    name: str
    score: float
    description: str
    details: str | None = None


class RiskAnalysisResponse(BaseModel):
    analysis_id: int | None = None
    risk_score: float
    risk_level: str
    signals: list[RiskSignalResponse] = Field(
        default_factory=list
    )
    recommendations: list[str] = Field(
        default_factory=list
    )


class RiskScoreResponse(BaseModel):
    found: bool
    analysis_id: int
    repository_id: str | None = None
    pr_id: int | None = None
    risk_score: float | None = None
    risk_level: str | None = None
    analyzed_at: str | None = None


class HistoricalRiskResponse(BaseModel):
    repository_id: str
    paths: list[str]
    file_count: int
    changes: int
    failed_changes: int
    historical_failure_rate: float
