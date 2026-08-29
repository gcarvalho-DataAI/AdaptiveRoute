from __future__ import annotations

from dataclasses import replace
from typing import Any

from adaptiveroute.domain.models import RoutingPlan, RoutingScenario, Vehicle
from adaptiveroute.domain.serialization import plan_to_dict
from adaptiveroute.drivers.service import DriverService, driver_to_dict
from adaptiveroute.operations.models import OperationalRouteRecord
from adaptiveroute.operations.service import OperationalRouteService, route_to_dict
from adaptiveroute.scenarios.service import ScenarioService
from adaptiveroute.solvers.base import RoutingEngine


class DailyPlanningService:
    def __init__(
        self,
        *,
        driver_service: DriverService,
        scenario_service: ScenarioService,
        operational_route_service: OperationalRouteService,
        engine: RoutingEngine,
    ):
        self._driver_service = driver_service
        self._scenario_service = scenario_service
        self._operational_route_service = operational_route_service
        self._engine = engine

    def run_daily_planning(
        self,
        *,
        scenario_id: str = "demo-cvrp-8",
        route_prefix: str = "ROUTE",
        include_demo_drivers: bool = True,
    ) -> dict[str, Any]:
        scenario = self._scenario_service.get_scenario(scenario_id)
        if scenario is None and scenario_id == "demo-cvrp-8":
            scenario = self._scenario_service.seed_demo_scenario()
        if scenario is None:
            raise ValueError(f"Routing scenario not found: {scenario_id}")

        drivers = self._driver_service.list_drivers()
        if include_demo_drivers:
            drivers = self._driver_service.ensure_demo_drivers()
        available_drivers = [driver for driver in drivers if driver.status == "available"]
        if include_demo_drivers and not available_drivers:
            self._driver_service.release_demo_drivers_for_planning()
            drivers = self._driver_service.list_drivers()
            available_drivers = [driver for driver in drivers if driver.status == "available"]
        if not available_drivers:
            raise ValueError("No available drivers for planning.")

        planning_scenario = _scenario_with_driver_vehicles(scenario, available_drivers)
        result = self._engine.solve(planning_scenario)
        if result.plan is None:
            raise ValueError(f"Daily planning failed: {result.message}")
        if len(result.plan.routes) > len(available_drivers):
            raise ValueError("Solver returned more routes than available drivers.")

        routes = []
        for index, vehicle_route in enumerate(result.plan.routes, start=1):
            driver = available_drivers[index - 1]
            route_plan = RoutingPlan(
                scenario_id=result.plan.scenario_id,
                routes=(vehicle_route,),
                total_distance=vehicle_route.distance,
            )
            route = self._operational_route_service.create_route_from_plan(
                route_id=f"{route_prefix}-{index:03d}",
                driver_id=driver.id,
                scenario_id=result.plan.scenario_id,
                plan=plan_to_dict(route_plan),
                status="assigned",
                metadata={
                    "created_from": "daily_planning",
                    "driver": driver_to_dict(driver),
                    "solver_vehicle_id": vehicle_route.vehicle_id,
                },
            )
            self._driver_service.mark_on_route(driver.id)
            routes.append(route)

        return {
            "scenario_id": scenario.id,
            "solver_status": result.status.value,
            "solve_time_ms": result.solve_time_ms,
            "available_driver_count": len(available_drivers),
            "created_route_count": len(routes),
            "routes": [route_to_dict(route) for route in routes],
            "plan": plan_to_dict(result.plan),
        }


def _scenario_with_driver_vehicles(scenario: RoutingScenario, drivers: list) -> RoutingScenario:
    vehicles = tuple(Vehicle(id=driver.vehicle_id, capacity=driver.capacity) for driver in drivers)
    return replace(scenario, vehicles=vehicles)
