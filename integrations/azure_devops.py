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
            "Authorization": f"Basic {self._get_encoded_pat()}"
        }
    
    def _get_encoded_pat(self) -> str:
        """Encode PAT for Basic Auth"""
        import base64
        token = f":{self.settings.azure_devops_pat}"
        return base64.b64encode(token.encode()).decode()
    
    async def get_pull_request(self, repository_id: str, pr_id: int) -> Dict:
        """
        Get pull request details
        
        API: GET /_apis/git/repositories/{repoId}/pullRequests/{pullRequestId}
        """
        url = f"{self.base_url}/{self.settings.azure_devops_project}/_apis/git/repositories/{repository_id}/pullrequests/{pr_id}?api-version=7.0"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, timeout=30.0)
            response.raise_for_status()
            
            logger.info("fetched_pull_request", pr_id=pr_id, repository_id=repository_id)
            return response.json()
    
    async def get_pr_changes(self, repository_id: str, pr_id: int) -> Dict:
        """
        Get pull request file changes
        
        API: GET /_apis/git/repositories/{repoId}/pullRequests/{pullRequestId}/changes
        """
        url = f"{self.base_url}/{self.settings.azure_devops_project}/_apis/git/repositories/{repository_id}/pullrequests/{pr_id}/changes?api-version=7.0"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, timeout=30.0)
            response.raise_for_status()
            
            data = response.json()
            logger.info("fetched_pr_changes", 
                       pr_id=pr_id, 
                       files_changed=len(data.get("changeEntries", [])))
            return data
    
    async def get_pipeline_runs(
        self, 
        pipeline_id: Optional[int] = None,
        top: int = 100
    ) -> List[Dict]:
        """
        Get pipeline runs for failure analysis
        
        API: GET /_apis/pipelines/runs
        """
        url = f"{self.base_url}/{self.settings.azure_devops_project}/_apis/pipelines/runs?api-version=7.0&$top={top}"
        
        if pipeline_id:
            url += f"&pipelineId={pipeline_id}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, timeout=30.0)
            response.raise_for_status()
            
            data = response.json()
            runs = data.get("value", [])
            logger.info("fetched_pipeline_runs", count=len(runs))
            return runs
    
    async def post_pr_comment(
        self, 
        repository_id: str, 
        pr_id: int, 
        comment_text: str
    ) -> Dict:
        """
        Post a comment thread to a pull request
        
        API: POST /_apis/git/repositories/{repoId}/pullRequests/{prId}/threads
        """
        url = f"{self.base_url}/{self.settings.azure_devops_project}/_apis/git/repositories/{repository_id}/pullrequests/{pr_id}/threads?api-version=7.0"
        
        payload = {
            "comments": [
                {
                    "parentCommentId": 0,
                    "content": comment_text,
                    "commentType": 1  # Text comment
                }
            ],
            "status": 1  # Active
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, 
                json=payload, 
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            
            logger.info("posted_pr_comment", pr_id=pr_id, repository_id=repository_id)
            return response.json()
    
    async def get_commit_files(self, repository_id: str, commit_id: str) -> List[Dict]:
        """
        Get files changed in a specific commit
        
        API: GET /_apis/git/repositories/{repoId}/commits/{commitId}/changes
        """
        url = f"{self.base_url}/{self.settings.azure_devops_project}/_apis/git/repositories/{repository_id}/commits/{commit_id}/changes?api-version=7.0"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, timeout=30.0)
            response.raise_for_status()
            
            data = response.json()
            changes = data.get("changes", [])
            logger.info("fetched_commit_files", commit_id=commit_id, files=len(changes))
            return changes
