from datetime import datetime
import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


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


class PRAnalysisSchema(BaseModel):
    """PR analysis database schema"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    pr_id: int
    repository_id: str
    risk_score: float
    risk_level: str
    pr_title: Optional[str] = None
    pr_author: Optional[str] = None
    files_changed: Optional[int] = None
    analyzed_at: datetime
    change_graph: Optional[Dict[str, Any]] = None

    @field_validator("change_graph", mode="before")
    @classmethod
    def parse_change_graph(cls, value):
        if value is None or value == "":
            return None

        if isinstance(value, str):
            return json.loads(value)

        if isinstance(value, dict):
            return value

        raise ValueError("Invalid change_graph format")


class FileHistorySchema(BaseModel):
    """File history schema"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    file_path: str
    change_count: int
    failure_count: int
    failure_rate: float
    last_modified: datetime


class WebhookPayload(BaseModel):
    """Azure DevOps webhook payload"""

    subscriptionId: str
    notificationId: int
    id: str
    eventType: str
    resource: dict

    model_config = ConfigDict(extra="allow")
