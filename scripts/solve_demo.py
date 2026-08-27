from __future__ import annotations

from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.services.validation import validate_plan
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine


def main() -> int:
    scenario = build_demo_scenario()
    result = PyomoHighsEngine().solve(scenario)

    print(f"Scenario: {scenario.id}")
    print(f"Status: {result.status}")
    if result.solve_time_ms is not None:
        print(f"Solve time: {result.solve_time_ms:.1f} ms")
    if result.message:
        print(f"Message: {result.message}")

    if result.plan is None:
        return 1

    validation = validate_plan(scenario, result.plan)
    print(f"Total distance: {result.plan.total_distance:.2f}")
    print()

    for route in result.plan.routes:
        vehicle = next(v for v in scenario.vehicles if v.id == route.vehicle_id)
        print(f"{route.vehicle_id}: {' -> '.join(route.stops)}")
        print(f"  Load: {route.load} / {vehicle.capacity}")
        print(f"  Distance: {route.distance:.2f}")

    print()
    print(f"Validation: {'passed' if validation.passed else 'failed'}")
    for violation in validation.violations:
        print(f"- {violation.code}: {violation.message}")

    return 0 if validation.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

