from typing import Dict, List, Optional


class MockAzureDevOpsClient:
    """Mock Azure DevOps client for local demo/testing mode."""

    def __init__(self):
        self._comments: List[Dict] = []

    async def get_pull_request(
        self,
        repository_id: str,
        pr_id: int,
    ) -> Dict:
        return {
            "pullRequestId": pr_id,
            "title": f"Demo PR #{pr_id}",
            "createdBy": {"displayName": "Demo Engineer"},
        }

    async def get_pr_changes(
        self,
        repository_id: str,
        pr_id: int,
    ) -> Dict:
        """
        Deterministic file-change scenarios.
        """

        scenario = pr_id % 3

        if scenario == 0:
            # Low-risk PR
            files = [
                "/docs/readme.md",
                "/frontend/button.tsx",
            ]

        elif scenario == 1:
            # Medium-risk PR
            files = [
                "/core/cache.py",
                "/api/users.py",
                "/auth/session.py",
                "/frontend/profile.tsx",
                "/database/migrations/2026_03_10.sql",
                "/services/notification.py",
            ]

        else:
            # High-risk PR
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
            "changeEntries": [
                {
                    "item": {
                        "path": path,
                    }
                }
                for path in files
            ]
        }

    async def get_pr_diff_stats(
        self,
        repository_id: str,
        pr_id: int,
    ) -> Dict:
        """
        Deterministic diff statistics for local/demo testing.
        """

        scenario = pr_id % 3

        if scenario == 0:
            return {
                "available": True,
                "iteration_id": 1,
                "files_changed": 2,
                "lines_added": 18,
                "lines_deleted": 7,
                "lines_changed": 25,
                "binary_files": 0,
                "unavailable_files": 0,
            }

        if scenario == 1:
            return {
                "available": True,
                "iteration_id": 1,
                "files_changed": 6,
                "lines_added": 142,
                "lines_deleted": 51,
                "lines_changed": 193,
                "binary_files": 0,
                "unavailable_files": 0,
            }

        return {
            "available": True,
            "iteration_id": 1,
            "files_changed": 12,
            "lines_added": 521,
            "lines_deleted": 188,
            "lines_changed": 709,
            "binary_files": 0,
            "unavailable_files": 0,
        }

    async def get_pipeline_runs(
        self,
        pipeline_id: Optional[int] = None,
        top: int = 100,
    ) -> List[Dict]:

        runs: List[Dict] = []

        for i in range(top):

            result = (
                "failed" if i % 6 == 0 else "canceled" if i % 19 == 0 else "succeeded"
            )

            runs.append(
                {
                    "id": 100000 + i,
                    "pipeline": {
                        "id": pipeline_id or 1,
                        "name": "demo-pipeline",
                    },
                    "state": "completed",
                    "result": result,
                    "sourceBranch": "refs/heads/main",
                    "sourceCommit": {},
                }
            )

        return runs

    async def post_pr_comment(
        self,
        repository_id: str,
        pr_id: int,
        comment_text: str,
    ) -> Dict:

        comment = {
            "id": len(self._comments) + 1,
            "repositoryId": repository_id,
            "pullRequestId": pr_id,
            "content": comment_text,
        }

        self._comments.append(comment)

        return comment

    async def get_commit_files(
        self,
        repository_id: str,
        commit_id: str,
    ) -> List[Dict]:

        return [
            {
                "item": {
                    "path": "/core/demo.py",
                }
            }
        ]
