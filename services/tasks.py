import asyncio
import uuid

import structlog
from celery.exceptions import MaxRetriesExceededError

from db.database import SessionLocal
from db.models import WebhookEvent
from services.analysis_service import AnalysisService
from services.celery_app import celery_app
from services.metrics import MetricsService, MetricsTimer


logger = structlog.get_logger()


MAX_RETRIES = 3
SOFT_TIME_LIMIT = 300
HARD_TIME_LIMIT = 360


def _safe_increment(
    metrics: MetricsService,
    metric: str,
    amount: int = 1,
) -> None:
    """
    Increment a metric without allowing metrics infrastructure
    failures to affect the actual analysis task.
    """
    try:
        metrics.increment(
            metric,
            amount,
        )
    except Exception as exc:
        logger.warning(
            "metrics_increment_failed",
            metric=metric,
            error=str(exc),
            error_type=type(exc).__name__,
        )


def _safe_record_duration(
    metrics: MetricsService,
    duration_seconds: float,
) -> None:
    """
    Record analysis duration without allowing metrics failures
    to affect the analysis result.
    """
    try:
        metrics.record_duration(
            duration_seconds,
        )
    except Exception as exc:
        logger.warning(
            "metrics_duration_record_failed",
            duration_seconds=duration_seconds,
            error=str(exc),
            error_type=type(exc).__name__,
        )


def _safe_record_deployment_decision(
    metrics: MetricsService,
    status: str | None,
) -> None:
    """
    Record deployment decision metrics without allowing metrics
    failures to affect the analysis task.
    """
    try:
        metrics.record_deployment_decision(
            status,
        )
    except Exception as exc:
        logger.warning(
            "metrics_deployment_decision_record_failed",
            deployment_status=status,
            error=str(exc),
            error_type=type(exc).__name__,
        )


@celery_app.task(
    name="deployguard.analyze_pr",
    bind=True,
    max_retries=MAX_RETRIES,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=SOFT_TIME_LIMIT,
    time_limit=HARD_TIME_LIMIT,
)
def analyze_pr_task(
    self,
    repository_id: str,
    pr_id: int,
    tenant_id: int,
    webhook_event_id: int | None = None,
    correlation_id: str | None = None,
):
    """
    Execute PR risk analysis asynchronously through Celery.

    Reliability guarantees:
    - Late task acknowledgement
    - Worker-loss requeue
    - Explicit retry handling
    - Exponential retry backoff
    - Maximum retry limit
    - Soft/hard execution limits
    - Structured lifecycle logging
    - Correlation ID across the task lifecycle

    Metrics:
    - Analysis started
    - Analysis completed
    - Analysis failed
    - Celery retries
    - Analysis duration
    - Deployment decision distribution
    """

    task_id = self.request.id
    retry_count = self.request.retries

    # -----------------------------------------------------------------
    # Reuse the correlation ID supplied by the webhook.
    # Generate one for manually queued tasks.
    # -----------------------------------------------------------------

    correlation_id = correlation_id or str(uuid.uuid4())

    # -----------------------------------------------------------------
    # Metrics are shared through Redis between the API and worker.
    # -----------------------------------------------------------------

    metrics = MetricsService()

    # -----------------------------------------------------------------
    # Timer measures the complete task execution time.
    # -----------------------------------------------------------------

    timer = MetricsTimer()

    # -----------------------------------------------------------------
    # Count a logical analysis only once.
    #
    # Retries should NOT inflate "analyses.started".
    # -----------------------------------------------------------------

    if retry_count == 0:
        _safe_increment(
            metrics,
            MetricsService.ANALYSIS_STARTED,
        )

    # -----------------------------------------------------------------
    # Structured logger with correlation context.
    # -----------------------------------------------------------------

    log = logger.bind(
        correlation_id=correlation_id,
        task_id=task_id,
        repository_id=repository_id,
        pr_id=pr_id,
        tenant_id=tenant_id,
        webhook_event_id=webhook_event_id,
        retry_count=retry_count,
    )

    log.info(
        "celery_pr_analysis_started",
        max_retries=MAX_RETRIES,
    )

    db = SessionLocal()

    try:
        # -------------------------------------------------------------
        # Create AnalysisService with the same correlation ID.
        # -------------------------------------------------------------

        service = AnalysisService(
            db=db,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )

        # -------------------------------------------------------------
        # Execute asynchronous analysis.
        # -------------------------------------------------------------

        result = asyncio.run(
            service.analyze_and_comment_pr(
                repository_id=repository_id,
                pr_id=pr_id,
            )
        )

        # -------------------------------------------------------------
        # Mark webhook as successfully processed.
        #
        # This happens only after the complete analysis succeeds.
        # -------------------------------------------------------------

        if webhook_event_id is not None:
            webhook_event = (
                db.query(WebhookEvent)
                .filter(
                    WebhookEvent.id == webhook_event_id
                )
                .first()
            )

            if webhook_event:
                webhook_event.processed = 1
                webhook_event.error_message = None
                db.commit()

                log.info(
                    "webhook_event_marked_processed",
                    webhook_event_id=webhook_event.id,
                )

        # -------------------------------------------------------------
        # Record successful analysis metrics.
        # -------------------------------------------------------------

        _safe_increment(
            metrics,
            MetricsService.ANALYSIS_COMPLETED,
        )

        _safe_record_duration(
            metrics,
            timer.elapsed(),
        )

        # -------------------------------------------------------------
        # Record deployment decision distribution.
        #
        # RiskAnalysisResult currently exposes deployment_decision
        # as a dictionary, so handle that form safely.
        # -------------------------------------------------------------

        deployment_decision = getattr(
            result,
            "deployment_decision",
            None,
        )

        if isinstance(
            deployment_decision,
            dict,
        ):
            _safe_record_deployment_decision(
                metrics,
                deployment_decision.get("status"),
            )

        # -------------------------------------------------------------
        # Successful completion log.
        # -------------------------------------------------------------

        log.info(
            "celery_pr_analysis_completed",
            analysis_id=result.analysis_id,
            risk_score=result.risk_score,
            risk_level=result.risk_level,
            duration_seconds=round(
                timer.elapsed(),
                3,
            ),
        )

        return {
            "status": "success",
            "analysis_id": result.analysis_id,
            "pr_id": pr_id,
            "repository_id": repository_id,
            "tenant_id": tenant_id,
            "risk_score": result.risk_score,
            "risk_level": result.risk_level,
            "correlation_id": correlation_id,
        }

    except Exception as exc:
        current_retry = self.request.retries

        # -------------------------------------------------------------
        # Log the failure with full structured context.
        # -------------------------------------------------------------

        log.exception(
            "celery_pr_analysis_failed",
            error=str(exc),
            error_type=type(exc).__name__,
            current_retry=current_retry,
            max_retries=MAX_RETRIES,
            duration_seconds=round(
                timer.elapsed(),
                3,
            ),
        )

        # -------------------------------------------------------------
        # Retry while attempts remain.
        #
        # Backoff:
        #   retry 1 -> 10 seconds
        #   retry 2 -> 20 seconds
        #   retry 3 -> 40 seconds
        #
        # Maximum countdown is capped at 120 seconds.
        # -------------------------------------------------------------

        if current_retry < MAX_RETRIES:

            _safe_increment(
                metrics,
                MetricsService.CELERY_RETRIES,
            )

            countdown = min(
                2 ** current_retry * 10,
                120,
            )

            log.warning(
                "celery_pr_analysis_retry_scheduled",
                next_retry=current_retry + 1,
                countdown_seconds=countdown,
            )

            try:
                raise self.retry(
                    exc=exc,
                    countdown=countdown,
                    max_retries=MAX_RETRIES,
                )

            except MaxRetriesExceededError:
                # Defensive fallback.
                log.error(
                    "celery_pr_analysis_max_retries_exceeded",
                    current_retry=current_retry,
                )

        # -------------------------------------------------------------
        # Final failure.
        #
        # This block is reached only after all retries are exhausted.
        # -------------------------------------------------------------

        _safe_increment(
            metrics,
            MetricsService.ANALYSIS_FAILED,
        )

        _safe_record_duration(
            metrics,
            timer.elapsed(),
        )

        # -------------------------------------------------------------
        # Mark webhook as permanently failed.
        # -------------------------------------------------------------

        if webhook_event_id is not None:
            try:
                webhook_event = (
                    db.query(WebhookEvent)
                    .filter(
                        WebhookEvent.id == webhook_event_id
                    )
                    .first()
                )

                if webhook_event:
                    webhook_event.processed = -1
                    webhook_event.error_message = str(exc)
                    db.commit()

                    log.error(
                        "webhook_event_marked_failed",
                        webhook_event_id=webhook_event.id,
                    )

            except Exception as webhook_exc:
                db.rollback()

                log.exception(
                    "webhook_failure_state_update_failed",
                    error=str(webhook_exc),
                    error_type=type(webhook_exc).__name__,
                )

        # -------------------------------------------------------------
        # Final task failure.
        # -------------------------------------------------------------

        log.error(
            "celery_pr_analysis_final_failure",
            current_retry=current_retry,
        )

        raise

    finally:
        db.close()

        log.info(
            "celery_pr_analysis_task_finished",
            duration_seconds=round(
                timer.elapsed(),
                3,
            ),
        )