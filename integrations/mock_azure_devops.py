from typing import Dict, List, Optional


class MockAzureDevOpsClient:
    """Mock Azure DevOps client for local demo/testing mode."""

    def __init__(self):
        self._comments: List[Dict] = []

    async def get_pull_request(self, repository_id: str, pr_id: int) -> Dict:
        return {
            "pullRequestId": pr_id,
            "title": f"Demo PR #{pr_id}",
            "createdBy": {"displayName": "Demo Engineer"},
            "repository": {"id": repository_id},
        }

    async def get_pr_changes(self, repository_id: str, pr_id: int) -> Dict:
        # Deterministic scenarios by pr_id % 3
        scenario = pr_id % 3
        if scenario == 0:  # low risk
            files = ["/docs/readme.md", "/frontend/button.tsx"]
        elif scenario == 1:  # medium risk
            files = [
                "/core/cache.py",
                "/api/users.py",
                "/auth/session.py",
                "/frontend/profile.tsx",
                "/database/migrations/2026_03_10.sql",
                "/services/notification.py",
            ]
        else:  # high risk
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

        return {
            "changeEntries": [{"item": {"path": p}} for p in files]
        }

    async def get_pipeline_runs(
        self,
        pipeline_id: Optional[int] = None,
        top: int = 100,
    ) -> List[Dict]:
        runs: List[Dict] = []
        for i in range(top):
            # ~18% failed/canceled for realistic medium-high instability
            result = "failed" if i % 6 == 0 else "canceled" if i % 19 == 0 else "succeeded"
            runs.append(
                {
                    "id": 100000 + i,
                    "pipeline": {"id": pipeline_id or 1, "name": "demo-pipeline"},
                    "state": "completed",
                    "result": result,
                    "sourceBranch": "refs/heads/main",
                }
            )
        return runs

    async def post_pr_comment(self, repository_id: str, pr_id: int, comment_text: str) -> Dict:
        comment = {
            "id": len(self._comments) + 1,
            "repositoryId": repository_id,
            "pullRequestId": pr_id,
            "content": comment_text,
        }
        self._comments.append(comment)
        return comment

    async def get_commit_files(self, repository_id: str, commit_id: str) -> List[Dict]:
        return [{"item": {"path": "/core/demo.py"}}]
