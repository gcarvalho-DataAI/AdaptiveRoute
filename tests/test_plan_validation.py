from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.domain.models import RoutingPlan, VehicleRoute
from adaptiveroute.services.validation import validate_plan


def test_validation_detects_missing_customer() -> None:
    scenario = build_demo_scenario()
    plan = RoutingPlan(
        scenario_id=scenario.id,
        routes=(
            VehicleRoute(vehicle_id="V1", stops=("D0", "C1", "D0"), load=4, distance=10.0),
        ),
        total_distance=10.0,
    )

    validation = validate_plan(scenario, plan)

    assert not validation.passed
    assert "missing_customer" in {violation.code for violation in validation.violations}


def test_validation_detects_duplicate_customer() -> None:
    scenario = build_demo_scenario()
    plan = RoutingPlan(
        scenario_id=scenario.id,
        routes=(
            VehicleRoute(vehicle_id="V1", stops=("D0", "C1", "D0"), load=4, distance=10.0),
            VehicleRoute(vehicle_id="V2", stops=("D0", "C1", "D0"), load=4, distance=10.0),
        ),
        total_distance=20.0,
    )

    validation = validate_plan(scenario, plan)

    assert not validation.passed
    assert "duplicate_customer" in {violation.code for violation in validation.violations}
