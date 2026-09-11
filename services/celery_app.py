from celery import Celery

from config import get_settings


settings = get_settings()


celery_app = Celery(
    "deployguard",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["services.tasks"],
)


celery_app.conf.update(
    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # ------------------------------------------------------------------
    # Timezone
    # ------------------------------------------------------------------
    timezone="UTC",
    enable_utc=True,

    # ------------------------------------------------------------------
    # Broker reliability
    # ------------------------------------------------------------------
    broker_connection_retry_on_startup=True,

    # Redis visibility timeout.
    # A task that disappears from a worker unexpectedly can become
    # available again after this period.
    broker_transport_options={
        "visibility_timeout": 3600,
    },

    # ------------------------------------------------------------------
    # Task acknowledgement / worker reliability
    # ------------------------------------------------------------------
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Prevent one worker from reserving a large batch of tasks.
    worker_prefetch_multiplier=1,

    # ------------------------------------------------------------------
    # Task observability
    # ------------------------------------------------------------------
    task_track_started=True,

    # Keep Celery results for a reasonable period.
    result_expires=86400,

    # ------------------------------------------------------------------
    # Worker behavior
    # ------------------------------------------------------------------
    worker_send_task_events=True,

    # ------------------------------------------------------------------
    # Default task execution limits
    #
    # These are safety defaults. Individual tasks can define more
    # specific limits in their decorators.
    # ------------------------------------------------------------------
    task_soft_time_limit=300,
    task_time_limit=360,

    # ------------------------------------------------------------------
    # Retry behavior
    # ------------------------------------------------------------------
    task_default_retry_delay=10,
    task_max_retries=3,
)