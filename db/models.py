from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from db.database import Base


class Tenant(Base):
    """Organization/workspace owning repositories and analyses."""
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    plan = Column(String(50), nullable=False, default="free")
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    """Enterprise user account."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(200))
    password_hash = Column(String(255), nullable=True)
    auth_provider = Column(String(50), nullable=False, default="local")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Membership(Base):
    """User membership and role inside a tenant."""
    __tablename__ = "memberships"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(30), nullable=False, default="viewer")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_membership_tenant_user"),
    )


class Repository(Base):
    """Tenant-managed repository registration."""
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    external_repo_id = Column(String(120), nullable=False)
    name = Column(String(200), nullable=False)
    provider = Column(String(50), nullable=False, default="azure-devops")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "external_repo_id", name="uq_repo_tenant_external"),
    )


class TenantApiKey(Base):
    """API key mapping for tenant-scoped integrations."""
    __tablename__ = "tenant_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    key_hash = Column(String(255), nullable=False, unique=True, index=True)
    label = Column(String(100), nullable=False)
    is_active = Column(Integer, nullable=False, default=1)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UsageEvent(Base):
    """Billing/metering events for enterprise plans."""
    __tablename__ = "usage_events"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    api_key_id = Column(Integer, ForeignKey("tenant_api_keys.id"), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    event_metadata = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_usage_tenant_event', 'tenant_id', 'event_type'),
        Index('idx_usage_created', 'created_at'),
    )


class FileHistory(Base):
    """Track file modification and failure history"""
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    file_path = Column(String(500), nullable=False, index=True)
    change_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    last_modified = Column(DateTime(timezone=True), server_default=func.now())
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate"""
        if self.change_count == 0:
            return 0.0
        return self.failure_count / self.change_count
    
    __table_args__ = (
        Index('idx_file_path', 'file_path'),
        Index('idx_tenant_file_path', 'tenant_id', 'file_path'),
        UniqueConstraint('tenant_id', 'file_path', name='uq_files_tenant_path'),
    )


class PRAnalysis(Base):
    """Store PR risk analysis results"""
    __tablename__ = "pr_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    pr_id = Column(Integer, nullable=False, index=True)
    repository_id = Column(String(100), nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)  # low, medium, high
    signals = Column(Text)  # JSON string of signals
    recommendations = Column(Text)  # JSON string of recommendations
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # PR metadata
    pr_title = Column(String(500))
    pr_author = Column(String(100))
    files_changed = Column(Integer)
    lines_changed = Column(Integer)
    
    __table_args__ = (
        Index('idx_pr_repo', 'pr_id', 'repository_id'),
        Index('idx_analyzed_at', 'analyzed_at'),
        Index('idx_tenant_risk', 'tenant_id', 'risk_level'),
    )


class PipelineHistory(Base):
    """Track pipeline run history for failure rate analysis"""
    __tablename__ = "pipeline_history"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    pipeline_id = Column(Integer, nullable=False, index=True)
    pipeline_name = Column(String(200))
    run_id = Column(Integer, nullable=False, unique=True)
    status = Column(String(50), nullable=False)  # succeeded, failed, canceled
    result = Column(String(50))  # succeeded, failed, canceled
    commit_id = Column(String(50))
    branch = Column(String(200))
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_pipeline_id', 'pipeline_id'),
        Index('idx_status', 'status'),
        Index('idx_commit', 'commit_id'),
        Index('idx_tenant_pipeline', 'tenant_id', 'pipeline_id'),
    )


class WebhookEvent(Base):
    """Log incoming webhook events for debugging"""
    __tablename__ = "webhook_events"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    repository_id = Column(String(100))
    pr_id = Column(Integer)
    payload = Column(Text)  # Full JSON payload
    processed = Column(Integer, default=0)  # 0=pending, 1=processed, -1=error
    error_message = Column(Text)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        Index('idx_event_type', 'event_type'),
        Index('idx_processed', 'processed'),
        Index('idx_tenant_processed', 'tenant_id', 'processed'),
    )
