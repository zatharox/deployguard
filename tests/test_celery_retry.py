from types import SimpleNamespace

from services import tasks


class FakeQuery:
    def __init__(self, webhook_event):
        self.webhook_event = webhook_event

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.webhook_event


class FakeDB:
    def __init__(self):
        self.webhook_event = SimpleNamespace(
            id=123,
            processed=0,
            error_message=None,
        )
        self.commit_count = 0
        self.rollback_count = 0

    def query(self, *args, **kwargs):
        return FakeQuery(self.webhook_event)

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rollback_count += 1

    def close(self):
        pass


def test_celery_task_retries_then_succeeds(monkeypatch):
    fake_db = FakeDB()
    call_count = {"value": 0}
    expected_correlation_id = "test-correlation-id"

    class FakeAnalysisService:
        def __init__(
            self,
            db,
            tenant_id,
            correlation_id=None,
        ):
            assert db is fake_db
            assert tenant_id == 42
            assert correlation_id == expected_correlation_id

        async def analyze_and_comment_pr(
            self,
            repository_id,
            pr_id,
        ):
            call_count["value"] += 1

            if call_count["value"] == 1:
                raise RuntimeError("temporary analysis failure")

            return SimpleNamespace(
                analysis_id=999,
                risk_score=2.1,
                risk_level="low",
            )

    monkeypatch.setattr(
        tasks,
        "SessionLocal",
        lambda: fake_db,
    )

    monkeypatch.setattr(
        tasks,
        "AnalysisService",
        FakeAnalysisService,
    )

    result = tasks.analyze_pr_task.apply(
        args=(
            "demo-repo",
            999,
            42,
            123,
            expected_correlation_id,
        ),
    )

    assert result.successful()

    assert result.result["status"] == "success"
    assert result.result["analysis_id"] == 999
    assert result.result["pr_id"] == 999
    assert result.result["repository_id"] == "demo-repo"
    assert result.result["tenant_id"] == 42
    assert result.result["risk_score"] == 2.1
    assert result.result["risk_level"] == "low"
    assert result.result["correlation_id"] == expected_correlation_id

    assert call_count["value"] == 2

    assert fake_db.webhook_event.processed == 1
    assert fake_db.webhook_event.error_message is None

    assert fake_db.commit_count >= 1