import time
from typing import Any, Dict

import redis

from config import get_settings


class MetricsService:
    """
    Redis-backed operational metrics for DeployGuard.

    Metrics are shared between the FastAPI application and Celery
    workers because both processes write to the same Redis instance.
    """

    KEY = "deployguard:metrics"

    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_COMPLETED = "analysis_completed"
    ANALYSIS_FAILED = "analysis_failed"
    CELERY_RETRIES = "celery_retries"

    DEPLOYMENT_SAFE = "deployment_safe"
    DEPLOYMENT_REVIEW_RECOMMENDED = "deployment_review_recommended"
    DEPLOYMENT_REVIEW_REQUIRED = "deployment_review_required"
    DEPLOYMENT_BLOCKED = "deployment_blocked"

    ANALYSIS_DURATION_COUNT = "analysis_duration_count"
    ANALYSIS_DURATION_TOTAL = "analysis_duration_total"
    ANALYSIS_DURATION_MAX = "analysis_duration_max"

    def __init__(self) -> None:
        settings = get_settings()

        self.redis = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )

    def increment(
        self,
        metric: str,
        amount: int = 1,
    ) -> None:
        """Increment a counter."""

        self.redis.hincrby(
            self.KEY,
            metric,
            amount,
        )

    def record_duration(self, duration_seconds: float) -> None:
        duration = max(float(duration_seconds), 0.0)

        pipeline = self.redis.pipeline()

        pipeline.hincrby(
            self.KEY,
            self.ANALYSIS_DURATION_COUNT,
            1,
        )

        pipeline.hincrbyfloat(
            self.KEY,
            self.ANALYSIS_DURATION_TOTAL,
            duration,
        )

        pipeline.execute()

        current_max = float(
            self.redis.hget(
                self.KEY,
                self.ANALYSIS_DURATION_MAX,
            )
            or 0.0
        )

        if duration > current_max:
            self.redis.hset(
                self.KEY,
                self.ANALYSIS_DURATION_MAX,
                duration,
            )

            
    def record_deployment_decision(
        self,
        status: str | None,
    ) -> None:
        """Record deployment-policy decision distribution."""

        normalized = str(
            status or ""
        ).strip().lower()

        mapping = {
            "safe": self.DEPLOYMENT_SAFE,
            "review_recommended": (
                self.DEPLOYMENT_REVIEW_RECOMMENDED
            ),
            "review_required": (
                self.DEPLOYMENT_REVIEW_REQUIRED
            ),
            "blocked": self.DEPLOYMENT_BLOCKED,
        }

        metric = mapping.get(normalized)

        if metric:
            self.increment(metric)

    def snapshot(self) -> Dict[str, Any]:
        data = self.redis.hgetall(self.KEY)

        started = int(float(data.get(self.ANALYSIS_STARTED, 0)))
        completed = int(float(data.get(self.ANALYSIS_COMPLETED, 0)))
        failed = int(float(data.get(self.ANALYSIS_FAILED, 0)))
        retries = int(float(data.get(self.CELERY_RETRIES, 0)))

        duration_count = int(
            float(data.get(self.ANALYSIS_DURATION_COUNT, 0))
        )
        duration_total = float(
            data.get(self.ANALYSIS_DURATION_TOTAL, 0.0)
        )
        duration_max = float(
            data.get(self.ANALYSIS_DURATION_MAX, 0.0)
        )

        average_duration = (
            duration_total / duration_count
            if duration_count > 0
            else 0.0
        )

        return {
            "analyses": {
                "started": started,
                "completed": completed,
                "failed": failed,
            },
            "duration": {
                "count": duration_count,
                "total_seconds": duration_total,
                "average_seconds": average_duration,
                "max_seconds": duration_max,
            },
            "celery": {
                "retries": retries,
            },
            "deployment_decisions": {
                "safe": int(
                    float(data.get(self.DEPLOYMENT_SAFE, 0))
                ),
                "review_recommended": int(
                    float(
                        data.get(
                            self.DEPLOYMENT_REVIEW_RECOMMENDED,
                            0,
                        )
                    )
                ),
                "review_required": int(
                    float(
                        data.get(
                            self.DEPLOYMENT_REVIEW_REQUIRED,
                            0,
                        )
                    )
                ),
                "blocked": int(
                    float(data.get(self.DEPLOYMENT_BLOCKED, 0))
                ),
            },
        }
    def reset(self) -> None:
        """
        Reset metrics.

        Intended for development/testing only.
        """

        self.redis.delete(self.KEY)


class MetricsTimer:
    """Small helper for measuring elapsed time."""

    def __init__(self) -> None:
        self.started_at = time.monotonic()

    def elapsed(self) -> float:
        return time.monotonic() - self.started_at