"""
Azure DevOps connectivity testing endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import structlog
from typing import Dict, Optional

from integrations.azure_devops import AzureDevOpsClient
from services.auth_service import get_current_user
from db.models import User

router = APIRouter()
logger = structlog.get_logger()


class AzureTestRequest(BaseModel):
    organization: str
    project: str
    pat: str


class ConnectivityTestResult(BaseModel):
    status: str
    organization: str
    project: str
    tests: Dict[str, dict]
    summary: str


@router.post("/test-connection", response_model=ConnectivityTestResult)
async def test_azure_connection(
    request: AzureTestRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Test Azure DevOps API connectivity with provided credentials.
    Tests: authentication, project access, PR API, repository access.
    """
    logger.info("testing_azure_connection", 
                user_id=current_user.id,
                org=request.organization,
                project=request.project)
    
    client = AzureDevOpsClient(
        organization=request.organization,
        project=request.project,
        pat=request.pat
    )
    
    tests = {}
    
    # Test 1: Basic authentication
    try:
        # Try to get project info
        project_url = f"https://dev.azure.com/{request.organization}/_apis/projects/{request.project}?api-version=7.0"
        response = await client._make_request("GET", project_url)
        tests["authentication"] = {
            "status": "success",
            "message": "Successfully authenticated with Azure DevOps",
            "project_id": response.get("id"),
            "project_name": response.get("name")
        }
    except Exception as e:
        tests["authentication"] = {
            "status": "failed",
            "message": f"Authentication failed: {str(e)}"
        }
        return ConnectivityTestResult(
            status="failed",
            organization=request.organization,
            project=request.project,
            tests=tests,
            summary="Authentication failed. Check PAT permissions and organization/project names."
        )
    
    # Test 2: Repository access
    try:
        repos = await client.get_repositories()
        tests["repositories"] = {
            "status": "success",
            "message": f"Found {len(repos)} repositories",
            "count": len(repos),
            "sample_repos": [r["name"] for r in repos[:3]]
        }
    except Exception as e:
        tests["repositories"] = {
            "status": "failed",
            "message": f"Repository access failed: {str(e)}"
        }
    
    # Test 3: Pull Request API access
    try:
        # Try to list PRs (even if empty)
        pr_url = f"https://dev.azure.com/{request.organization}/{request.project}/_apis/git/pullrequests?api-version=7.0&searchCriteria.status=all&$top=1"
        response = await client._make_request("GET", pr_url)
        pr_count = response.get("count", 0)
        tests["pull_requests"] = {
            "status": "success",
            "message": f"PR API accessible. Found {pr_count} recent PRs",
            "accessible": True
        }
    except Exception as e:
        tests["pull_requests"] = {
            "status": "failed",
            "message": f"PR API access failed: {str(e)}"
        }
    
    # Test 4: Pipeline API access
    try:
        pipeline_url = f"https://dev.azure.com/{request.organization}/{request.project}/_apis/pipelines?api-version=7.0"
        response = await client._make_request("GET", pipeline_url)
        pipeline_count = response.get("count", 0)
        tests["pipelines"] = {
            "status": "success",
            "message": f"Pipeline API accessible. Found {pipeline_count} pipelines",
            "count": pipeline_count
        }
    except Exception as e:
        tests["pipelines"] = {
            "status": "failed",
            "message": f"Pipeline API access failed: {str(e)}"
        }
    
    # Determine overall status
    failed_tests = [k for k, v in tests.items() if v.get("status") == "failed"]
    
    if not failed_tests:
        status = "success"
        summary = f"All connectivity tests passed! Connected to {request.organization}/{request.project}"
    elif len(failed_tests) == len(tests):
        status = "failed"
        summary = "All tests failed. Check credentials and permissions."
    else:
        status = "partial"
        summary = f"{len(tests) - len(failed_tests)}/{len(tests)} tests passed. Some APIs may not be accessible."
    
    logger.info("azure_connection_test_completed",
                user_id=current_user.id,
                status=status,
                failed_tests=failed_tests)
    
    return ConnectivityTestResult(
        status=status,
        organization=request.organization,
        project=request.project,
        tests=tests,
        summary=summary
    )


@router.get("/webhook-setup-guide")
async def get_webhook_setup_guide(
    current_user: User = Depends(get_current_user)
):
    """
    Get step-by-step guide for setting up Azure DevOps webhooks
    """
    return {
        "title": "Azure DevOps Webhook Setup Guide",
        "steps": [
            {
                "step": 1,
                "title": "Navigate to Project Settings",
                "description": "Go to your Azure DevOps project → Project Settings → Service Hooks"
            },
            {
                "step": 2,
                "title": "Create Service Hook",
                "description": "Click '+ Create subscription' → Select 'Web Hooks' as the service"
            },
            {
                "step": 3,
                "title": "Configure Trigger",
                "description": "Select 'Pull request created' or 'Pull request updated' as the trigger event",
                "options": [
                    "Pull request created",
                    "Pull request updated",
                    "Pull request merge attempted"
                ]
            },
            {
                "step": 4,
                "title": "Set Webhook URL",
                "description": "Enter your DeployGuard webhook URL",
                "url_format": "https://your-deployguard-domain.com/api/v1/webhook/azure-devops",
                "headers": {
                    "X-Tenant-Slug": "your-tenant-slug",
                    "Authorization": "Bearer your-api-key"
                }
            },
            {
                "step": 5,
                "title": "Test Webhook",
                "description": "Use the 'Test' button in Azure DevOps to send a test event"
            }
        ],
        "required_permissions": [
            "Project Collection Administrator (to create service hooks)",
            "Or custom role with 'Edit subscriptions' permission"
        ],
        "troubleshooting": {
            "webhook_not_firing": "Check that the trigger event matches your PR workflow",
            "401_unauthorized": "Verify your API key or bearer token is correct",
            "404_not_found": "Check the webhook URL is accessible from Azure DevOps",
            "timeout": "Ensure your DeployGuard instance is publicly accessible"
        }
    }
