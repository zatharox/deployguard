from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict
import json
import structlog

from db.models import PRAnalysis, FileHistory, PipelineHistory
from engine.change_graph import ChangeGraphAnalyzer
from engine.risk_analyzer import RiskEngine, RiskAnalysisResult
from integrations.azure_devops import AzureDevOpsClient
from integrations.mock_azure_devops import MockAzureDevOpsClient
from config import get_settings

logger = structlog.get_logger()


class AnalysisService:
    """Service layer for PR analysis orchestration."""

    def __init__(
        self,
        db: Session,
        tenant_id: int | None = None,
        correlation_id: str | None = None,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.correlation_id = correlation_id

        self.logger = logger.bind(
            correlation_id=correlation_id,
            tenant_id=tenant_id,
        )

        settings = get_settings()

        self.azure_client = (
            MockAzureDevOpsClient()
            if settings.demo_mode
            else AzureDevOpsClient()
        )

        self.risk_engine = RiskEngine()
        self.change_graph_analyzer = ChangeGraphAnalyzer()

    async def analyze_pr(
        self,
        repository_id: str,
        pr_id: int,
    ) -> RiskAnalysisResult:
        """
        Perform read-only PR analysis and persist the result.

        Steps:
        1. Fetch PR metadata.
        2. Fetch changed files.
        3. Calculate actual diff statistics.
        4. Load historical file risk.
        5. Load pipeline statistics.
        6. Run risk engine.
        7. Persist result.
        """

        self.logger.info(   
            "starting_pr_analysis",
            pr_id=pr_id,
            repository_id=repository_id,
        )

        # ---------------------------------------------------------
        # 1. Fetch PR metadata.
        # ---------------------------------------------------------
        pr_data = await self.azure_client.get_pull_request(
            repository_id,
            pr_id,
        )

        # ---------------------------------------------------------
        # 2. Fetch changed file entries.
        # ---------------------------------------------------------
        changes_data = await self.azure_client.get_pr_changes(
            repository_id,
            pr_id,
        )

        # ---------------------------------------------------------
        # 3. Calculate actual diff statistics.
        # ---------------------------------------------------------
        diff_stats = await self.azure_client.get_pr_diff_stats(
            repository_id=repository_id,
            pr_id=pr_id,
        )

        changes_data["diffStats"] = diff_stats
        # ---------------------------------------------------------
        # 3a. Structural change graph / blast radius.
        # ---------------------------------------------------------
        changed_files = [
            entry.get("item", {}).get("path", "")
            for entry in changes_data.get("changeEntries", [])
        ]

        change_graph = self.change_graph_analyzer.analyze(changed_files)

        changes_data["changeGraph"] = change_graph.to_dict()

        # ---------------------------------------------------------
        # 4. Historical file risk.
        # ---------------------------------------------------------
        file_history = self._get_file_history_dict()

        # ---------------------------------------------------------
        # 4a. Capture immutable file-impact snapshot.
        # ---------------------------------------------------------
        file_impacts = self._build_file_impacts(
            change_graph=change_graph.to_dict(),
        )

        changes_data["fileImpacts"] = file_impacts

        # Keep the file-impact snapshot inside the persisted
        # change graph so historical analyses do not change when
        # current FileHistory records change later.
        change_graph_data = change_graph.to_dict()
        change_graph_data["file_impacts"] = file_impacts
        changes_data["changeGraph"] = change_graph_data

        # ---------------------------------------------------------
        # 5. Pipeline statistics.
        # ---------------------------------------------------------
        pipeline_stats = await self._get_pipeline_stats()

        # ---------------------------------------------------------
        # 6. Risk analysis.
        # ---------------------------------------------------------
        result = await self.risk_engine.analyze_pr(
            pr_data=pr_data,
            changes_data=changes_data,
            file_history=file_history,
            pipeline_stats=pipeline_stats,
        )

        # ---------------------------------------------------------
        # 7. Save result.
        # ---------------------------------------------------------
        analysis = self._save_analysis_result(
            pr_data=pr_data,
            repository_id=repository_id,
            changes_data=changes_data,
            result=result,
        )

        result.analysis_id = analysis.id

        self.logger.info(
            "pr_analysis_completed",
            analysis_id=analysis.id,
            pr_id=pr_id,
            risk_score=result.risk_score,
            risk_level=result.risk_level,
        )

        return result

    async def analyze_and_comment_pr(
        self,
        repository_id: str,
        pr_id: int,
    ) -> RiskAnalysisResult:
        """
        Analyze a PR and post the generated risk report as a comment.
        """

        result = await self.analyze_pr(
            repository_id=repository_id,
            pr_id=pr_id,
        )

        comment_text = self.risk_engine.format_pr_comment(result)

        await self.azure_client.post_pr_comment(
            repository_id=repository_id,
            pr_id=pr_id,
            comment_text=comment_text,
        )

        return result

    def _get_file_history_dict(
        self,
    ) -> Dict[str, float]:
        """
        Return:
            {
                file_path: failure_rate
            }
        """

        query = self.db.query(FileHistory).filter(FileHistory.change_count > 0)

        if self.tenant_id is not None:
            query = query.filter(FileHistory.tenant_id == self.tenant_id)

        files = query.all()

        return {file.file_path: file.failure_rate for file in files}
    
    def _build_file_impacts(
        self,
        change_graph: Dict,
    ) -> list[Dict]:
        """
        Build an immutable file-impact snapshot for the current analysis.

        File impacts are derived from the current FileHistory records for
        files identified by Change Intelligence.

        The snapshot is stored inside change_graph so historical analyses
        retain the exact file-impact state that existed at analysis time.
        """

        changed_files = list(
            change_graph.get("changed_files") or []
        )

        if not changed_files:
            return []

        query = self.db.query(FileHistory).filter(
            FileHistory.file_path.in_(changed_files)
        )

        if self.tenant_id is not None:
            query = query.filter(
                FileHistory.tenant_id == self.tenant_id
            )

        history_records = query.all()

        history_by_path = {
            record.file_path: record
            for record in history_records
        }

        file_impacts: list[Dict] = []

        for file_path in changed_files:
            history = history_by_path.get(file_path)

            # No historical record for this file.
            if history is None:
                file_impacts.append(
                    {
                        "file_path": file_path,
                        "change_count": 0,
                        "failure_count": 0,
                        "failure_rate": 0.0,
                        "last_modified": None,
                        "impact_level": "unknown",
                        "historical_data_available": False,
                    }
                )
                continue

            failure_rate = float(
                history.failure_rate or 0.0
            )

            # Deterministic file-impact classification.
            if failure_rate >= 0.20:
                impact_level = "high"
            elif failure_rate >= 0.10:
                impact_level = "medium"
            elif failure_rate > 0:
                impact_level = "low"
            else:
                impact_level = "none"

            last_modified = None

            if history.last_modified is not None:
                last_modified = (
                    history.last_modified.isoformat()
                    if hasattr(history.last_modified, "isoformat")
                    else str(history.last_modified)
                )

            file_impacts.append(
                {
                    "file_path": file_path,
                    "change_count": int(
                        history.change_count or 0
                    ),
                    "failure_count": int(
                        history.failure_count or 0
                    ),
                    "failure_rate": failure_rate,
                    "last_modified": last_modified,
                    "impact_level": impact_level,
                    "historical_data_available": True,
                }
            )

        self.logger.info(
            "file_impacts_built",
            files_analyzed=len(file_impacts),
            files_with_history=sum(
                1
                for impact in file_impacts
                if impact["historical_data_available"]
            ),
            high_impact_files=sum(
                1
                for impact in file_impacts
                if impact["impact_level"] == "high"
            ),
        )

        return file_impacts
    async def _get_pipeline_stats(self) -> Dict:
        """
        Calculate pipeline statistics from recent runs.
        """

        total_runs_query = self.db.query(PipelineHistory)

        if self.tenant_id is not None:
            total_runs_query = total_runs_query.filter(
                PipelineHistory.tenant_id == self.tenant_id
            )

        total_runs = total_runs_query.count()

        failed_runs_query = self.db.query(PipelineHistory).filter(
            PipelineHistory.status.in_(["failed", "canceled"])
        )

        if self.tenant_id is not None:
            failed_runs_query = failed_runs_query.filter(
                PipelineHistory.tenant_id == self.tenant_id
            )

        failed_runs = failed_runs_query.count()

        # ---------------------------------------------------------
        # If DB does not contain pipeline history, get it from Azure.
        # ---------------------------------------------------------
        if total_runs == 0:

            logger.info("fetching_pipeline_history_from_azure")

            runs = await self.azure_client.get_pipeline_runs(top=100)

            for run in runs:

                existing = (
                    self.db.query(PipelineHistory)
                    .filter(PipelineHistory.run_id == run.get("id"))
                    .first()
                )

                if existing:
                    continue

                pipeline_info = run.get("pipeline", {})

                source_commit = run.get("sourceCommit") or {}

                pipeline_run = PipelineHistory(
                    tenant_id=self.tenant_id,
                    pipeline_id=pipeline_info.get("id") or 0,
                    pipeline_name=pipeline_info.get("name"),
                    run_id=run.get("id"),
                    status=run.get("result") or run.get("state", "unknown"),
                    result=run.get("result"),
                    commit_id=source_commit.get("commitId"),
                    branch=run.get("sourceBranch"),
                )

                self.db.add(pipeline_run)

            self.db.commit()

            total_runs = len(runs)

            failed_runs = sum(
                1 for run in runs if run.get("result") in ["failed", "canceled"]
            )

        return {
            "total_runs": total_runs,
            "failed_runs": failed_runs,
        }

    def _save_analysis_result(
        self,
        pr_data: Dict,
        repository_id: str,
        changes_data: Dict,
        result: RiskAnalysisResult,
    ) -> PRAnalysis:
        """
        Persist analysis result.

        Actual diff statistics are stored when available.
        """

        change_entries = changes_data.get("changeEntries", [])

        diff_stats = changes_data.get("diffStats") or {}

        files_changed = diff_stats.get("files_changed")

        if files_changed is None:
            files_changed = len(change_entries)

        lines_changed = diff_stats.get("lines_changed")

        if lines_changed is not None:
            lines_changed = int(lines_changed)

        pr_analysis = PRAnalysis(
            tenant_id=self.tenant_id,
            pr_id=pr_data.get("pullRequestId"),
            repository_id=repository_id,
            risk_score=result.risk_score,
            risk_level=result.risk_level,
            signals=json.dumps([s.__dict__ for s in result.signals]),
            recommendations=json.dumps(result.recommendations),
            change_graph=(
                json.dumps(result.change_graph)
                if result.change_graph is not None
                else None
            ),
            pr_title=pr_data.get("title"),
            pr_author=(pr_data.get("createdBy", {}).get("displayName")),
            files_changed=files_changed,
            lines_changed=lines_changed,
        )

        self.db.add(pr_analysis)
        self.db.commit()
        self.db.refresh(pr_analysis)

        self.logger.info(
            "analysis_saved_to_database",
            analysis_id=pr_analysis.id,
            pr_id=pr_analysis.pr_id,
        )

        return pr_analysis

    def update_file_history(
        self,
        file_path: str,
        failed: bool = False,
    ):
        """
        Update file modification/failure history.
        """

        query = self.db.query(FileHistory).filter(FileHistory.file_path == file_path)

        if self.tenant_id is not None:
            query = query.filter(FileHistory.tenant_id == self.tenant_id)

        file_history = query.first()

        if not file_history:

            file_history = FileHistory(
                tenant_id=self.tenant_id,
                file_path=file_path,
                change_count=0,
                failure_count=0,
            )

            self.db.add(file_history)

        file_history.change_count += 1

        if failed:
            file_history.failure_count += 1

        file_history.last_modified = func.now()

        self.db.commit()

        self.logger.info(
            "file_history_updated",
            file_path=file_path,
            failure_rate=file_history.failure_rate,
        )
