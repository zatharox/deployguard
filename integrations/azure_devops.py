import asyncio
import difflib
import httpx

from typing import Dict, List, Optional

import structlog

from config import get_settings

logger = structlog.get_logger()


class AzureDevOpsClient:
    """Client for Azure DevOps REST API interactions"""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = f"https://dev.azure.com/{self.settings.azure_devops_org}"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self._get_encoded_pat()}",
        }

    def _get_encoded_pat(self) -> str:
        """Encode PAT for Basic Auth"""
        import base64

        token = f":{self.settings.azure_devops_pat}"
        return base64.b64encode(token.encode()).decode()

    async def get_pull_request(
        self,
        repository_id: str,
        pr_id: int,
    ) -> Dict:
        """
        Get pull request details.
        """
        url = (
            f"{self.base_url}/{self.settings.azure_devops_project}"
            f"/_apis/git/repositories/{repository_id}"
            f"/pullrequests/{pr_id}"
            f"?api-version=7.0"
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self.headers,
                timeout=30.0,
            )
            response.raise_for_status()

            logger.info(
                "fetched_pull_request",
                pr_id=pr_id,
                repository_id=repository_id,
            )

            return response.json()

    async def get_pr_changes(
        self,
        repository_id: str,
        pr_id: int,
    ) -> Dict:
        """
        Get pull request file changes.
        """
        url = (
            f"{self.base_url}/{self.settings.azure_devops_project}"
            f"/_apis/git/repositories/{repository_id}"
            f"/pullrequests/{pr_id}/changes"
            f"?api-version=7.0"
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self.headers,
                timeout=30.0,
            )
            response.raise_for_status()

            data = response.json()

            logger.info(
                "fetched_pr_changes",
                pr_id=pr_id,
                files_changed=len(data.get("changeEntries", [])),
            )

            return data

    async def get_pr_diff_stats(
        self,
        repository_id: str,
        pr_id: int,
    ) -> Dict:
        """
        Calculate actual PR diff statistics.

        The method:
        1. Gets the latest PR iteration.
        2. Gets all changed files in that iteration.
        3. Fetches old/new Git blob contents.
        4. Calculates added/deleted lines locally.

        Returns:
            {
                "available": bool,
                "iteration_id": int | None,
                "files_changed": int,
                "lines_added": int,
                "lines_deleted": int,
                "lines_changed": int,
                "binary_files": int,
                "unavailable_files": int,
            }
        """

        iterations_url = (
            f"{self.base_url}/{self.settings.azure_devops_project}"
            f"/_apis/git/repositories/{repository_id}"
            f"/pullRequests/{pr_id}/iterations"
        )

        async with httpx.AsyncClient() as client:
            # ---------------------------------------------------------
            # 1. Get PR iterations.
            # ---------------------------------------------------------
            response = await client.get(
                iterations_url,
                params={
                    "api-version": "7.1",
                },
                headers=self.headers,
                timeout=30.0,
            )
            response.raise_for_status()

            iterations_data = response.json()
            iterations = iterations_data.get("value", [])

            if not iterations:
                logger.warning(
                    "pr_iterations_unavailable",
                    pr_id=pr_id,
                    repository_id=repository_id,
                )

                return {
                    "available": False,
                    "iteration_id": None,
                    "files_changed": 0,
                    "lines_added": 0,
                    "lines_deleted": 0,
                    "lines_changed": 0,
                    "binary_files": 0,
                    "unavailable_files": 0,
                    "reason": "No PR iterations available",
                }

            latest_iteration = max(
                iterations,
                key=lambda item: item.get("id", 0),
            )

            iteration_id = latest_iteration.get("id")

            if iteration_id is None:
                return {
                    "available": False,
                    "iteration_id": None,
                    "files_changed": 0,
                    "lines_added": 0,
                    "lines_deleted": 0,
                    "lines_changed": 0,
                    "binary_files": 0,
                    "unavailable_files": 0,
                    "reason": "Latest PR iteration has no ID",
                }

            # ---------------------------------------------------------
            # 2. Get all changes for latest iteration.
            # ---------------------------------------------------------
            change_entries = []
            skip = 0
            page_size = 2000

            while True:
                changes_url = (
                    f"{self.base_url}/{self.settings.azure_devops_project}"
                    f"/_apis/git/repositories/{repository_id}"
                    f"/pullRequests/{pr_id}"
                    f"/iterations/{iteration_id}/changes"
                )

                params = {
                    "$top": page_size,
                    "api-version": "7.1",
                }

                if skip:
                    params["$skip"] = skip

                changes_response = await client.get(
                    changes_url,
                    params=params,
                    headers=self.headers,
                    timeout=30.0,
                )
                changes_response.raise_for_status()

                page = changes_response.json()
                entries = page.get("changeEntries", [])

                change_entries.extend(entries)

                next_skip = page.get("nextSkip")

                if not next_skip or len(entries) < page_size:
                    break

                skip = next_skip

            # ---------------------------------------------------------
            # 3. Select actual files.
            # ---------------------------------------------------------
            file_entries = []

            for entry in change_entries:
                item = entry.get("item", {})

                path = item.get("path")
                if not path:
                    continue

                if item.get("gitObjectType") == "tree":
                    continue

                file_entries.append(entry)

            # ---------------------------------------------------------
            # 4. Blob cache and concurrency control.
            # ---------------------------------------------------------
            semaphore = asyncio.Semaphore(8)
            blob_cache: Dict[str, Optional[str]] = {}

            async def fetch_blob_text(
                blob_id: Optional[str],
            ) -> Optional[str]:

                if not blob_id:
                    return None

                if blob_id in blob_cache:
                    return blob_cache[blob_id]

                async with semaphore:
                    blob_url = (
                        f"{self.base_url}/{self.settings.azure_devops_project}"
                        f"/_apis/git/repositories/{repository_id}"
                        f"/blobs/{blob_id}"
                    )

                    blob_response = await client.get(
                        blob_url,
                        params={
                            "$format": "text",
                            "api-version": "7.1",
                        },
                        headers={
                            **self.headers,
                            "Accept": "text/plain",
                        },
                        timeout=30.0,
                    )

                    if blob_response.status_code == 404:
                        blob_cache[blob_id] = None
                        return None

                    blob_response.raise_for_status()

                    raw = blob_response.content

                    # Null bytes are a strong binary-file indicator.
                    if b"\x00" in raw:
                        blob_cache[blob_id] = None
                        return None

                    try:
                        content = raw.decode("utf-8")
                    except UnicodeDecodeError:
                        blob_cache[blob_id] = None
                        return None

                    blob_cache[blob_id] = content
                    return content

            # ---------------------------------------------------------
            # 5. Determine old/new blob IDs.
            # ---------------------------------------------------------
            blob_pairs = []

            for entry in file_entries:
                item = entry.get("item", {})

                change_type = (entry.get("changeType") or "").lower()

                current_blob = item.get("objectId")
                original_blob = item.get("originalObjectId")

                if change_type == "add":
                    original_blob = None

                elif change_type == "delete":
                    current_blob = None

                blob_pairs.append(
                    (
                        entry,
                        original_blob,
                        current_blob,
                    )
                )

            # ---------------------------------------------------------
            # 6. Fetch old/new contents concurrently.
            # ---------------------------------------------------------
            async def fetch_pair(pair):
                entry, old_blob, new_blob = pair

                old_content, new_content = await asyncio.gather(
                    fetch_blob_text(old_blob),
                    fetch_blob_text(new_blob),
                )

                return entry, old_content, new_content

            results = await asyncio.gather(*(fetch_pair(pair) for pair in blob_pairs))

            # ---------------------------------------------------------
            # 7. Calculate actual additions/deletions.
            # ---------------------------------------------------------
            lines_added = 0
            lines_deleted = 0
            binary_files = 0
            unavailable_files = 0

            for entry, old_content, new_content in results:

                change_type = (entry.get("changeType") or "").lower()

                # New file.
                if change_type == "add":
                    if new_content is None:
                        binary_files += 1
                        continue

                    lines_added += len(new_content.splitlines())
                    continue

                # Deleted file.
                if change_type == "delete":
                    if old_content is None:
                        binary_files += 1
                        continue

                    lines_deleted += len(old_content.splitlines())
                    continue

                # Modified / renamed / other text changes.
                if old_content is None or new_content is None:
                    unavailable_files += 1
                    continue

                old_lines = old_content.splitlines()
                new_lines = new_content.splitlines()

                matcher = difflib.SequenceMatcher(
                    None,
                    old_lines,
                    new_lines,
                    autojunk=False,
                )

                for tag, i1, i2, j1, j2 in matcher.get_opcodes():

                    if tag == "insert":
                        lines_added += j2 - j1

                    elif tag == "delete":
                        lines_deleted += i2 - i1

                    elif tag == "replace":
                        lines_deleted += i2 - i1
                        lines_added += j2 - j1

            lines_changed = lines_added + lines_deleted

            stats = {
                "available": True,
                "iteration_id": iteration_id,
                "files_changed": len(file_entries),
                "lines_added": lines_added,
                "lines_deleted": lines_deleted,
                "lines_changed": lines_changed,
                "binary_files": binary_files,
                "unavailable_files": unavailable_files,
            }

            logger.info(
                "calculated_pr_diff_stats",
                pr_id=pr_id,
                repository_id=repository_id,
                files_changed=len(file_entries),
                lines_added=lines_added,
                lines_deleted=lines_deleted,
                lines_changed=lines_changed,
                binary_files=binary_files,
                unavailable_files=unavailable_files,
            )

            return stats

    async def get_pipeline_runs(
        self,
        pipeline_id: Optional[int] = None,
        top: int = 100,
    ) -> List[Dict]:
        """
        Get pipeline runs for failure analysis.
        """
        url = (
            f"{self.base_url}/{self.settings.azure_devops_project}"
            f"/_apis/pipelines/runs"
            f"?api-version=7.0&$top={top}"
        )

        if pipeline_id:
            url += f"&pipelineId={pipeline_id}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self.headers,
                timeout=30.0,
            )
            response.raise_for_status()

            data = response.json()
            runs = data.get("value", [])

            logger.info(
                "fetched_pipeline_runs",
                count=len(runs),
            )

            return runs

    async def post_pr_comment(
        self,
        repository_id: str,
        pr_id: int,
        comment_text: str,
    ) -> Dict:
        """
        Post a comment thread to a pull request.
        """
        url = (
            f"{self.base_url}/{self.settings.azure_devops_project}"
            f"/_apis/git/repositories/{repository_id}"
            f"/pullrequests/{pr_id}/threads?api-version=7.0"
        )

        payload = {
            "comments": [
                {
                    "parentCommentId": 0,
                    "content": comment_text,
                    "commentType": 1,
                }
            ],
            "status": 1,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=30.0,
            )
            response.raise_for_status()

            logger.info(
                "posted_pr_comment",
                pr_id=pr_id,
                repository_id=repository_id,
            )

            return response.json()

    async def get_commit_files(
        self,
        repository_id: str,
        commit_id: str,
    ) -> List[Dict]:
        """
        Get files changed in a specific commit.
        """
        url = (
            f"{self.base_url}/{self.settings.azure_devops_project}"
            f"/_apis/git/repositories/{repository_id}"
            f"/commits/{commit_id}/changes?api-version=7.0"
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self.headers,
                timeout=30.0,
            )
            response.raise_for_status()

            data = response.json()
            changes = data.get("changes", [])

            logger.info(
                "fetched_commit_files",
                commit_id=commit_id,
                files=len(changes),
            )

            return changes
