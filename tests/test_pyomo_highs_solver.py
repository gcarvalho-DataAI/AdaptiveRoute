from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.domain.models import SolveStatus
from adaptiveroute.services.validation import validate_plan
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine


def test_demo_scenario_solves_to_valid_plan() -> None:
    scenario = build_demo_scenario()
    result = PyomoHighsEngine().solve(scenario)

    assert result.status == SolveStatus.OPTIMAL
    assert result.plan is not None
    assert result.plan.total_distance > 0

    validation = validate_plan(scenario, result.plan)
    assert validation.passed, [violation.message for violation in validation.violations]


def test_solver_uses_multiple_routes_within_capacity() -> None:
    scenario = build_demo_scenario()
    result = PyomoHighsEngine().solve(scenario)

    assert result.plan is not None
    assert len(result.plan.routes) <= len(scenario.vehicles)
    assert sum(route.load for route in result.plan.routes) == sum(customer.demand for customer in scenario.active_customers)

