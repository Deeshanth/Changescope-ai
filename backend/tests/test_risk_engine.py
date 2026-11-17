from app.services.risk_engine import ComponentRiskInput, RiskEngine


def test_risk_engine_is_strictly_deterministic() -> None:
    engine = RiskEngine()
    item = ComponentRiskInput(
        node_id=1,
        node_key="app.billing.charge",
        node_type="function",
        is_test=False,
        hop_distance=0,
        fan_in=6,
        complexity=8,
        loc=40,
        changed_lines=10,
        has_heuristic_path=False,
        max_repo_fan_in=10,
    )

    r1 = engine.calculate_component_risk(item)
    r2 = engine.calculate_component_risk(item)
    assert r1.risk_score == r2.risk_score
    assert r1.factors == r2.factors
    assert r1.risk_level in {"MEDIUM", "HIGH", "CRITICAL"}


def test_risk_engine_proximity_decay_and_test_dampening() -> None:
    engine = RiskEngine()
    direct_prod = engine.calculate_component_risk(
        ComponentRiskInput(1, "a", "function", False, 0, 2, 2, 10, 5, False, 10)
    )
    hop2_prod = engine.calculate_component_risk(
        ComponentRiskInput(2, "b", "function", False, 2, 2, 2, 10, 0, False, 10)
    )
    direct_test = engine.calculate_component_risk(
        ComponentRiskInput(3, "test_a", "function", True, 0, 2, 2, 10, 5, False, 10)
    )

    assert direct_prod.risk_score > hop2_prod.risk_score
    assert direct_prod.risk_score > direct_test.risk_score
    assert direct_test.factors["test_dampening_factor"] == 0.35
