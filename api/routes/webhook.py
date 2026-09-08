from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import json
import structlog

from db.database import get_db
from db.models import WebhookEvent, Repository
from db.schemas import WebhookPayload
from services.tasks import analyze_pr_task

router = APIRouter()
logger = structlog.get_logger()


SUPPORTED_EVENTS = {
    "git.pullrequest.created",
    "git.pullrequest.updated",
}


@router.post("/azure-devops")
async def handle_azure_devops_webhook(
    payload: WebhookPayload,
    db: Session = Depends(get_db),
):
    """
    Handle Azure DevOps webhook events.

    Supported events:
    - git.pullrequest.created
    - git.pullrequest.updated
    """

    event_type = payload.eventType
    resource = payload.resource
    notification_id = payload.notificationId

    logger.info(
        "webhook_received",
        event_type=event_type,
        subscription_id=payload.subscriptionId,
        notification_id=notification_id,
    )

    # ---------------------------------------------------------
    # Ignore unsupported events
    # ---------------------------------------------------------

    if event_type not in SUPPORTED_EVENTS:
        webhook_event = WebhookEvent(
            tenant_id=None,
            notification_id=notification_id,
            event_type=event_type,
            payload=json.dumps(payload.model_dump()),
            processed=1,
        )

        try:
            db.add(webhook_event)
            db.commit()

        except IntegrityError:
            db.rollback()

            existing_event = (
                db.query(WebhookEvent)
                .filter(
                    WebhookEvent.notification_id == notification_id
                )
                .first()
            )

            if existing_event:
                logger.info(
                    "webhook_duplicate",
                    notification_id=notification_id,
                    existing_event_id=existing_event.id,
                    event_type=event_type,
                )

                return {
                    "status": "duplicate",
                    "message": "Webhook notification already received",
                    "notification_id": notification_id,
                    "webhook_event_id": existing_event.id,
                    "processed": existing_event.processed,
                }

            raise

        logger.info(
            "webhook_ignored",
            event_type=event_type,
            notification_id=notification_id,
        )

        return {
            "status": "ignored",
            "message": f"Event type '{event_type}' not supported",
            "notification_id": notification_id,
        }

    # ---------------------------------------------------------
    # Extract PR information
    # ---------------------------------------------------------

    pr_id = resource.get("pullRequestId")

    repository = resource.get("repository") or {}
    repository_id = repository.get("id")

    if not pr_id:
        raise HTTPException(
            status_code=400,
            detail="Webhook payload is missing pullRequestId",
        )

    if not repository_id:
        raise HTTPException(
            status_code=400,
            detail="Webhook payload is missing repository.id",
        )

    # ---------------------------------------------------------
    # Resolve tenant from registered repository
    # ---------------------------------------------------------

    registered_repository = (
        db.query(Repository)
        .filter(
            Repository.external_repo_id == repository_id,
            Repository.provider == "azure-devops",
        )
        .first()
    )

    if registered_repository is None:
        logger.warning(
            "webhook_repository_not_registered",
            repository_id=repository_id,
            pr_id=pr_id,
            notification_id=notification_id,
        )

        raise HTTPException(
            status_code=404,
            detail=(
                f"Repository '{repository_id}' is not registered "
                "with DeployGuard"
            ),
        )

    tenant_id = registered_repository.tenant_id

    # ---------------------------------------------------------
    # Atomically claim the notification
    #
    # The unique DB index on notification_id guarantees that
    # concurrent duplicate requests cannot both create events.
    # ---------------------------------------------------------

    webhook_event = WebhookEvent(
        tenant_id=tenant_id,
        notification_id=notification_id,
        event_type=event_type,
        repository_id=repository_id,
        pr_id=pr_id,
        payload=json.dumps(payload.model_dump()),
        processed=0,
    )

    try:
        db.add(webhook_event)

        # Force INSERT now so IntegrityError is raised here,
        # before we enqueue a Celery task.
        db.flush()

        db.commit()
        db.refresh(webhook_event)

    except IntegrityError:
        db.rollback()

        existing_event = (
            db.query(WebhookEvent)
            .filter(
                WebhookEvent.notification_id == notification_id
            )
            .first()
        )

        if existing_event:
            logger.info(
                "webhook_duplicate",
                notification_id=notification_id,
                existing_event_id=existing_event.id,
                existing_status=existing_event.processed,
                event_type=event_type,
            )

            return {
                "status": "duplicate",
                "message": "Webhook notification already received",
                "notification_id": notification_id,
                "webhook_event_id": existing_event.id,
                "processed": existing_event.processed,
            }

        logger.error(
            "webhook_duplicate_detection_failed",
            notification_id=notification_id,
            repository_id=repository_id,
            pr_id=pr_id,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to determine webhook state",
        )

    # ---------------------------------------------------------
    # Enqueue asynchronous analysis
    # ---------------------------------------------------------

    try:
        task = analyze_pr_task.delay(
            repository_id=repository_id,
            pr_id=pr_id,
            tenant_id=tenant_id,
            webhook_event_id=webhook_event.id,
        )

    except Exception as exc:
        # Celery enqueue failed after the event was persisted.
        webhook_event.processed = -1
        webhook_event.error_message = str(exc)
        db.commit()

        logger.error(
            "webhook_analysis_enqueue_failed",
            webhook_event_id=webhook_event.id,
            notification_id=notification_id,
            task_error=str(exc),
        )

        raise HTTPException(
            status_code=503,
            detail="Webhook accepted but analysis could not be queued",
        )

    logger.info(
        "webhook_analysis_enqueued",
        webhook_event_id=webhook_event.id,
        task_id=task.id,
        tenant_id=tenant_id,
        pr_id=pr_id,
        repository_id=repository_id,
        notification_id=notification_id,
    )

    return {
        "status": "accepted",
        "message": "PR analysis queued",
        "notification_id": notification_id,
        "webhook_event_id": webhook_event.id,
        "pr_id": pr_id,
        "repository_id": repository_id,
        "tenant_id": tenant_id,
        "task_id": task.id,
    }