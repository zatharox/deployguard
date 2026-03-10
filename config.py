from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application configuration"""
    
    # Azure DevOps
    azure_devops_org: str
    azure_devops_pat: str
    azure_devops_project: str
    
    # Database
    database_url: str
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Application
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    secret_key: str
    demo_mode: bool = False
    default_tenant_slug: str = "default"
    
    # Webhook
    webhook_secret: str
    
    # Risk Engine Configuration
    high_risk_threshold: float = 7.0
    medium_risk_threshold: float = 4.0
    max_lines_low_risk: int = 300
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
