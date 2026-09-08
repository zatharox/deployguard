import asyncio
import structlog

from db.database import SessionLocal
from db.models import WebhookEvent
from services.analysis_service import AnalysisService
from services.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    name="deployguard.analyze_pr",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def analyze_pr_task(
    self,
    repository_id: str,
    pr_id: int,
    tenant_id: int,
    webhook_event_id: int | None = None,
):
    """
    Execute PR risk analysis asynchronously through Celery.
    """

    logger.info(
        "celery_pr_analysis_started",
        task_id=self.request.id,
        repository_id=repository_id,
        pr_id=pr_id,
        tenant_id=tenant_id,
        webhook_event_id=webhook_event_id,
    )

    db = SessionLocal()

    try:
        service = AnalysisService(
            db=db,
            tenant_id=tenant_id,
        )

        result = asyncio.run(
            service.analyze_and_comment_pr(
                repository_id=repository_id,
                pr_id=pr_id,
            )
        )

        # ---------------------------------------------------------
        # Mark webhook as successfully processed
        # ---------------------------------------------------------

        if webhook_event_id is not None:
            webhook_event = (
                db.query(WebhookEvent)
                .filter(WebhookEvent.id == webhook_event_id)
                .first()
            )

            if webhook_event:
                webhook_event.processed = 1
                webhook_event.error_message = None
                db.commit()

        logger.info(
            "celery_pr_analysis_completed",
            task_id=self.request.id,
            analysis_id=result.analysis_id,
            repository_id=repository_id,
            pr_id=pr_id,
            tenant_id=tenant_id,
            risk_score=result.risk_score,
            risk_level=result.risk_level,
        )

        return {
            "status": "success",
            "analysis_id": result.analysis_id,
            "pr_id": pr_id,
            "repository_id": repository_id,
            "tenant_id": tenant_id,
            "risk_score": result.risk_score,
            "risk_level": result.risk_level,
        }

    except Exception as exc:

        logger.error(
            "celery_pr_analysis_failed",
            task_id=self.request.id,
            repository_id=repository_id,
            pr_id=pr_id,
            tenant_id=tenant_id,
            webhook_event_id=webhook_event_id,
            error=str(exc),
        )

        # ---------------------------------------------------------
        # Mark webhook as failed
        # ---------------------------------------------------------

        if webhook_event_id is not None:
            try:
                webhook_event = (
                    db.query(WebhookEvent)
                    .filter(WebhookEvent.id == webhook_event_id)
                    .first()
                )

                if webhook_event:
                    webhook_event.processed = -1
                    webhook_event.error_message = str(exc)
                    db.commit()

            except Exception:
                db.rollback()

        raise

    finally:
        db.close()