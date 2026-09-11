from fastapi import APIRouter
from fastapi.responses import JSONResponse

from sqlalchemy import text

import redis

from services.metrics import MetricsService
from config import get_settings
from db.database import SessionLocal
from integrations.azure_devops import AzureDevOpsClient
from services.celery_app import celery_app


router = APIRouter()


# ---------------------------------------------------------------------
# Liveness
# ---------------------------------------------------------------------

@router.get(
    "/health",
    summary="🏥 Health Check",
    description="Check whether the DeployGuard API process is alive.",
)
async def health_check():
    """
    Liveness check.

    This endpoint intentionally does not check external dependencies.
    A 200 response means the API process itself is running.
    """

    return {
        "status": "healthy",
        "service": "DeployGuard",
        "version": "1.0.0",
    }


# ---------------------------------------------------------------------
# Readiness
# ---------------------------------------------------------------------

@router.get(
    "/readiness",
    summary="🚦 Readiness Check",
    description=(
        "Check whether DeployGuard is ready to process "
        "requests and asynchronous analysis jobs."
    ),
)
async def readiness_check():
    """
    Readiness check.

    Verifies:
    - PostgreSQL
    - Redis
    - Celery worker

    Azure DevOps is intentionally not included here because it is an
    external integration and may be unavailable without making the
    DeployGuard service itself unhealthy.

    Returns HTTP 200 when all required runtime dependencies are healthy.
    Returns HTTP 503 when one or more required dependencies are unhealthy.
    """

    checks = {}

    # -------------------------------------------------------------
    # Database
    # -------------------------------------------------------------

    try:
        db = SessionLocal()

        try:
            db.execute(text("SELECT 1"))
            checks["database"] = {
                "status": "ok",
            }
        finally:
            db.close()

    except Exception as exc:
        checks["database"] = {
            "status": "error",
            "message": str(exc),
        }

    # -------------------------------------------------------------
    # Redis
    # -------------------------------------------------------------

    try:
        settings = get_settings()

        redis_client = redis.Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
        )

        redis_client.ping()

        checks["redis"] = {
            "status": "ok",
        }

        redis_client.close()

    except Exception as exc:
        checks["redis"] = {
            "status": "error",
            "message": str(exc),
        }

    # -------------------------------------------------------------
    # Celery worker
    # -------------------------------------------------------------

    try:
        inspector = celery_app.control.inspect(
            timeout=1.0,
        )

        workers = inspector.ping() or {}

        if workers:
            checks["celery"] = {
                "status": "ok",
                "workers": list(workers.keys()),
            }
        else:
            checks["celery"] = {
                "status": "error",
                "message": "No active Celery workers detected",
            }

    except Exception as exc:
        checks["celery"] = {
            "status": "error",
            "message": str(exc),
        }

    # -------------------------------------------------------------
    # Overall readiness
    # -------------------------------------------------------------

    failed_checks = [
        name
        for name, result in checks.items()
        if result.get("status") != "ok"
    ]

    overall_status = (
        "ready"
        if not failed_checks
        else "not_ready"
    )

    response = {
        "status": overall_status,
        "service": "DeployGuard",
        "version": "1.0.0",
        "checks": checks,
    }

    if failed_checks:
        response["failed_checks"] = failed_checks

        return JSONResponse(
            status_code=503,
            content=response,
        )

    return response


# ---------------------------------------------------------------------
# Azure DevOps
# ---------------------------------------------------------------------

@router.get(
    "/health/azure-devops",
    summary="🔌 Azure DevOps Connectivity",
    description="Validate Azure DevOps auth and Pipeline API connectivity.",
)
async def azure_devops_health_check():
    """
    Check Azure DevOps connectivity.

    This remains an explicit integration check rather than being part of
    the core readiness check.
    """

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
        return JSONResponse(
            status_code=503,
            content={
                "status": "failed",
                "organization": settings.azure_devops_org,
                "project": settings.azure_devops_project,
                "pipeline_api": "error",
                "message": str(exc),
            },
        )

@router.get(
    "/metrics",
    summary="📊 DeployGuard Metrics",
    description="Return current DeployGuard operational metrics.",
)
async def metrics():
    """
    Return operational metrics collected by DeployGuard.
    """

    metrics_service = MetricsService()

    try:
        return {
            "status": "ok",
            "service": "DeployGuard",
            "version": "1.0.0",
            "metrics": metrics_service.snapshot(),
        }

    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "service": "DeployGuard",
                "message": str(exc),
            },
        )

    
# ---------------------------------------------------------------------
# API Info
# ---------------------------------------------------------------------

@router.get(
    "/",
    summary="🏠 API Info",
    description="Get basic API information and links",
)
async def root():
    """Root endpoint with API information."""

    return {
        "message": "DeployGuard API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/v1/health",
        "readiness": "/api/v1/readiness",
        "azure_devops_health": "/api/v1/health/azure-devops",
    }

