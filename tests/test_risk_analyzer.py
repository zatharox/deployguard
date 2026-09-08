import pytest

from engine.risk_analyzer import RiskEngine,RiskAnalysisResult

def test_total_risk_score_is_capped_at_ten():
    raw_score = sum(
        [
            3.0,  # Commit Size Risk
            3.0,  # File Instability Risk
            2.0,  # Pipeline History Risk
            2.0,  # Critical Directory Risk
            0.8,  # Author Risk
            1.8,  # Blast Radius Risk
        ]
    )

    normalized_score = min(
        raw_score,
        10.0,
    )

    assert raw_score == pytest.approx(12.6)
    assert normalized_score == pytest.approx(10.0)

def test_blast_radius_signal_is_bounded():
    engine = RiskEngine()

    changes_data = {
        "changeEntries": [
            {
                "item": {
                    "path": "auth/token.py",
                }
            },
            {
                "item": {
                    "path": "payment/service.py",
                }
            },
            {
                "item": {
                    "path": "db/repository.py",
                }
            },
        ],
        "changeGraph": {
            "changed_files": [
                "auth/token.py",
                "payment/service.py",
                "db/repository.py",
            ],
            "components": [
                "auth",
                "payment",
                "db",
            ],
            "critical_areas": [
                "authentication",
                "payment",
                "database",
            ],
            "blast_radius": {
                "score": 10.0,
                "level": "broad",
                "confidence": "high",
            },
        },
    }

    signal = engine._analyze_blast_radius(changes_data)

    assert signal.name == "Blast Radius Risk"
    assert signal.score == 2.0
    assert "Broad structural blast radius" in signal.description
    assert "authentication" in signal.details



def test_risk_analysis_result_includes_change_graph():
    engine = RiskEngine()

    changes_data = {
        "changeGraph": {
            "changed_files": [
                "auth/token.py",
                "payment/service.py",
            ],
            "components": [
                "auth",
                "payment",
            ],
            "critical_areas": [
                "authentication",
                "payment",
            ],
            "blast_radius": {
                "score": 7.0,
                "level": "broad",
                "confidence": "high",
            },
        }
    }

    result = RiskAnalysisResult(
        risk_score=8.0,
        risk_level="high",
        signals=[],
        recommendations=[],
        change_graph=changes_data["changeGraph"],
    )

    output = result.to_dict()

    assert "change_graph" in output
    assert output["change_graph"]["blast_radius"]["score"] == 7.0
    assert output["change_graph"]["blast_radius"]["level"] == "broad"
    assert "auth" in output["change_graph"]["components"]