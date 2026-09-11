from services.metrics import MetricsService


class FakeRedisPipeline:
    def __init__(self, redis):
        self.redis = redis
        self.operations = []

    def hincrby(self, key, field, amount):
        self.operations.append(("hincrby", key, field, amount))
        return self

    def hincrbyfloat(self, key, field, amount):
        self.operations.append(("hincrbyfloat", key, field, amount))
        return self

    def execute(self):
        results = []

        for operation in self.operations:
            name = operation[0]

            if name == "hincrby":
                _, key, field, amount = operation
                result = self.redis.hincrby(key, field, amount)
                results.append(result)

            elif name == "hincrbyfloat":
                _, key, field, amount = operation
                result = self.redis.hincrbyfloat(key, field, amount)
                results.append(result)

        self.operations.clear()
        return results


class FakeRedis:
    def __init__(self):
        self.hashes = {}

    def hincrby(self, key, field, amount):
        bucket = self.hashes.setdefault(key, {})
        bucket[field] = int(bucket.get(field, 0)) + int(amount)
        return bucket[field]

    def hincrbyfloat(self, key, field, amount):
        bucket = self.hashes.setdefault(key, {})
        bucket[field] = float(bucket.get(field, 0.0)) + float(amount)
        return bucket[field]

    def hget(self, key, field):
        bucket = self.hashes.get(key, {})
        return bucket.get(field)

    def hset(self, key, field, value):
        bucket = self.hashes.setdefault(key, {})
        bucket[field] = value
        return 1

    def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    def delete(self, key):
        self.hashes.pop(key, None)

    def pipeline(self):
        return FakeRedisPipeline(self)


def test_metrics_snapshot(monkeypatch):
    fake_redis = FakeRedis()

    monkeypatch.setattr(
        "services.metrics.redis.Redis.from_url",
        lambda *args, **kwargs: fake_redis,
    )

    metrics = MetricsService()

    metrics.increment(MetricsService.ANALYSIS_STARTED)
    metrics.increment(MetricsService.ANALYSIS_STARTED)
    metrics.increment(MetricsService.ANALYSIS_COMPLETED)

    metrics.record_duration(10.0)
    metrics.record_duration(20.0)

    metrics.record_deployment_decision("safe")
    metrics.record_deployment_decision("review_required")
    metrics.record_deployment_decision("blocked")

    snapshot = metrics.snapshot()

    assert snapshot["analyses"]["started"] == 2
    assert snapshot["analyses"]["completed"] == 1
    assert snapshot["analyses"]["failed"] == 0

    assert snapshot["duration"]["count"] == 2
    assert snapshot["duration"]["total_seconds"] == 30.0
    assert snapshot["duration"]["average_seconds"] == 15.0
    assert snapshot["duration"]["max_seconds"] == 20.0

    assert snapshot["deployment_decisions"]["safe"] == 1
    assert snapshot["deployment_decisions"]["review_required"] == 1
    assert snapshot["deployment_decisions"]["blocked"] == 1

    assert snapshot["celery"]["retries"] == 0


def test_metrics_ignores_unknown_deployment_decision(monkeypatch):
    fake_redis = FakeRedis()

    monkeypatch.setattr(
        "services.metrics.redis.Redis.from_url",
        lambda *args, **kwargs: fake_redis,
    )

    metrics = MetricsService()

    metrics.record_deployment_decision("something_unknown")

    snapshot = metrics.snapshot()

    assert snapshot["deployment_decisions"]["safe"] == 0
    assert snapshot["deployment_decisions"]["review_recommended"] == 0
    assert snapshot["deployment_decisions"]["review_required"] == 0
    assert snapshot["deployment_decisions"]["blocked"] == 0


def test_metrics_reset(monkeypatch):
    fake_redis = FakeRedis()

    monkeypatch.setattr(
        "services.metrics.redis.Redis.from_url",
        lambda *args, **kwargs: fake_redis,
    )

    metrics = MetricsService()

    metrics.increment(MetricsService.ANALYSIS_STARTED)
    metrics.record_duration(25.0)
    metrics.record_deployment_decision("safe")

    before_reset = metrics.snapshot()

    assert before_reset["analyses"]["started"] == 1
    assert before_reset["duration"]["count"] == 1
    assert before_reset["deployment_decisions"]["safe"] == 1

    metrics.reset()

    after_reset = metrics.snapshot()

    assert after_reset["analyses"]["started"] == 0
    assert after_reset["duration"]["count"] == 0
    assert after_reset["duration"]["total_seconds"] == 0.0
    assert after_reset["duration"]["max_seconds"] == 0.0
    assert after_reset["deployment_decisions"]["safe"] == 0