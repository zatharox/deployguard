from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import re

import structlog

from config import get_settings

logger = structlog.get_logger()


@dataclass
class RiskSignal:
    """Individual risk signal result."""

    name: str
    score: float
    description: str
    details: Optional[str] = None


@dataclass
class RiskAnalysisResult:
    """Complete risk analysis result."""

    risk_score: float
    risk_level: str
    signals: List[RiskSignal]
    recommendations: List[str]
    analysis_id: Optional[int] = None
    change_graph: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return {
            "analysis_id": self.analysis_id,
            "risk_score": round(
                self.risk_score,
                2,
            ),
            "risk_level": self.risk_level,
            "signals": [
                {
                    "name": signal.name,
                    "score": round(
                        signal.score,
                        2,
                    ),
                    "description": signal.description,
                    "details": signal.details,
                }
                for signal in self.signals
            ],
            "recommendations": self.recommendations,
            "change_graph": self.change_graph,
        }


class RiskEngine:
    """Core risk analysis engine."""

    def __init__(self):
        self.settings = get_settings()

    async def analyze_pr(
        self,
        pr_data: Dict,
        changes_data: Dict,
        file_history: Dict[str, float],
        pipeline_stats: Dict,
    ) -> RiskAnalysisResult:

        signals: List[RiskSignal] = []

        # Signal 1
        signals.append(self._analyze_commit_size(changes_data))

        # Signal 2
        signals.append(
            self._analyze_file_instability(
                changes_data,
                file_history,
            )
        )

        # Signal 3
        signals.append(self._analyze_pipeline_history(pipeline_stats))

        # Signal 4
        signals.append(self._analyze_critical_directories(changes_data))

        # Signal 5
        signals.append(
            self._analyze_author_risk(
                pr_data,
                file_history,
            )
        )

        # Signal 6
        signals.append(self._analyze_time_risk(pr_data))

        # Signal 7
        signals.append(self._analyze_dependency_changes(changes_data))

        # Signal 8
        signals.append(
            self._analyze_blast_radius(
                changes_data,
            )
        )

        raw_risk = sum(signal.score for signal in signals)

        total_risk= min (raw_risk,10.0,)

        if total_risk >= self.settings.high_risk_threshold:
            risk_level = "high"

        elif total_risk >= self.settings.medium_risk_threshold:
            risk_level = "medium"

        else:
            risk_level = "low"

        recommendations = self._generate_recommendations(
            signals,
            risk_level,
        )

        logger.info(
            "risk_analysis_completed",
            pr_id=pr_data.get("pullRequestId"),
            risk_score=total_risk,
            risk_level=risk_level,
        )

        return RiskAnalysisResult(
            risk_score=total_risk,
            risk_level=risk_level,
            signals=signals,
            recommendations=recommendations,
            change_graph=changes_data.get("changeGraph"),
        )

    
    def _analyze_blast_radius(
    self,
    changes_data: Dict,
    ) -> RiskSignal:
            """
            Signal 8: Structural blast radius.

            The ChangeGraphAnalyzer produces a 0-10 structural score.
            This signal converts that score to a maximum 2-point
            contribution to the overall risk score.
            """

            change_graph = changes_data.get("changeGraph") or {}

            blast_radius = change_graph.get("blast_radius") or {}

            structural_score = float(
                blast_radius.get("score", 0.0)
            )

            level = blast_radius.get(
                "level",
                "narrow",
            )

            confidence = blast_radius.get(
                "confidence",
                "low",
            )

            contribution = min(
                structural_score / 5.0,
                2.0,
            )

            changed_files = change_graph.get(
                "changed_files",
                [],
            )

            components = change_graph.get(
                "components",
                [],
            )

            critical_areas = change_graph.get(
                "critical_areas",
                [],
            )

            description = (
                f"{level.capitalize()} structural blast radius: "
                f"{len(changed_files)} files across "
                f"{len(components)} components"
            )

            details = (
                f"Structural score: {structural_score:.1f}/10, "
                f"confidence: {confidence}"
            )

            if critical_areas:
                details += (
                    ", critical areas: "
                    + ", ".join(critical_areas)
                )

            return RiskSignal(
                name="Blast Radius Risk",
                score=round(contribution, 2),
                description=description,
                details=details,
            )


    def _analyze_commit_size(
        self,
        changes_data: Dict,
    ) -> RiskSignal:
        """
        Signal 1: Actual PR diff size.

        Uses Azure DevOps diff statistics when available.

        No synthetic "50 lines per file" estimate is used.
        """

        change_entries = changes_data.get("changeEntries", [])

        diff_stats = changes_data.get("diffStats") or {}

        files_changed = diff_stats.get("files_changed")

        if files_changed is None:
            files_changed = len(change_entries)

        diff_available = bool(
            diff_stats.get(
                "available",
                False,
            )
        )

        if diff_available:

            lines_added = int(
                diff_stats.get(
                    "lines_added",
                    0,
                )
            )

            lines_deleted = int(
                diff_stats.get(
                    "lines_deleted",
                    0,
                )
            )

            total_lines = int(
                diff_stats.get(
                    "lines_changed",
                    lines_added + lines_deleted,
                )
            )

            binary_files = int(
                diff_stats.get(
                    "binary_files",
                    0,
                )
            )

            unavailable_files = int(
                diff_stats.get(
                    "unavailable_files",
                    0,
                )
            )

            # ---------------------------------------------------------
            # Risk scoring.
            # ---------------------------------------------------------
            if total_lines > 500:

                score = 3.0

                description = (
                    f"Very large change: "
                    f"{total_lines} lines across "
                    f"{files_changed} files"
                )

            elif total_lines > self.settings.max_lines_low_risk:

                score = 2.0

                description = (
                    f"Large change: "
                    f"{total_lines} lines across "
                    f"{files_changed} files"
                )

            elif total_lines > 100:

                score = 1.0

                description = (
                    f"Moderate change: "
                    f"{total_lines} lines across "
                    f"{files_changed} files"
                )

            else:

                score = 0.5

                description = (
                    f"Small change: "
                    f"{total_lines} lines across "
                    f"{files_changed} files"
                )

            details = (
                f"Files changed: {files_changed}, "
                f"Added: {lines_added}, "
                f"Deleted: {lines_deleted}"
            )

            if binary_files:
                details += f", Binary files: {binary_files}"

            if unavailable_files:
                details += f", Unavailable files: " f"{unavailable_files}"

            return RiskSignal(
                name="Commit Size Risk",
                score=score,
                description=description,
                details=details,
            )

        # -------------------------------------------------------------
        # Fallback.
        #
        # Important: we do NOT fabricate line counts here.
        # -------------------------------------------------------------
        if files_changed <= 2:
            score = 0.5

        elif files_changed <= 5:
            score = 1.0

        elif files_changed <= 10:
            score = 2.0

        else:
            score = 3.0

        return RiskSignal(
            name="Commit Size Risk",
            score=score,
            description=(f"Line count unavailable: " f"{files_changed} files changed"),
            details=("Diff content could not be calculated"),
        )

    def _analyze_file_instability(
        self,
        changes_data: Dict,
        file_history: Dict[str, float],
    ) -> RiskSignal:

        change_entries = changes_data.get("changeEntries", [])

        unstable_files = []
        max_failure_rate = 0.0

        for entry in change_entries:

            file_path = entry.get("item", {}).get("path", "")

            if file_path in file_history:

                failure_rate = file_history[file_path]

                if failure_rate > 0.15:

                    unstable_files.append(
                        (
                            file_path,
                            failure_rate,
                        )
                    )

                    max_failure_rate = max(
                        max_failure_rate,
                        failure_rate,
                    )

        if max_failure_rate > 0.25:

            score = 3.0

            description = (
                f"{len(unstable_files)} " "historically unstable files modified"
            )

        elif max_failure_rate > 0.15:

            score = 2.0

            description = f"{len(unstable_files)} " "files with elevated failure rates"

        elif unstable_files:

            score = 1.0

            description = f"{len(unstable_files)} " "files with some failure history"

        else:

            score = 0.0

            description = "No historically unstable files modified"

        details = None

        if unstable_files:

            top_files = sorted(
                unstable_files,
                key=lambda item: item[1],
                reverse=True,
            )[:3]

            details = "Top unstable files: " + ", ".join(
                f"{path.split('/')[-1]} " f"({rate * 100:.0f}%)"
                for path, rate in top_files
            )

        return RiskSignal(
            name="File Instability Risk",
            score=score,
            description=description,
            details=details,
        )

    def _analyze_pipeline_history(
        self,
        pipeline_stats: Dict,
    ) -> RiskSignal:

        total_runs = pipeline_stats.get(
            "total_runs",
            0,
        )

        failed_runs = pipeline_stats.get(
            "failed_runs",
            0,
        )

        if total_runs == 0:

            return RiskSignal(
                name="Pipeline History Risk",
                score=0.0,
                description=("No pipeline history available"),
                details="Insufficient data",
            )

        failure_rate = failed_runs / total_runs

        if failure_rate > 0.20:

            score = 2.0

            description = f"High pipeline failure rate: " f"{failure_rate * 100:.1f}%"

        elif failure_rate > 0.10:

            score = 1.5

            description = (
                f"Elevated pipeline failure rate: " f"{failure_rate * 100:.1f}%"
            )

        elif failure_rate > 0.05:

            score = 0.5

            description = (
                f"Moderate pipeline failure rate: " f"{failure_rate * 100:.1f}%"
            )

        else:

            score = 0.0

            description = f"Low pipeline failure rate: " f"{failure_rate * 100:.1f}%"

        return RiskSignal(
            name="Pipeline History Risk",
            score=score,
            description=description,
            details=(f"Recent runs: {total_runs}, " f"Failed: {failed_runs}"),
        )

    def _analyze_critical_directories(
        self,
        changes_data: Dict,
    ) -> RiskSignal:

        critical_paths = [
            "/auth/",
            "/authentication/",
            "/payment/",
            "/billing/",
            "/core/",
            "/kernel/",
            "/database/",
            "/db/",
            "/security/",
            "/api/",
        ]

        change_entries = changes_data.get("changeEntries", [])

        critical_files = []

        for entry in change_entries:

            file_path = entry.get("item", {}).get("path", "").lower()

            for critical_path in critical_paths:

                if critical_path in file_path:

                    critical_files.append(
                        (
                            file_path,
                            critical_path,
                        )
                    )

                    break

        if len(critical_files) >= 3:

            score = 2.0

            description = f"{len(critical_files)} " "critical service files modified"

        elif len(critical_files) >= 1:

            score = 1.5

            description = f"{len(critical_files)} " "critical service file(s) modified"

        else:

            score = 0.0

            description = "No critical service areas affected"

        details = None

        if critical_files:

            affected_areas = set(area.strip("/") for _, area in critical_files)

            details = "Affected areas: " + ", ".join(sorted(affected_areas))

        return RiskSignal(
            name="Critical Directory Risk",
            score=score,
            description=description,
            details=details,
        )

    def _analyze_author_risk(
        self,
        pr_data: Dict,
        file_history: Dict[str, float],
    ) -> RiskSignal:

        created_by = pr_data.get("createdBy", {})

        author_name = created_by.get(
            "displayName",
            "Unknown",
        )

        avg_failure_rate = sum(file_history.values()) / max(
            len(file_history),
            1,
        )

        if avg_failure_rate > 0.3:

            score = 1.5

            description = (
                f"Author's modified files have "
                f"{avg_failure_rate * 100:.0f}% "
                "historical failure rate"
            )

        elif avg_failure_rate > 0.15:

            score = 0.8

            description = (
                f"Author's modified files have "
                f"{avg_failure_rate * 100:.0f}% "
                "historical failure rate"
            )

        else:

            score = 0.0

            description = "Author has good track record " "on these files"

        return RiskSignal(
            name="Author Risk Profile",
            score=score,
            description=description,
            details=f"Author: {author_name}",
        )

    def _analyze_time_risk(
        self,
        pr_data: Dict,
    ) -> RiskSignal:

        created_date = pr_data.get("creationDate")

        if not created_date:

            return RiskSignal(
                name="Time-of-Day Risk",
                score=0.0,
                description=("PR creation time unavailable"),
            )

        try:

            dt = datetime.fromisoformat(
                created_date.replace(
                    "Z",
                    "+00:00",
                )
            )

            hour = dt.hour
            weekday = dt.weekday()

            score = 0.0
            reasons = []

            if weekday >= 5:

                score += 1.0
                reasons.append("weekend deployment")

            elif weekday == 4:

                score += 0.5
                reasons.append("Friday deployment")

            if hour < 8 or hour > 18:

                score += 0.5
                reasons.append("after-hours PR")

            if score > 0:

                description = "Elevated risk: " + ", ".join(reasons)

            else:

                description = "PR created during " "safe deployment window"

            day_name = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ][weekday]

            details = f"Created: {day_name} " f"at {hour:02d}:00"

            return RiskSignal(
                name="Time-of-Day Risk",
                score=min(score, 2.0),
                description=description,
                details=details,
            )

        except Exception as exc:

            logger.warning(
                "time_risk_analysis_failed",
                error=str(exc),
            )

            return RiskSignal(
                name="Time-of-Day Risk",
                score=0.0,
                description=("Could not analyze PR timing"),
            )

    def _analyze_dependency_changes(
        self,
        changes_data: Dict,
    ) -> RiskSignal:

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
            "packages.config",
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

            description = (
                "Multiple dependency files " f"modified ({len(modified_deps)} files)"
            )

        elif len(modified_deps) == 1:

            score = 1.5

            description = "Dependency file modified - " "version conflicts possible"

        else:

            score = 0.0

            description = "No dependency file changes"

        details = None

        if modified_deps:

            details = "Modified: " + ", ".join(
                path.split("/")[-1] for path in modified_deps
            )

        return RiskSignal(
            name="Dependency Change Risk",
            score=score,
            description=description,
            details=details,
        )

    def _generate_recommendations(
        self,
        signals: List[RiskSignal],
        risk_level: str,
    ) -> List[str]:

        recommendations = []

        if risk_level == "high":

            recommendations.append(
                "⚠️ High risk detected - " "Require senior engineer review"
            )

            recommendations.append("Consider breaking this PR " "into smaller changes")

        for signal in signals:

            if signal.name == "Commit Size Risk" and signal.score >= 2.0:

                recommendations.append(
                    "Large changeset - Review " "carefully for logic errors"
                )

            if signal.name == "File Instability Risk" and signal.score >= 2.0:

                recommendations.append(
                    "Modified files have failure " "history - Add extra tests"
                )

            if signal.name == "Pipeline History Risk" and signal.score >= 1.5:

                recommendations.append(
                    "Pipeline has been unstable - " "Monitor deployment closely"
                )

            if signal.name == "Critical Directory Risk" and signal.score >= 1.5:

                recommendations.append(
                    "Critical services affected - " "Ensure rollback plan is ready"
                )

            if signal.name == "Dependency Change Risk" and signal.score >= 1.5:

                recommendations.append(
                    "Dependency changes detected - "
                    "Test thoroughly across environments"
                )

            if signal.name == "Time-of-Day Risk" and signal.score >= 1.0:

                recommendations.append(
                    "Off-hours deployment - " "Ensure on-call support is available"
                )

        if not recommendations:

            recommendations.append("✅ Low risk - Standard review " "process applies")

        return recommendations

    def format_pr_comment(
        self,
        result: RiskAnalysisResult,
    ) -> str:
        """Format risk analysis as a PR comment."""

        emoji = {
            "high": "🔴",
            "medium": "🟡",
            "low": "🟢",
        }[result.risk_level]

        gate_status = {
            "high": ("⛔ Release Gate: BLOCK " "(manual approval required)"),
            "medium": ("⚠️ Release Gate: REVIEW " "(senior reviewer recommended)"),
            "low": ("✅ Release Gate: PASS " "(standard workflow)"),
        }[result.risk_level]

        dominant_signals = sorted(
            result.signals,
            key=lambda signal: signal.score,
            reverse=True,
        )[:2]

        dominant_text = ", ".join(
            f"{signal.name} " f"({signal.score:.1f})" for signal in dominant_signals
        )

        commit_signal = next(
            (signal for signal in result.signals if signal.name == "Commit Size Risk"),
            None,
        )

        pipeline_signal = next(
            (
                signal
                for signal in result.signals
                if signal.name == "Pipeline History Risk"
            ),
            None,
        )

        critical_signal = next(
            (
                signal
                for signal in result.signals
                if signal.name == "Critical Directory Risk"
            ),
            None,
        )

        changed_files = self._extract_files_changed(
            commit_signal.description if commit_signal else ""
        )

        changed_lines = self._extract_lines_changed(
            commit_signal.description if commit_signal else ""
        )

        pipeline_failure = self._extract_percentage(
            pipeline_signal.description if pipeline_signal else ""
        )

        impacted_areas = (
            critical_signal.details
            if critical_signal and critical_signal.details
            else "Affected areas: none"
        )

        required_checks = self._build_required_checks(result)

        comment = f"""## {emoji} DeployGuard Risk Report

**Risk Score:** {result.risk_score:.1f} / 10 ({result.risk_level.upper()} RISK)

### Executive Summary
• **Gate Decision:** {gate_status}
• **Dominant Risk Drivers:** {dominant_text}
• **Recommended Review Depth:** {
    "Deep review + test evidence"
    if result.risk_level in ["medium", "high"]
    else "Standard code review"
}

### Key Metrics
| Metric | Value |
|---|---|
| Lines changed | {changed_lines} |
| Files changed | {changed_files} |
| Pipeline failure trend | {pipeline_failure} |
| Critical impact | {impacted_areas.replace("Affected areas: ", "")} |

### Risk Signals
"""

        for signal in result.signals:

            comment += f"\n**{signal.name}** " f"({signal.score:.1f} points)\n"

            comment += f"• {signal.description}\n"

            if signal.details:

                comment += f"  _{signal.details}_\n"

        comment += "\n### Recommendations\n"

        for recommendation in result.recommendations:

            comment += f"• {recommendation}\n"

        comment += "\n### Required Checks Before Merge\n"

        for check in required_checks:

            comment += f"• {check}\n"

        comment += "\n### Audit Metadata\n"

        comment += "• Model version: `risk-engine-v1`\n"

        comment += f"• Signal count: " f"`{len(result.signals)}`\n"

        comment += (
            "• Generated by policy thresholds: "
            f"high≥{self.settings.high_risk_threshold}, "
            f"medium≥{self.settings.medium_risk_threshold}\n"
        )

        comment += (
            "\n---\n" "_Powered by " "[DeployGuard](https://github.com/zatharox)_"
        )

        return comment

    def _extract_files_changed(
        self,
        text: str,
    ) -> str:

        match = re.search(
            r"(\d+) files",
            text,
        )

        return match.group(1) if match else "N/A"

    def _extract_lines_changed(
        self,
        text: str,
    ) -> str:
        """
        Extract changed-line count from the commit
        size description.
        """

        match = re.search(
            r"(\d+) lines",
            text,
        )

        return match.group(1) if match else "N/A"

    def _extract_percentage(
        self,
        text: str,
    ) -> str:

        match = re.search(
            r"(\d+(?:\.\d+)?)%",
            text,
        )

        return f"{match.group(1)}%" if match else "N/A"

    def _build_required_checks(
        self,
        result: RiskAnalysisResult,
    ) -> List[str]:

        checks = [
            "CI pipeline must pass on latest commit",
            "At least one reviewer must approve",
        ]

        for signal in result.signals:

            if signal.name == "Critical Directory Risk" and signal.score >= 1.5:

                checks.append(
                    "Attach rollback strategy for " "impacted critical services"
                )

            if signal.name == "File Instability Risk" and signal.score >= 2.0:

                checks.append(
                    "Add/attach targeted regression " "tests for unstable files"
                )

            if signal.name == "Pipeline History Risk" and signal.score >= 1.5:

                checks.append(
                    "Monitor post-merge pipeline and "
                    "deployment with on-call visibility"
                )

        if result.risk_level == "high":

            checks.append("Require senior engineer or " "release manager approval")

        # Preserve order and remove duplicates.
        seen = set()
        unique = []

        for check in checks:

            if check not in seen:

                unique.append(check)
                seen.add(check)

        return unique
