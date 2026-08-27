from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.domain.events import EventType, OperationalEvent
from adaptiveroute.services.comparison import compare_plans, comparison_to_dict
from adaptiveroute.services.mutations import apply_event
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine


def test_compare_plans_reports_removed_customer() -> None:
    engine = PyomoHighsEngine()
    scenario = build_demo_scenario()
    base = engine.solve(scenario)
    assert base.plan is not None

    event = OperationalEvent(
        type=EventType.CUSTOMER_UNAVAILABLE,
        payload={"customer_id": "C3"},
        description="Customer C3 is unavailable.",
    )
    mutated, _ = apply_event(scenario, event)
    replanned = engine.solve(mutated)
    assert replanned.plan is not None

    comparison = compare_plans(scenario, base.plan, mutated, replanned.plan)

    assert "C3" in comparison.removed_customers
    assert comparison_to_dict(comparison)["removed_customers"] == ["C3"]


def test_compare_plans_reports_blocked_arc_context() -> None:
    engine = PyomoHighsEngine()
    scenario = build_demo_scenario()
    base = engine.solve(scenario)
    assert base.plan is not None

    event = OperationalEvent(
        type=EventType.BLOCK_ARC,
        payload={"from_node": "C7", "to_node": "C6", "bidirectional": True},
        description="Accident between C7 and C6.",
    )
    mutated, _ = apply_event(scenario, event)
    replanned = engine.solve(mutated)
    assert replanned.plan is not None

    comparison = compare_plans(scenario, base.plan, mutated, replanned.plan)

    assert ("C7", "C6") in comparison.blocked_arcs_after
    assert ("C7", "C6") in comparison.removed_edges or ("C6", "C7") in comparison.removed_edges
