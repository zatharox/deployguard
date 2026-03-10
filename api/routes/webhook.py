from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
import json
import structlog

from db.database import get_db
from db.models import WebhookEvent
from db.schemas import WebhookPayload
from services.analysis_service import AnalysisService

router = APIRouter()
logger = structlog.get_logger()


@router.post("/azure-devops")
async def handle_azure_devops_webhook(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Handle Azure DevOps webhook events
    
    Supported events:
    - git.pullrequest.created
    - git.pullrequest.updated
    """
    
    event_type = payload.eventType
    resource = payload.resource
    
    logger.info("webhook_received", event_type=event_type, subscription_id=payload.subscriptionId, notification_id=payload.notificationId)
    
    # Log webhook event
    webhook_event = WebhookEvent(
        event_type=event_type,
        payload=json.dumps(payload.dict()),
        processed=0
    )
    
    try:
        # Extract PR information
        if event_type in ["git.pullrequest.created", "git.pullrequest.updated"]:
            pr_id = resource.get("pullRequestId")
            repository = resource.get("repository", {})
            repository_id = repository.get("id")
            
            webhook_event.pr_id = pr_id
            webhook_event.repository_id = repository_id
            
            db.add(webhook_event)
            db.commit()
            
            # Trigger analysis in background
            background_tasks.add_task(
                analyze_pr_background,
                pr_id=pr_id,
                repository_id=repository_id,
                webhook_event_id=webhook_event.id,
                db=db
            )
            
            logger.info("webhook_queued_for_processing",
                       webhook_event_id=webhook_event.id,
                       pr_id=pr_id,
                       repository_id=repository_id)
            
            return {
                "status": "accepted",
                "message": "PR analysis queued",
                "pr_id": pr_id
            }
        
        else:
            webhook_event.processed = 1  # Mark as processed (ignored)
            db.add(webhook_event)
            db.commit()
            
            logger.info("webhook_ignored", event_type=event_type)
            return {
                "status": "ignored",
                "message": f"Event type '{event_type}' not supported"
            }
    
    except Exception as e:
        webhook_event.processed = -1
        webhook_event.error_message = str(e)
        db.add(webhook_event)
        db.commit()
        
        logger.error("webhook_processing_failed", event_type=event_type, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


async def analyze_pr_background(
    pr_id: int,
    repository_id: str,
    webhook_event_id: int,
    db: Session
):
    """Background task to analyze PR and post comment"""
    try:
        logger.info("webhook_background_started", webhook_event_id=webhook_event_id, pr_id=pr_id, repository_id=repository_id)
        analysis_service = AnalysisService(db)
        
        # Run analysis and post comment
        await analysis_service.analyze_and_comment_pr(
            repository_id=repository_id,
            pr_id=pr_id
        )
        
        # Mark webhook as processed
        webhook_event = db.query(WebhookEvent).filter(
            WebhookEvent.id == webhook_event_id
        ).first()
        
        if webhook_event:
            webhook_event.processed = 1
            db.commit()
        
        logger.info("webhook_background_completed", webhook_event_id=webhook_event_id, pr_id=pr_id)
    
    except Exception as e:
        logger.error("webhook_background_failed", webhook_event_id=webhook_event_id, pr_id=pr_id, error=str(e))
        
        # Mark webhook as error
        webhook_event = db.query(WebhookEvent).filter(
            WebhookEvent.id == webhook_event_id
        ).first()
        
        if webhook_event:
            webhook_event.processed = -1
            webhook_event.error_message = str(e)
            db.commit()
