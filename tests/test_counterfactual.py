from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.services.counterfactual import analyze_counterfactual, build_plan_from_route_sequences
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine


def test_build_plan_from_route_sequences_adds_depot_boundaries() -> None:
    scenario = build_demo_scenario()
    plan = build_plan_from_route_sequences(scenario, {"V1": ["C1", "C2"]})

    assert plan.routes[0].stops[0] == "D0"
    assert plan.routes[0].stops[-1] == "D0"


def test_counterfactual_detects_capacity_violation() -> None:
    scenario = build_demo_scenario()
    reference = PyomoHighsEngine().solve(scenario)
    assert reference.plan is not None

    overloaded = {
        "V1": ["D0", "C1", "C2", "C3", "C4", "C5", "D0"],
        "V2": ["D0", "C6", "C7", "C8", "D0"],
    }
    analysis = analyze_counterfactual(scenario, reference.plan, overloaded)

    assert not analysis.validation.passed
    assert "capacity_violation" in {violation.code for violation in analysis.validation.violations}
    assert analysis.candidate_total_distance > 0

