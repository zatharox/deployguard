from engine.deployment_policy import DeploymentPolicy


POLICY_VERSION = "deployment-policy-v1"


def test_critical_risk_blocks_deployment():
    policy = DeploymentPolicy()

    decision = policy.evaluate(
        risk_level="critical",
        risk_score=9.5,
        change_graph={},
    )

    assert decision.status == "blocked"
    assert decision.label == "DEPLOYMENT BLOCKED"
    assert decision.blocking is True
    assert "Critical risk detected" in decision.reason
    assert decision.policy_version == POLICY_VERSION


def test_high_risk_with_broad_blast_radius_blocks_deployment():
    policy = DeploymentPolicy()

    decision = policy.evaluate(
        risk_level="high",
        risk_score=8.0,
        change_graph={
            "blast_radius": {
                "score": 9.0,
                "level": "broad",
                "confidence": "high",
            }
        },
    )

    assert decision.status == "blocked"
    assert decision.label == "DEPLOYMENT BLOCKED"
    assert decision.blocking is True
    assert "broad structural blast radius" in decision.reason
    assert decision.policy_version == POLICY_VERSION


def test_high_risk_requires_review():
    policy = DeploymentPolicy()

    decision = policy.evaluate(
        risk_level="high",
        risk_score=7.0,
        change_graph={
            "blast_radius": {
                "score": 4.0,
                "level": "narrow",
                "confidence": "high",
            }
        },
    )

    assert decision.status == "review_required"
    assert decision.label == "REVIEW REQUIRED"
    assert decision.blocking is False
    assert "High deployment risk detected" in decision.reason
    assert decision.policy_version == POLICY_VERSION


def test_critical_area_requires_review():
    policy = DeploymentPolicy()

    decision = policy.evaluate(
        risk_level="low",
        risk_score=2.0,
        change_graph={
            "critical_areas": ["authentication"],
            "blast_radius": {
                "score": 2.5,
                "level": "narrow",
                "confidence": "high",
            },
        },
    )

    assert decision.status == "review_required"
    assert decision.label == "REVIEW REQUIRED"
    assert decision.blocking is False
    assert "Critical service areas are affected" in decision.reason
    assert decision.policy_version == POLICY_VERSION


def test_broad_blast_radius_requires_review():
    policy = DeploymentPolicy()

    decision = policy.evaluate(
        risk_level="low",
        risk_score=2.0,
        change_graph={
            "blast_radius": {
                "score": 7.5,
                "level": "broad",
                "confidence": "high",
            }
        },
    )

    assert decision.status == "review_required"
    assert decision.label == "REVIEW REQUIRED"
    assert decision.blocking is False
    assert "broad structural blast radius" in decision.reason
    assert decision.policy_version == POLICY_VERSION


def test_medium_risk_recommends_review():
    policy = DeploymentPolicy()

    decision = policy.evaluate(
        risk_level="medium",
        risk_score=5.0,
        change_graph={
            "blast_radius": {
                "score": 4.0,
                "level": "narrow",
                "confidence": "high",
            }
        },
    )

    assert decision.status == "review_recommended"
    assert decision.label == "REVIEW RECOMMENDED"
    assert decision.blocking is False
    assert "Moderate deployment risk detected" in decision.reason
    assert decision.policy_version == POLICY_VERSION


def test_low_confidence_recommends_review():
    policy = DeploymentPolicy()

    decision = policy.evaluate(
        risk_level="low",
        risk_score=1.5,
        change_graph={
            "blast_radius": {
                "score": 1.5,
                "level": "narrow",
                "confidence": "low",
            }
        },
    )

    assert decision.status == "review_recommended"
    assert decision.label == "REVIEW RECOMMENDED"
    assert decision.blocking is False
    assert "Risk analysis confidence is low" in decision.reason
    assert decision.policy_version == POLICY_VERSION


def test_low_risk_narrow_high_confidence_is_safe():
    policy = DeploymentPolicy()

    decision = policy.evaluate(
        risk_level="low",
        risk_score=1.6,
        change_graph={
            "critical_areas": [],
            "blast_radius": {
                "score": 1.5,
                "level": "narrow",
                "confidence": "medium",
            },
        },
    )

    assert decision.status == "safe"
    assert decision.label == "SAFE TO DEPLOY"
    assert decision.blocking is False
    assert "No deployment-blocking policy violations" in decision.reason
    assert decision.policy_version == POLICY_VERSION


def test_empty_change_graph_with_low_risk_is_safe():
    policy = DeploymentPolicy()

    decision = policy.evaluate(
        risk_level="low",
        risk_score=1.0,
        change_graph=None,
    )

    assert decision.status == "safe"
    assert decision.label == "SAFE TO DEPLOY"
    assert decision.blocking is False
    assert decision.policy_version == POLICY_VERSION


def test_policy_precedence_critical_area_over_low_risk():
    policy = DeploymentPolicy()

    decision = policy.evaluate(
        risk_level="low",
        risk_score=1.0,
        change_graph={
            "critical_areas": ["database"],
            "blast_radius": {
                "score": 1.0,
                "level": "narrow",
                "confidence": "high",
            },
        },
    )

    assert decision.status == "review_required"
    assert decision.label == "REVIEW REQUIRED"
    assert decision.blocking is False


def test_policy_precedence_high_broad_over_critical_area():
    policy = DeploymentPolicy()

    decision = policy.evaluate(
        risk_level="high",
        risk_score=8.0,
        change_graph={
            "critical_areas": ["database"],
            "blast_radius": {
                "score": 9.0,
                "level": "broad",
                "confidence": "high",
            },
        },
    )

    assert decision.status == "blocked"
    assert decision.label == "DEPLOYMENT BLOCKED"
    assert decision.blocking is True


def test_policy_is_case_insensitive():
    policy = DeploymentPolicy()

    decision = policy.evaluate(
        risk_level="HIGH",
        risk_score=7.5,
        change_graph={
            "blast_radius": {
                "score": 4.0,
                "level": "NARROW",
                "confidence": "HIGH",
            }
        },
    )

    assert decision.status == "review_required"
    assert decision.label == "REVIEW REQUIRED"


def test_decision_to_dict_contains_expected_fields():
    policy = DeploymentPolicy()

    decision = policy.evaluate(
        risk_level="low",
        risk_score=1.0,
        change_graph={},
    )

    data = decision.to_dict()

    assert data == {
        "status": "safe",
        "label": "SAFE TO DEPLOY",
        "reason": (
            "No deployment-blocking policy violations "
            "were detected. Standard review applies."
        ),
        "blocking": False,
        "policy_version": POLICY_VERSION,
    }