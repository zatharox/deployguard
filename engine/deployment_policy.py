from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class DeploymentDecision:
    status: str
    label: str
    reason: str
    blocking: bool
    policy_version: str = "deployment-policy-v1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "label": self.label,
            "reason": self.reason,
            "blocking": self.blocking,
            "policy_version": self.policy_version,
        }


class DeploymentPolicy:
    """
    Deterministic deployment/release policy.

    The policy evaluates the already-computed risk analysis and
    change-intelligence results. It does not fetch external data
    and does not perform any additional analysis.

    Flow:

        Risk Analysis
            +
        Change Intelligence
            ↓
        Deployment Policy
            ↓
        SAFE / REVIEW / BLOCKED
    """

    POLICY_VERSION = "deployment-policy-v1"

    def evaluate(
        self,
        risk_level: str,
        risk_score: float,
        change_graph: Dict[str, Any] | None = None,
    ) -> DeploymentDecision:
        graph = change_graph or {}

        blast_radius = graph.get("blast_radius") or {}

        blast_level = str(
            blast_radius.get("level") or ""
        ).lower()

        confidence = str(
            blast_radius.get("confidence") or ""
        ).lower()

        critical_areas: List[str] = list(
            graph.get("critical_areas") or []
        )

        normalized_level = str(
            risk_level or "low"
        ).lower()

        # ---------------------------------------------------------
        # Policy 1:
        # Critical risk always blocks deployment.
        # ---------------------------------------------------------
        if normalized_level == "critical":
            return DeploymentDecision(
                status="blocked",
                label="DEPLOYMENT BLOCKED",
                reason=(
                    "Critical risk detected. "
                    "Deployment requires explicit approval "
                    "and mitigation."
                ),
                blocking=True,
                policy_version=self.POLICY_VERSION,
            )

        # ---------------------------------------------------------
        # Policy 2:
        # High risk combined with broad structural impact
        # blocks deployment.
        # ---------------------------------------------------------
        if (
            normalized_level == "high"
            and blast_level == "broad"
        ):
            return DeploymentDecision(
                status="blocked",
                label="DEPLOYMENT BLOCKED",
                reason=(
                    "High-risk changes have a broad structural "
                    "blast radius. Release approval and rollback "
                    "planning are required."
                ),
                blocking=True,
                policy_version=self.POLICY_VERSION,
            )

        # ---------------------------------------------------------
        # Policy 3:
        # High risk requires explicit engineering review.
        # ---------------------------------------------------------
        if normalized_level == "high":
            return DeploymentDecision(
                status="review_required",
                label="REVIEW REQUIRED",
                reason=(
                    "High deployment risk detected. "
                    "Senior engineer or release-owner review "
                    "is required before deployment."
                ),
                blocking=False,
                policy_version=self.POLICY_VERSION,
            )

        # ---------------------------------------------------------
        # Policy 4:
        # Any critical service area requires additional review.
        # ---------------------------------------------------------
        if critical_areas:
            return DeploymentDecision(
                status="review_required",
                label="REVIEW REQUIRED",
                reason=(
                    "Critical service areas are affected. "
                    "Validate regression coverage and rollback "
                    "readiness before deployment."
                ),
                blocking=False,
                policy_version=self.POLICY_VERSION,
            )

        # ---------------------------------------------------------
        # Policy 5:
        # Broad structural impact requires additional review
        # even when the aggregate risk level is not high.
        # ---------------------------------------------------------
        if blast_level == "broad":
            return DeploymentDecision(
                status="review_required",
                label="REVIEW REQUIRED",
                reason=(
                    "The change has a broad structural blast radius. "
                    "Additional review is recommended before release."
                ),
                blocking=False,
                policy_version=self.POLICY_VERSION,
            )

        # ---------------------------------------------------------
        # Policy 6:
        # Medium risk requires review.
        # ---------------------------------------------------------
        if normalized_level == "medium":
            return DeploymentDecision(
                status="review_recommended",
                label="REVIEW RECOMMENDED",
                reason=(
                    "Moderate deployment risk detected. "
                    "Complete normal validation and review "
                    "before release."
                ),
                blocking=False,
                policy_version=self.POLICY_VERSION,
            )

        # ---------------------------------------------------------
        # Policy 7:
        # Low confidence means the analysis is not strong enough
        # to automatically declare the change safe.
        # ---------------------------------------------------------
        if confidence == "low":
            return DeploymentDecision(
                status="review_recommended",
                label="REVIEW RECOMMENDED",
                reason=(
                    "Risk analysis confidence is low. "
                    "Additional validation is recommended "
                    "before deployment."
                ),
                blocking=False,
                policy_version=self.POLICY_VERSION,
            )

        # ---------------------------------------------------------
        # Default:
        # Low risk with no blocking/review conditions.
        # ---------------------------------------------------------
        return DeploymentDecision(
            status="safe",
            label="SAFE TO DEPLOY",
            reason=(
                "No deployment-blocking policy violations "
                "were detected. Standard review applies."
            ),
            blocking=False,
            policy_version=self.POLICY_VERSION,
        )
