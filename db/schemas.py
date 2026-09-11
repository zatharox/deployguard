from datetime import datetime
import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

class RiskSignalSchema(BaseModel):
    """Risk signal response schema"""

    name: str
    score: float
    description: str
    details: Optional[str] = None


class RiskAnalysisResponse(BaseModel):
    """Risk analysis result response"""

    risk_score: float
    risk_level: str
    signals: List[RiskSignalSchema]
    recommendations: List[str]


class FileImpactSchema(BaseModel):
    """Per-file structural and historical impact."""

    file: str
    component: Optional[str] = None
    critical_area: Optional[str] = None
    change_count: int = 0
    failure_count: int = 0
    failure_rate: float = 0.0
    structural_impact: str = "low"


class DeploymentDecisionSchema(BaseModel):
    """Deployment/release policy decision."""

    status: str
    label: str
    reason: str
    blocking: bool
    policy_version: str


class PRAnalysisSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pr_id: int
    repository_id: Optional[str] = None

    risk_score: float
    risk_level: str

    pr_title: Optional[str] = None
    pr_author: Optional[str] = None

    files_changed: Optional[int] = None
    analyzed_at: Optional[datetime] = None

    signals: List[RiskSignalSchema] = []
    recommendations: List[str] = []

    change_graph: Optional[Dict[str, Any]] = None

    deployment_decision: Optional[DeploymentDecisionSchema] = None

    @field_validator("signals", mode="before")
    @classmethod
    def parse_signals(cls, value):
        if value is None:
            return []

        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else []
            except (TypeError, ValueError):
                return []

        return value

    @field_validator("recommendations", mode="before")
    @classmethod
    def parse_recommendations(cls, value):
        if value is None:
            return []

        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else []
            except (TypeError, ValueError):
                return []

        return value

    @field_validator("change_graph", mode="before")
    @classmethod
    def parse_change_graph(cls, value):
        if value is None:
            return None

        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, dict) else None
            except (TypeError, ValueError):
                return None

        return value

    @model_validator(mode="after")
    def populate_deployment_decision(self):
        from engine.deployment_policy import DeploymentPolicy

        decision = DeploymentPolicy().evaluate(
            risk_level=self.risk_level,
            risk_score=self.risk_score,
            change_graph=self.change_graph or {},
        )

        self.deployment_decision = DeploymentDecisionSchema(
            **decision.to_dict()
        )

        return self

class FileHistorySchema(BaseModel):
    """File history schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    file_path: str
    change_count: int
    failure_count: int
    failure_rate: float
    last_modified: datetime


class WebhookPayload(BaseModel):
    """Azure DevOps webhook payload."""

    subscriptionId: str
    notificationId: int
    id: str
    eventType: str
    resource: dict

    model_config = ConfigDict(extra="allow")