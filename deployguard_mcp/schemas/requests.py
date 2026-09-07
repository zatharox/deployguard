from pydantic import BaseModel, Field


class AnalyzePRRequest(BaseModel):
    repository_id: str = Field(..., min_length=1)
    pr_id: int = Field(..., gt=0)


class RiskScoreRequest(BaseModel):
    analysis_id: int = Field(..., gt=0)


class HistoricalRiskRequest(BaseModel):
    repository_id: str = Field(..., min_length=1)
    paths: list[str] = Field(..., min_length=1)
