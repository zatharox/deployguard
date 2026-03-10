from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict
import json
import structlog

from db.models import PRAnalysis, FileHistory, PipelineHistory
from engine.risk_analyzer import RiskEngine, RiskAnalysisResult
from integrations.azure_devops import AzureDevOpsClient
from integrations.mock_azure_devops import MockAzureDevOpsClient
from config import get_settings

logger = structlog.get_logger()


class AnalysisService:
    """Service layer for PR analysis orchestration"""
    
    def __init__(self, db: Session, tenant_id: int | None = None):
        self.db = db
        self.tenant_id = tenant_id
        settings = get_settings()
        self.azure_client = MockAzureDevOpsClient() if settings.demo_mode else AzureDevOpsClient()
        self.risk_engine = RiskEngine()
    
    async def analyze_and_comment_pr(
        self,
        repository_id: str,
        pr_id: int
    ) -> RiskAnalysisResult:
        """
        Complete PR analysis workflow:
        1. Fetch PR data from Azure DevOps
        2. Get file history from database
        3. Get pipeline statistics
        4. Run risk analysis
        5. Save results to database
        6. Post comment to PR
        """
        
        logger.info("starting_pr_analysis", pr_id=pr_id, repository_id=repository_id)
        
        # Step 1: Fetch PR data
        pr_data = await self.azure_client.get_pull_request(repository_id, pr_id)
        changes_data = await self.azure_client.get_pr_changes(repository_id, pr_id)
        
        # Step 2: Get file history
        file_history = self._get_file_history_dict()
        
        # Step 3: Get pipeline statistics
        pipeline_stats = await self._get_pipeline_stats()
        
        # Step 4: Run risk analysis
        result = await self.risk_engine.analyze_pr(
            pr_data=pr_data,
            changes_data=changes_data,
            file_history=file_history,
            pipeline_stats=pipeline_stats
        )
        
        # Step 5: Save to database
        self._save_analysis_result(
            pr_data=pr_data,
            repository_id=repository_id,
            changes_data=changes_data,
            result=result
        )
        
        # Step 6: Post comment to PR
        comment_text = self.risk_engine.format_pr_comment(result)
        await self.azure_client.post_pr_comment(
            repository_id=repository_id,
            pr_id=pr_id,
            comment_text=comment_text
        )
        
        logger.info("pr_analysis_completed",
                   pr_id=pr_id,
                   risk_score=result.risk_score,
                   risk_level=result.risk_level)
        
        return result
    
    def _get_file_history_dict(self) -> Dict[str, float]:
        """
        Get file failure rates from database
        
        Returns:
            Dict mapping file_path to failure_rate
        """
        files = self.db.query(FileHistory).filter(
            FileHistory.change_count > 0,
            FileHistory.tenant_id == self.tenant_id if self.tenant_id is not None else True,
        ).all()
        
        return {
            file.file_path: file.failure_rate
            for file in files
        }
    
    async def _get_pipeline_stats(self) -> Dict:
        """
        Calculate pipeline statistics from recent runs
        
        Returns:
            Dict with total_runs and failed_runs
        """
        # Get recent pipeline runs (last 100)
        total_runs_query = self.db.query(PipelineHistory)
        if self.tenant_id is not None:
            total_runs_query = total_runs_query.filter(PipelineHistory.tenant_id == self.tenant_id)
        total_runs = total_runs_query.count()
        
        failed_runs_query = self.db.query(PipelineHistory).filter(
            PipelineHistory.status.in_(["failed", "canceled"])
        )
        if self.tenant_id is not None:
            failed_runs_query = failed_runs_query.filter(PipelineHistory.tenant_id == self.tenant_id)
        failed_runs = failed_runs_query.count()
        
        # If no data in database, fetch from Azure DevOps
        if total_runs == 0:
            logger.info("fetching_pipeline_history_from_azure")
            runs = await self.azure_client.get_pipeline_runs(top=100)
            
            # Store in database for future use
            for run in runs:
                existing = self.db.query(PipelineHistory).filter(
                    PipelineHistory.run_id == run.get("id")
                ).first()
                
                if not existing:
                    pipeline_run = PipelineHistory(
                        tenant_id=self.tenant_id,
                        pipeline_id=run.get("pipeline", {}).get("id"),
                        pipeline_name=run.get("pipeline", {}).get("name"),
                        run_id=run.get("id"),
                        status=run.get("state", "unknown"),
                        result=run.get("result"),
                        commit_id=run.get("sourceCommit", {}).get("commitId") if run.get("sourceCommit") else None,
                        branch=run.get("sourceBranch")
                    )
                    self.db.add(pipeline_run)
            
            self.db.commit()
            
            # Recalculate stats
            total_runs = len(runs)
            failed_runs = sum(
                1 for r in runs 
                if r.get("result") in ["failed", "canceled"]
            )
        
        return {
            "total_runs": total_runs,
            "failed_runs": failed_runs
        }
    
    def _save_analysis_result(
        self,
        pr_data: Dict,
        repository_id: str,
        changes_data: Dict,
        result: RiskAnalysisResult
    ):
        """Save analysis result to database"""
        
        change_entries = changes_data.get("changeEntries", [])
        
        pr_analysis = PRAnalysis(
            tenant_id=self.tenant_id,
            pr_id=pr_data.get("pullRequestId"),
            repository_id=repository_id,
            risk_score=result.risk_score,
            risk_level=result.risk_level,
            signals=json.dumps([s.__dict__ for s in result.signals]),
            recommendations=json.dumps(result.recommendations),
            pr_title=pr_data.get("title"),
            pr_author=pr_data.get("createdBy", {}).get("displayName"),
            files_changed=len(change_entries),
            lines_changed=len(change_entries) * 50  # Estimate
        )
        
        self.db.add(pr_analysis)
        self.db.commit()
        
        logger.info("analysis_saved_to_database", pr_id=pr_analysis.pr_id)
    
    def update_file_history(
        self,
        file_path: str,
        failed: bool = False
    ):
        """
        Update file history after a deployment
        
        Args:
            file_path: Path to the file
            failed: Whether the deployment failed
        """
        file_history = self.db.query(FileHistory).filter(
            FileHistory.file_path == file_path,
            FileHistory.tenant_id == self.tenant_id if self.tenant_id is not None else True,
        ).first()
        
        if not file_history:
            file_history = FileHistory(
                tenant_id=self.tenant_id,
                file_path=file_path,
                change_count=0,
                failure_count=0
            )
            self.db.add(file_history)
        
        file_history.change_count += 1
        if failed:
            file_history.failure_count += 1
        
        file_history.last_modified = func.now()
        self.db.commit()
        
        logger.info("file_history_updated",
                   file_path=file_path,
                   failure_rate=file_history.failure_rate)
