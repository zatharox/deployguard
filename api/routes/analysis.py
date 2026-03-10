from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime
import json
import structlog

from db.database import get_db
from db.schemas import PRAnalysisSchema, FileHistorySchema
from db.models import PRAnalysis, FileHistory, PipelineHistory
from services.analysis_service import AnalysisService
from services.auth_service import require_api_key, require_roles
from services.metering_service import record_usage_event
from services.plan_service import enforce_analysis_quota
from engine.risk_analyzer import RiskEngine

router = APIRouter()
logger = structlog.get_logger()


@router.get("/demo/scenarios",
           summary="🧪 List Demo Scenarios",
           description="List built-in scenarios to test all major risk situations")
async def list_demo_scenarios():
    return {
        "scenarios": {
            "low": "Small PR, no critical paths, healthy pipelines",
            "medium": "Moderate PR with one unstable file and moderate pipeline failures",
            "high": "Large PR touching critical paths with high pipeline failures",
            "critical": "Very large PR with multiple unstable files and severe pipeline instability"
        }
    }


@router.post("/demo/run/{scenario}",
            summary="🎬 Run Demo Scenario",
            description="Generate deterministic test data and run full risk analysis for a given scenario")
async def run_demo_scenario(
    scenario: str,
    reset: bool = True,
    auth=Depends(require_roles(["owner", "admin", "manager", "reviewer"])),
    db: Session = Depends(get_db)
):
    tenant = auth["tenant"]
    logger.info("analysis_demo_started", tenant_slug=tenant.slug, scenario=scenario, reset=reset)
    enforce_analysis_quota(db, tenant)
    scenario = scenario.lower().strip()
    if scenario not in {"low", "medium", "high", "critical"}:
        raise HTTPException(status_code=400, detail="scenario must be one of: low, medium, high, critical")

    if reset:
        db.query(PRAnalysis).filter(PRAnalysis.tenant_id == tenant.id).delete()
        db.query(FileHistory).filter(FileHistory.tenant_id == tenant.id).delete()
        db.query(PipelineHistory).filter(PipelineHistory.tenant_id == tenant.id).delete()
        db.commit()

    if scenario == "low":
        files = ["/docs/readme.md", "/frontend/button.tsx"]
        file_histories = [
            FileHistory(tenant_id=tenant.id, file_path="/frontend/button.tsx", change_count=20, failure_count=1),
            FileHistory(tenant_id=tenant.id, file_path="/docs/readme.md", change_count=10, failure_count=0),
        ]
        failures = 3
        total_runs = 100
    elif scenario == "medium":
        files = [
            "/core/cache.py",
            "/api/users.py",
            "/auth/session.py",
            "/frontend/profile.tsx",
            "/services/notification.py",
            "/utils/mapper.py",
        ]
        file_histories = [
            FileHistory(tenant_id=tenant.id, file_path="/core/cache.py", change_count=25, failure_count=5),
            FileHistory(tenant_id=tenant.id, file_path="/auth/session.py", change_count=18, failure_count=2),
        ]
        failures = 14
        total_runs = 100
    elif scenario == "high":
        files = [
            "/auth/auth_service.py",
            "/payment/payment_api.py",
            "/core/transaction_manager.py",
            "/database/repository.py",
            "/security/token_validator.py",
            "/api/gateway.py",
            "/services/billing.py",
            "/services/refunds.py",
            "/kernel/runtime.py",
            "/db/connection_pool.py",
            "/core/order_orchestrator.py",
            "/auth/mfa.py",
        ]
        file_histories = [
            FileHistory(tenant_id=tenant.id, file_path="/auth/auth_service.py", change_count=40, failure_count=14),
            FileHistory(tenant_id=tenant.id, file_path="/payment/payment_api.py", change_count=35, failure_count=8),
            FileHistory(tenant_id=tenant.id, file_path="/database/repository.py", change_count=32, failure_count=9),
        ]
        failures = 24
        total_runs = 100
    else:  # critical
        files = [
            "/auth/auth_service.py",
            "/payment/payment_api.py",
            "/core/transaction_manager.py",
            "/database/repository.py",
            "/security/token_validator.py",
            "/api/gateway.py",
            "/services/billing.py",
            "/services/refunds.py",
            "/kernel/runtime.py",
            "/db/connection_pool.py",
            "/core/order_orchestrator.py",
            "/auth/mfa.py",
            "/database/migrations/critical_patch.sql",
            "/core/failover.py",
            "/payment/settlement.py",
            "/auth/rbac.py",
        ]
        file_histories = [
            FileHistory(tenant_id=tenant.id, file_path="/auth/auth_service.py", change_count=40, failure_count=16),
            FileHistory(tenant_id=tenant.id, file_path="/payment/payment_api.py", change_count=35, failure_count=10),
            FileHistory(tenant_id=tenant.id, file_path="/database/repository.py", change_count=32, failure_count=12),
            FileHistory(tenant_id=tenant.id, file_path="/core/transaction_manager.py", change_count=30, failure_count=11),
        ]
        failures = 38
        total_runs = 120

    for fh in file_histories:
        existing = db.query(FileHistory).filter(
            FileHistory.file_path == fh.file_path,
            FileHistory.tenant_id == tenant.id,
        ).first()
        if existing:
            existing.change_count = fh.change_count
            existing.failure_count = fh.failure_count
        else:
            db.add(fh)

    now = datetime.utcnow()
    max_run_id = db.query(func.max(PipelineHistory.run_id)).filter(PipelineHistory.tenant_id == tenant.id).scalar() or 500000
    for i in range(total_runs):
        status = "failed" if i < failures else "succeeded"
        db.add(
            PipelineHistory(
                tenant_id=tenant.id,
                pipeline_id=1,
                pipeline_name="demo-pipeline",
                run_id=max_run_id + i + 1,
                status=status,
                result=status,
                commit_id=f"demo-{i}",
                branch="refs/heads/main",
                started_at=now,
                finished_at=now,
            )
        )
    db.commit()

    pr_data = {
        "pullRequestId": 999,
        "title": f"Demo {scenario.capitalize()} Risk PR",
        "createdBy": {"displayName": "Demo User"},
    }
    changes_data = {"changeEntries": [{"item": {"path": p}} for p in files]}

    risk_engine = RiskEngine()
    analysis_service = AnalysisService(db, tenant_id=tenant.id)
    result = await risk_engine.analyze_pr(
        pr_data=pr_data,
        changes_data=changes_data,
        file_history=analysis_service._get_file_history_dict(),
        pipeline_stats={"total_runs": total_runs, "failed_runs": failures},
    )

    record = PRAnalysis(
        tenant_id=tenant.id,
        pr_id=pr_data["pullRequestId"],
        repository_id="demo-repo",
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        signals=json.dumps([s.__dict__ for s in result.signals]),
        recommendations=json.dumps(result.recommendations),
        pr_title=pr_data["title"],
        pr_author=pr_data["createdBy"]["displayName"],
        files_changed=len(files),
        lines_changed=len(files) * 50,
    )
    db.add(record)
    db.commit()
    record_usage_event(
        db,
        tenant_id=tenant.id,
        event_type="analysis.demo",
        metadata={"scenario": scenario, "risk_level": result.risk_level},
    )
    logger.info("analysis_demo_completed", tenant_slug=tenant.slug, scenario=scenario, risk_score=result.risk_score, risk_level=result.risk_level)

    return {
        "status": "success",
        "tenant": tenant.slug,
        "scenario": scenario,
        "reset": reset,
        "analysis": result.to_dict(),
        "comment_preview": risk_engine.format_pr_comment(result),
    }


@router.post("/demo/run-all",
            summary="🚀 Run All Demo Scenarios",
            description="Run low, medium, high, critical scenarios in sequence for production-like smoke simulation")
async def run_all_demo_scenarios(
    reset_first: bool = True,
    auth=Depends(require_roles(["owner", "admin", "manager", "reviewer"])),
    db: Session = Depends(get_db)
):
    logger.info("analysis_demo_batch_started", tenant_slug=auth["tenant"].slug, reset_first=reset_first)
    results = []
    for idx, scenario in enumerate(["low", "medium", "high", "critical"]):
        result = await run_demo_scenario(
            scenario=scenario,
            reset=reset_first and idx == 0,
            auth=auth,
            db=db,
        )
        results.append({
            "scenario": scenario,
            "risk_score": result["analysis"]["risk_score"],
            "risk_level": result["analysis"]["risk_level"],
        })

    logger.info("analysis_demo_batch_completed", tenant_slug=auth["tenant"].slug, total=len(results))
    return {
        "status": "success",
        "results": results,
    }


@router.post("/analyze/{repository_id}/{pr_id}", 
            summary="🔍 Analyze Pull Request",
            description="Manually trigger comprehensive risk analysis for a specific Pull Request")
async def analyze_pr_manual(
    repository_id: str,
    pr_id: int,
    auth=Depends(require_roles(["owner", "admin", "manager", "reviewer"])),
    db: Session = Depends(get_db)
):
    """
    Manually trigger PR analysis
    
    **Use this endpoint to:**
    - Test the risk analysis engine
    - Re-analyze existing PRs
    - Debug analysis results
    
    **Returns:** Complete risk analysis with score, signals, and recommendations
    """
    try:
        tenant = auth["tenant"]
        logger.info("analysis_manual_started", tenant_slug=tenant.slug, repository_id=repository_id, pr_id=pr_id)
        enforce_analysis_quota(db, tenant)
        analysis_service = AnalysisService(db, tenant_id=tenant.id)
        result = await analysis_service.analyze_and_comment_pr(
            repository_id=repository_id,
            pr_id=pr_id
        )
        record_usage_event(
            db,
            tenant_id=tenant.id,
            event_type="analysis.manual",
            metadata={"repository_id": repository_id, "pr_id": pr_id, "risk_level": result.risk_level},
        )
        
        return {
            "status": "success",
            "tenant": tenant.slug,
            "analysis": result.to_dict()
        }
    
    except Exception as e:
        logger.error("analysis_manual_failed", repository_id=repository_id, pr_id=pr_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{pr_id}", 
           response_model=List[PRAnalysisSchema],
           summary="📜 Get PR Analysis History",
           description="Retrieve all historical risk analyses for a specific Pull Request")
async def get_pr_analysis_history(
    pr_id: int,
    auth=Depends(require_roles(["owner", "admin", "manager", "reviewer", "viewer"])),
    db: Session = Depends(get_db)
):
    """
    Get analysis history for a specific PR
    
    **Useful for:**
    - Tracking how risk scores change over time
    - Comparing multiple analyses
    - Audit trails
    """
    
    tenant = auth["tenant"]
    analyses = db.query(PRAnalysis).filter(
        PRAnalysis.pr_id == pr_id,
        PRAnalysis.tenant_id == tenant.id,
    ).order_by(PRAnalysis.analyzed_at.desc()).all()
    
    return analyses


@router.get("/files/unstable", 
           response_model=List[FileHistorySchema],
           summary="⚠️ Get Unstable Files",
           description="List files with high historical failure rates - your most risky files")
async def get_unstable_files(
    min_failure_rate: float = 0.15,
    limit: int = 50,
    auth=Depends(require_roles(["owner", "admin", "manager", "reviewer", "viewer"])),
    db: Session = Depends(get_db)
):
    """
    Get list of unstable files with high failure rates
    
    **Parameters:**
    - **min_failure_rate**: Minimum failure rate threshold (default 0.15 = 15%)
    - **limit**: Maximum number of results (default 50)
    
    **Use this to:**
    - Identify problem areas in your codebase
    - Prioritize refactoring efforts
    - Set up targeted alerts
    """
    
    tenant = auth["tenant"]
    files = db.query(FileHistory).filter(
        FileHistory.change_count > 0,
        FileHistory.tenant_id == tenant.id,
    ).all()
    
    # Filter by failure rate (calculated property)
    unstable_files = [
        f for f in files 
        if f.failure_rate >= min_failure_rate
    ]
    
    # Sort by failure rate descending
    unstable_files.sort(key=lambda x: x.failure_rate, reverse=True)
    
    return unstable_files[:limit]


@router.get("/stats/summary",
           summary="📈 Get Summary Statistics",
           description="Get overall system statistics and metrics")
async def get_summary_stats(
    auth=Depends(require_roles(["owner", "admin", "manager", "reviewer", "viewer"])),
    db: Session = Depends(get_db)
):
    """
    Get summary statistics
    
    **Returns:**
    - Total analyses performed
    - High-risk PRs detected
    - Total files tracked
    - Unstable files count
    
    **Perfect for:** Dashboards, monitoring, and reporting
    """
    
    tenant = auth["tenant"]
    total_analyses = db.query(PRAnalysis).count()
    total_analyses = db.query(PRAnalysis).filter(PRAnalysis.tenant_id == tenant.id).count()

    high_risk_count = db.query(PRAnalysis).filter(
        PRAnalysis.risk_level == "high",
        PRAnalysis.tenant_id == tenant.id,
    ).count()

    total_files = db.query(FileHistory).filter(FileHistory.tenant_id == tenant.id).count()

    unstable_files = db.query(FileHistory).filter(
        FileHistory.change_count > 0,
        FileHistory.tenant_id == tenant.id,
    ).all()
    
    unstable_count = sum(1 for f in unstable_files if f.failure_rate >= 0.15)
    
    return {
        "tenant": tenant.slug,
        "total_analyses": total_analyses,
        "high_risk_prs": high_risk_count,
        "total_tracked_files": total_files,
        "unstable_files": unstable_count
    }


@router.post("/agent/demo/run/{scenario}",
            summary="🤖 Agent Demo Run (API Key)",
            description="Run demo scenario using X-API-Key for CI/CD agents")
async def run_demo_scenario_agent(
    scenario: str,
    reset: bool = False,
    machine=Depends(require_api_key),
    db: Session = Depends(get_db),
):
    tenant = machine["tenant"]
    api_key = machine["api_key"]
    logger.info("analysis_agent_started", tenant_slug=tenant.slug, api_key_id=api_key.id, scenario=scenario, reset=reset)
    enforce_analysis_quota(db, tenant)

    result = await run_demo_scenario(
        scenario=scenario,
        reset=reset,
        auth={"tenant": tenant, "membership": {"role": "service"}, "user": None},
        db=db,
    )
    record_usage_event(
        db,
        tenant_id=tenant.id,
        api_key_id=api_key.id,
        event_type="analysis.agent",
        metadata={"scenario": scenario},
    )
    logger.info("analysis_agent_completed", tenant_slug=tenant.slug, api_key_id=api_key.id, scenario=scenario)
    return result
