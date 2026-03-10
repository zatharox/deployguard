from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


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
    id: int
    pr_id: int
    repository_id: str
    risk_score: float
    risk_level: str
    pr_title: Optional[str]
    pr_author: Optional[str]
    files_changed: Optional[int]
    analyzed_at: datetime
    
    class Config:
        from_attributes = True


class FileHistorySchema(BaseModel):
    """File history schema"""
    id: int
    file_path: str
    change_count: int
    failure_count: int
    failure_rate: float
    last_modified: datetime
    
    class Config:
        from_attributes = True


class WebhookPayload(BaseModel):
    """Azure DevOps webhook payload"""
    subscriptionId: str
    notificationId: int
    id: str
    eventType: str
    resource: dict
    
    class Config:
        extra = "allow"
