from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import re
import structlog
from config import get_settings

logger = structlog.get_logger()


@dataclass
class RiskSignal:
    """Individual risk signal result"""
    name: str
    score: float
    description: str
    details: Optional[str] = None


@dataclass
class RiskAnalysisResult:
    """Complete risk analysis result"""
    risk_score: float
    risk_level: str  # "low", "medium", "high"
    signals: List[RiskSignal]
    recommendations: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "risk_score": round(self.risk_score, 2),
            "risk_level": self.risk_level,
            "signals": [
                {
                    "name": s.name,
                    "score": round(s.score, 2),
                    "description": s.description,
                    "details": s.details
                }
                for s in self.signals
            ],
            "recommendations": self.recommendations
        }


class RiskEngine:
    """Core risk analysis engine with 4 key signals"""
    
    def __init__(self):
        self.settings = get_settings()
    
    async def analyze_pr(
        self,
        pr_data: Dict,
        changes_data: Dict,
        file_history: Dict[str, float],
        pipeline_stats: Dict
    ) -> RiskAnalysisResult:
        """
        Analyze pull request and calculate risk score
        
        Args:
            pr_data: PR details from Azure DevOps API
            changes_data: File changes from Azure DevOps API
            file_history: Historical file failure rates {file_path: failure_rate}
            pipeline_stats: Pipeline statistics {total_runs, failed_runs}
        """
        signals = []
        
        # Signal 1: Commit Size Risk
        size_signal = self._analyze_commit_size(changes_data)
        signals.append(size_signal)
        
        # Signal 2: File Instability Risk
        instability_signal = self._analyze_file_instability(changes_data, file_history)
        signals.append(instability_signal)
        
        # Signal 3: Pipeline Failure History Risk
        pipeline_signal = self._analyze_pipeline_history(pipeline_stats)
        signals.append(pipeline_signal)
        
        # Signal 4: Critical Directory Risk
        critical_signal = self._analyze_critical_directories(changes_data)
        signals.append(critical_signal)
        
        # Signal 5: Author Risk Profile
        author_signal = self._analyze_author_risk(pr_data, file_history)
        signals.append(author_signal)
        
        # Signal 6: Time-of-Day Risk
        time_signal = self._analyze_time_risk(pr_data)
        signals.append(time_signal)
        
        # Signal 7: Dependency Changes Risk
        dependency_signal = self._analyze_dependency_changes(changes_data)
        signals.append(dependency_signal)
        
        # Calculate total risk score (0-10 scale)
        total_risk = sum(s.score for s in signals)
        
        # Determine risk level
        if total_risk >= self.settings.high_risk_threshold:
            risk_level = "high"
        elif total_risk >= self.settings.medium_risk_threshold:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Generate recommendations
        recommendations = self._generate_recommendations(signals, risk_level)
        
        logger.info("risk_analysis_completed",
                   pr_id=pr_data.get("pullRequestId"),
                   risk_score=total_risk,
                   risk_level=risk_level)
        
        return RiskAnalysisResult(
            risk_score=total_risk,
            risk_level=risk_level,
            signals=signals,
            recommendations=recommendations
        )
    
    def _analyze_commit_size(self, changes_data: Dict) -> RiskSignal:
        """Signal 1: Large changes → higher failure probability"""
        change_entries = changes_data.get("changeEntries", [])
        
        total_lines = 0
        files_changed = len(change_entries)
        
        # Calculate total lines changed
        for entry in change_entries:
            item = entry.get("item", {})
            # Note: Azure DevOps API doesn't always provide line counts in changes
            # You may need to fetch diffs separately for accurate counts
            # For MVP, we estimate based on file count
            total_lines += 50  # Average estimate per file
        
        # Calculate risk score (0-3 points)
        if total_lines > 500:
            score = 3.0
            description = f"{total_lines}+ lines modified across {files_changed} files"
        elif total_lines > self.settings.max_lines_low_risk:
            score = 2.0
            description = f"{total_lines} lines modified across {files_changed} files"
        elif total_lines > 100:
            score = 1.0
            description = f"{total_lines} lines modified across {files_changed} files"
        else:
            score = 0.5
            description = f"Small change: {total_lines} lines across {files_changed} files"
        
        return RiskSignal(
            name="Commit Size Risk",
            score=score,
            description=description,
            details=f"Files changed: {files_changed}"
        )
    
    def _analyze_file_instability(
        self, 
        changes_data: Dict, 
        file_history: Dict[str, float]
    ) -> RiskSignal:
        """Signal 2: Files with historical failure rates"""
        change_entries = changes_data.get("changeEntries", [])
        
        unstable_files = []
        max_failure_rate = 0.0
        
        for entry in change_entries:
            file_path = entry.get("item", {}).get("path", "")
            
            if file_path in file_history:
                failure_rate = file_history[file_path]
                if failure_rate > 0.15:  # 15% failure threshold
                    unstable_files.append((file_path, failure_rate))
                    max_failure_rate = max(max_failure_rate, failure_rate)
        
        # Calculate risk score (0-3 points)
        if max_failure_rate > 0.25:
            score = 3.0
            description = f"{len(unstable_files)} historically unstable files modified"
        elif max_failure_rate > 0.15:
            score = 2.0
            description = f"{len(unstable_files)} files with elevated failure rates"
        elif unstable_files:
            score = 1.0
            description = f"{len(unstable_files)} files with some failure history"
        else:
            score = 0.0
            description = "No historically unstable files modified"
        
        details = None
        if unstable_files:
            top_files = sorted(unstable_files, key=lambda x: x[1], reverse=True)[:3]
            details = "Top unstable files: " + ", ".join(
                f"{f[0].split('/')[-1]} ({f[1]*100:.0f}%)" for f in top_files
            )
        
        return RiskSignal(
            name="File Instability Risk",
            score=score,
            description=description,
            details=details
        )
    
    def _analyze_pipeline_history(self, pipeline_stats: Dict) -> RiskSignal:
        """Signal 3: Overall pipeline failure rate"""
        total_runs = pipeline_stats.get("total_runs", 0)
        failed_runs = pipeline_stats.get("failed_runs", 0)
        
        if total_runs == 0:
            return RiskSignal(
                name="Pipeline History Risk",
                score=0.0,
                description="No pipeline history available",
                details="Insufficient data"
            )
        
        failure_rate = failed_runs / total_runs
        
        # Calculate risk score (0-2 points)
        if failure_rate > 0.20:
            score = 2.0
            description = f"High pipeline failure rate: {failure_rate*100:.1f}%"
        elif failure_rate > 0.10:
            score = 1.5
            description = f"Elevated pipeline failure rate: {failure_rate*100:.1f}%"
        elif failure_rate > 0.05:
            score = 0.5
            description = f"Moderate pipeline failure rate: {failure_rate*100:.1f}%"
        else:
            score = 0.0
            description = f"Low pipeline failure rate: {failure_rate*100:.1f}%"
        
        return RiskSignal(
            name="Pipeline History Risk",
            score=score,
            description=description,
            details=f"Recent runs: {total_runs}, Failed: {failed_runs}"
        )
    
    def _analyze_critical_directories(self, changes_data: Dict) -> RiskSignal:
        """Signal 4: Critical service areas detection"""
        critical_paths = [
            "/auth/", "/authentication/",
            "/payment/", "/billing/",
            "/core/", "/kernel/",
            "/database/", "/db/",
            "/security/",
            "/api/",
        ]
        
        change_entries = changes_data.get("changeEntries", [])
        critical_files = []
        
        for entry in change_entries:
            file_path = entry.get("item", {}).get("path", "").lower()
            
            for critical_path in critical_paths:
                if critical_path in file_path:
                    critical_files.append((file_path, critical_path))
                    break
        
        # Calculate risk score (0-2 points)
        if len(critical_files) >= 3:
            score = 2.0
            description = f"{len(critical_files)} critical service files modified"
        elif len(critical_files) >= 1:
            score = 1.5
            description = f"{len(critical_files)} critical service file(s) modified"
        else:
            score = 0.0
            description = "No critical service areas affected"
        
        details = None
        if critical_files:
            affected_areas = set(c[1].strip('/') for c in critical_files)
            details = f"Affected areas: {', '.join(affected_areas)}"
        
        return RiskSignal(
            name="Critical Directory Risk",
            score=score,
            description=description,
            details=details
        )
    
    def _analyze_author_risk(self, pr_data: Dict, file_history: Dict[str, float]) -> RiskSignal:
        """Signal 5: Author experience and past contribution quality"""
        created_by = pr_data.get("createdBy", {})
        author_name = created_by.get("displayName", "Unknown")
        
        # Simple heuristic: new contributors or contributors with high failure history
        # In production, this would query historical commit/PR success rates
        
        # For demo, use simple rules
        is_new_contributor = False  # Would check commit history
        avg_failure_rate = sum(file_history.values()) / max(len(file_history), 1)
        
        if avg_failure_rate > 0.3:
            score = 1.5
            description = f"Author's modified files have {avg_failure_rate*100:.0f}% historical failure rate"
        elif avg_failure_rate > 0.15:
            score = 0.8
            description = f"Author's modified files have {avg_failure_rate*100:.0f}% historical failure rate"
        else:
            score = 0.0
            description = "Author has good track record on these files"
        
        return RiskSignal(
            name="Author Risk Profile",
            score=score,
            description=description,
            details=f"Author: {author_name}"
        )
    
    def _analyze_time_risk(self, pr_data: Dict) -> RiskSignal:
        """Signal 6: Deployments late in day/week are riskier"""
        created_date = pr_data.get("creationDate")
        
        if not created_date:
            return RiskSignal(
                name="Time-of-Day Risk",
                score=0.0,
                description="PR creation time unavailable"
            )
        
        try:
            # Parse Azure DevOps datetime format
            dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
            hour = dt.hour
            weekday = dt.weekday()  # 0=Monday, 6=Sunday
            
            # Risk factors:
            # - After hours (before 8am or after 6pm): +0.5
            # - Friday: +0.5
            # - Weekend: +1.0
            
            score = 0.0
            reasons = []
            
            if weekday >= 5:  # Weekend
                score += 1.0
                reasons.append("weekend deployment")
            elif weekday == 4:  # Friday
                score += 0.5
                reasons.append("Friday deployment")
            
            if hour < 8 or hour > 18:
                score += 0.5
                reasons.append("after-hours PR")
            
            if score > 0:
                description = f"Elevated risk: {', '.join(reasons)}"
            else:
                description = "PR created during safe deployment window"
            
            day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][weekday]
            details = f"Created: {day_name} at {hour:02d}:00"
            
            return RiskSignal(
                name="Time-of-Day Risk",
                score=min(score, 2.0),
                description=description,
                details=details
            )
        except Exception as e:
            logger.warning("time_risk_analysis_failed", error=str(e))
            return RiskSignal(
                name="Time-of-Day Risk",
                score=0.0,
                description="Could not analyze PR timing"
            )
    
    def _analyze_dependency_changes(self, changes_data: Dict) -> RiskSignal:
        """Signal 7: Changes to dependency files are high-risk"""
        dependency_files = [
            "package.json",
            "requirements.txt",
            "pom.xml",
            "build.gradle",
            "go.mod",
            "cargo.toml",
            "composer.json",
            "gemfile",
            ".csproj",
            "packages.config"
        ]
        
        change_entries = changes_data.get("changeEntries", [])
        modified_deps = []
        
        for entry in change_entries:
            file_path = entry.get("item", {}).get("path", "").lower()
            file_name = file_path.split("/")[-1]
            
            for dep_file in dependency_files:
                if dep_file in file_name:
                    modified_deps.append(file_path)
                    break
        
        if len(modified_deps) >= 2:
            score = 2.0
            description = f"Multiple dependency files modified ({len(modified_deps)} files)"
        elif len(modified_deps) == 1:
            score = 1.5
            description = "Dependency file modified - version conflicts possible"
        else:
            score = 0.0
            description = "No dependency file changes"
        
        details = None
        if modified_deps:
            details = f"Modified: {', '.join([f.split('/')[-1] for f in modified_deps])}"
        
        return RiskSignal(
            name="Dependency Change Risk",
            score=score,
            description=description,
            details=details
        )
    
    def _generate_recommendations(
        self, 
        signals: List[RiskSignal], 
        risk_level: str
    ) -> List[str]:
        """Generate actionable recommendations based on signals"""
        recommendations = []
        
        if risk_level == "high":
            recommendations.append("⚠️ High risk detected - Require senior engineer review")
            recommendations.append("Consider breaking this PR into smaller changes")
        
        for signal in signals:
            if signal.name == "Commit Size Risk" and signal.score >= 2.0:
                recommendations.append("Large changeset - Review carefully for logic errors")
            
            if signal.name == "File Instability Risk" and signal.score >= 2.0:
                recommendations.append("Modified files have failure history - Add extra tests")
            
            if signal.name == "Pipeline History Risk" and signal.score >= 1.5:
                recommendations.append("Pipeline has been unstable - Monitor deployment closely")
            
            if signal.name == "Critical Directory Risk" and signal.score >= 1.5:
                recommendations.append("Critical services affected - Ensure rollback plan is ready")
            
            if signal.name == "Dependency Change Risk" and signal.score >= 1.5:
                recommendations.append("Dependency changes detected - Test thoroughly across environments")
            
            if signal.name == "Time-of-Day Risk" and signal.score >= 1.0:
                recommendations.append("Off-hours deployment - Ensure on-call support is available")
        
        if not recommendations:
            recommendations.append("✅ Low risk - Standard review process applies")
        
        return recommendations
    
    def format_pr_comment(self, result: RiskAnalysisResult) -> str:
        """Format risk analysis as a PR comment"""
        emoji = {
            "high": "🔴",
            "medium": "🟡",
            "low": "🟢"
        }[result.risk_level]

        gate_status = {
            "high": "⛔ Release Gate: BLOCK (manual approval required)",
            "medium": "⚠️ Release Gate: REVIEW (senior reviewer recommended)",
            "low": "✅ Release Gate: PASS (standard workflow)",
        }[result.risk_level]

        dominant_signals = sorted(result.signals, key=lambda s: s.score, reverse=True)[:2]
        dominant_text = ", ".join(f"{s.name} ({s.score:.1f})" for s in dominant_signals)

        commit_signal = next((s for s in result.signals if s.name == "Commit Size Risk"), None)
        pipeline_signal = next((s for s in result.signals if s.name == "Pipeline History Risk"), None)
        critical_signal = next((s for s in result.signals if s.name == "Critical Directory Risk"), None)

        changed_files = self._extract_files_changed(commit_signal.description if commit_signal else "")
        est_lines = self._extract_estimated_lines(commit_signal.description if commit_signal else "")
        pipeline_failure = self._extract_percentage(pipeline_signal.description if pipeline_signal else "")
        impacted_areas = critical_signal.details if (critical_signal and critical_signal.details) else "Affected areas: none"

        required_checks = self._build_required_checks(result)
        
        comment = f"""## {emoji} DeployGuard Risk Report

**Risk Score:** {result.risk_score:.1f} / 10 ({result.risk_level.upper()} RISK)

### Executive Summary
• **Gate Decision:** {gate_status}
• **Dominant Risk Drivers:** {dominant_text}
• **Recommended Review Depth:** {"Deep review + test evidence" if result.risk_level in ["medium", "high"] else "Standard code review"}

### Key Metrics
| Metric | Value |
|---|---|
| Estimated lines changed | {est_lines} |
| Files changed | {changed_files} |
| Pipeline failure trend | {pipeline_failure} |
| Critical impact | {impacted_areas.replace('Affected areas: ', '')} |

### Risk Signals
"""
        
        for signal in result.signals:
            comment += f"\n**{signal.name}** ({signal.score:.1f} points)\n"
            comment += f"• {signal.description}\n"
            if signal.details:
                comment += f"  _{signal.details}_\n"
        
        comment += "\n### Recommendations\n"
        for rec in result.recommendations:
            comment += f"• {rec}\n"

        comment += "\n### Required Checks Before Merge\n"
        for check in required_checks:
            comment += f"• {check}\n"

        comment += "\n### Audit Metadata\n"
        comment += f"• Model version: `risk-engine-v1`\n"
        comment += f"• Signal count: `{len(result.signals)}`\n"
        comment += f"• Generated by policy thresholds: high≥{self.settings.high_risk_threshold}, medium≥{self.settings.medium_risk_threshold}\n"
        
        comment += "\n---\n_Powered by [DeployGuard](https://github.com/zatharox)_"
        
        return comment

    def _extract_files_changed(self, text: str) -> str:
        m = re.search(r"(\d+) files", text)
        return m.group(1) if m else "N/A"

    def _extract_estimated_lines(self, text: str) -> str:
        m = re.search(r"(\d+)\+? lines", text)
        return m.group(1) if m else "N/A"

    def _extract_percentage(self, text: str) -> str:
        m = re.search(r"(\d+(?:\.\d+)?)%", text)
        return f"{m.group(1)}%" if m else "N/A"

    def _build_required_checks(self, result: RiskAnalysisResult) -> List[str]:
        checks = [
            "CI pipeline must pass on latest commit",
            "At least one reviewer must approve",
        ]

        for signal in result.signals:
            if signal.name == "Critical Directory Risk" and signal.score >= 1.5:
                checks.append("Attach rollback strategy for impacted critical services")
            if signal.name == "File Instability Risk" and signal.score >= 2.0:
                checks.append("Add/attach targeted regression tests for unstable files")
            if signal.name == "Pipeline History Risk" and signal.score >= 1.5:
                checks.append("Monitor post-merge pipeline and deployment with on-call visibility")

        if result.risk_level == "high":
            checks.append("Require senior engineer or release manager approval")

        # Preserve order, remove duplicates
        seen = set()
        unique = []
        for c in checks:
            if c not in seen:
                unique.append(c)
                seen.add(c)
        return unique
