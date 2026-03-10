from fastapi import APIRouter
from config import get_settings
from integrations.azure_devops import AzureDevOpsClient

router = APIRouter()


@router.get("/health", summary="🏥 Health Check", description="Check if the DeployGuard API is healthy and operational")
async def health_check():
    """Health check endpoint - Returns system status"""
    return {
        "status": "healthy",
        "service": "DeployGuard",
        "version": "1.0.0"
    }


@router.get(
    "/health/azure-devops",
    summary="🔌 Azure DevOps Connectivity",
    description="Validate Azure DevOps auth and Pipeline API connectivity"
)
async def azure_devops_health_check():
    """Checks whether DeployGuard can read Azure DevOps pipeline runs."""
    settings = get_settings()
    client = AzureDevOpsClient()

    try:
        runs = await client.get_pipeline_runs(top=1)
        return {
            "status": "connected",
            "organization": settings.azure_devops_org,
            "project": settings.azure_devops_project,
            "pipeline_api": "ok",
            "sample_runs_count": len(runs),
        }
    except Exception as exc:
        return {
            "status": "failed",
            "organization": settings.azure_devops_org,
            "project": settings.azure_devops_project,
            "pipeline_api": "error",
            "message": str(exc),
        }


@router.get("/", summary="🏠 API Info", description="Get basic API information and links")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "DeployGuard API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/v1/health"
    }
