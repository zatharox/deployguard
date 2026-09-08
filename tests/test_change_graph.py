from engine.change_graph import ChangeGraphAnalyzer


def test_small_change_has_narrow_blast_radius():
    analyzer = ChangeGraphAnalyzer()

    result = analyzer.analyze(
        [
            "utils/helper.py",
        ]
    )

    assert result.changed_files == ["utils/helper.py"]
    assert result.components == ["utils"]
    assert result.critical_areas == []
    assert result.blast_radius_level == "narrow"
    assert result.confidence == "low"


def test_cross_component_change_is_detected():
    analyzer = ChangeGraphAnalyzer()

    result = analyzer.analyze(
        [
            "api/users.py",
            "services/user_service.py",
            "database/users.py",
        ]
    )

    assert set(result.components) == {
        "api",
        "database",
        "services",
    }

    assert "api" in result.critical_areas
    assert "database" in result.critical_areas
    assert result.blast_radius_score >= 4.0
    assert result.blast_radius_level in {
        "moderate",
        "broad",
    }


def test_critical_areas_are_detected():
    analyzer = ChangeGraphAnalyzer()

    result = analyzer.analyze(
        [
            "auth/token.py",
            "payment/service.py",
            "db/repository.py",
        ]
    )

    assert set(result.critical_areas) == {
        "authentication",
        "database",
        "payment",
    }

    assert result.blast_radius_level == "broad"


def test_duplicate_paths_are_removed():
    analyzer = ChangeGraphAnalyzer()

    result = analyzer.analyze(
        [
            "./api/users.py",
            "api/users.py",
            "api\\users.py",
        ]
    )

    assert result.changed_files == [
        "api/users.py",
    ]


def test_empty_changes_are_safe():
    analyzer = ChangeGraphAnalyzer()

    result = analyzer.analyze([])

    assert result.changed_files == []
    assert result.components == []
    assert result.critical_areas == []
    assert result.blast_radius_score == 0.0
    assert result.blast_radius_level == "narrow"


def test_graph_contains_expected_relationships():
    analyzer = ChangeGraphAnalyzer()

    result = analyzer.analyze(
        [
            "auth/token.py",
        ]
    )

    relationships = {edge.relationship for edge in result.edges}

    assert "belongs_to" in relationships
    assert "affects" in relationships
