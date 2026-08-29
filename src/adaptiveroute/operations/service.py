from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any

from adaptiveroute.domain.serialization import plan_to_dict
from adaptiveroute.operations.models import OperationalRouteRecord, utc_now
from adaptiveroute.operations.repository import OperationalRouteRepository
from adaptiveroute.scenarios.service import ScenarioService
from adaptiveroute.solvers.base import RoutingEngine


class OperationalRouteService:
    def __init__(
        self,
        *,
        repository: OperationalRouteRepository,
        scenario_service: ScenarioService,
        engine: RoutingEngine,
    ):
        self._repository = repository
        self._scenario_service = scenario_service
        self._engine = engine

    def create_route(
        self,
        *,
        route_id: str,
        driver_id: str,
        scenario_id: str = "demo-cvrp-8",
        status: str = "assigned",
        metadata: dict[str, Any] | None = None,
    ) -> OperationalRouteRecord:
        scenario = self._scenario_service.get_scenario(scenario_id)
        if scenario is None and scenario_id == "demo-cvrp-8":
            scenario = self._scenario_service.seed_demo_scenario()
        if scenario is None:
            raise ValueError(f"Routing scenario not found: {scenario_id}")

        plan_result = self._engine.solve(scenario)
        if plan_result.plan is None:
            raise ValueError(f"Could not generate initial plan for route {route_id}: {plan_result.message}")

        now = utc_now()
        route = OperationalRouteRecord(
            id=route_id,
            driver_id=driver_id,
            scenario_id=scenario.id,
            current_plan=plan_to_dict(plan_result.plan),
            status=status,  # type: ignore[arg-type]
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )
        return self._repository.save_route(route)

    def create_route_from_plan(
        self,
        *,
        route_id: str,
        driver_id: str,
        scenario_id: str,
        plan: dict[str, Any],
        status: str = "assigned",
        metadata: dict[str, Any] | None = None,
    ) -> OperationalRouteRecord:
        now = utc_now()
        route = OperationalRouteRecord(
            id=route_id,
            driver_id=driver_id,
            scenario_id=scenario_id,
            current_plan=plan,
            status=status,  # type: ignore[arg-type]
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )
        return self._repository.save_route(route)

    def get_route(self, route_id: str) -> OperationalRouteRecord | None:
        return self._repository.get_route(route_id)

    def list_routes(self) -> list[OperationalRouteRecord]:
        return self._repository.list_routes()

    def list_routes_by_driver(self, driver_id: str) -> list[OperationalRouteRecord]:
        return self._repository.list_routes_by_driver(driver_id)

    def mark_driver_removed(self, driver_id: str, *, driver_snapshot: dict[str, Any]) -> int:
        return self._repository.mark_driver_removed(driver_id, driver_snapshot=driver_snapshot)

    def update_status(self, route_id: str, status: str) -> OperationalRouteRecord | None:
        return self._repository.update_status(route_id, status)

    def update_current_plan(
        self,
        route_id: str,
        plan: dict[str, Any],
        *,
        scenario_id: str | None = None,
    ) -> OperationalRouteRecord | None:
        route = self._repository.get_route(route_id)
        scoped_plan = _filter_plan_for_operational_route(plan, route_id=route_id, metadata=route.metadata if route else {})
        return self._repository.update_current_plan(route_id, scoped_plan, scenario_id=scenario_id)


def extract_route_id(text: str) -> str | None:
    for direct in re.finditer(r"\b[A-Za-z0-9_-]*ROUTE[A-Za-z0-9_-]*\b", text, flags=re.IGNORECASE):
        candidate = direct.group(0)
        if candidate.lower() != "route" and (any(char.isdigit() for char in candidate) or "-" in candidate or "_" in candidate):
            return candidate
    match = re.search(r"\b(?:rota|route)\s*#?\s*([A-Za-z0-9][A-Za-z0-9_-]*\d[A-Za-z0-9_-]*)\b", text, flags=re.IGNORECASE)
    return match.group(1) if match else None


def route_to_dict(route: OperationalRouteRecord) -> dict[str, Any]:
    return _redact_sensitive_route_payload(asdict(route))


def _redact_sensitive_route_payload(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"password_hash", "temporary_password", "password"}:
                continue
            redacted[key] = _redact_sensitive_route_payload(item)
        return redacted
    if isinstance(value, list):
        return [_redact_sensitive_route_payload(item) for item in value]
    return value


def _filter_plan_for_operational_route(plan: dict[str, Any], *, route_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
    routes = plan.get("routes") if isinstance(plan.get("routes"), list) else []
    if not routes:
        return plan

    vehicle_ids = {
        value
        for value in (
            metadata.get("solver_vehicle_id"),
            metadata.get("vehicle_id"),
            (metadata.get("driver") or {}).get("vehicle_id") if isinstance(metadata.get("driver"), dict) else None,
            _infer_vehicle_id_from_route_id(route_id, routes),
        )
        if value
    }
    filtered_routes = [route for route in routes if route.get("vehicle_id") in vehicle_ids]
    if not filtered_routes:
        return plan
    return {
        **plan,
        "routes": filtered_routes,
        "total_distance": round(sum(float(route.get("distance") or 0) for route in filtered_routes), 2),
    }


def _infer_vehicle_id_from_route_id(route_id: str, routes: list[dict[str, Any]]) -> str | None:
    match = re.search(r"(\d+)$", route_id or "")
    if not match:
        return None
    index = int(match.group(1)) - 1
    if 0 <= index < len(routes):
        return routes[index].get("vehicle_id")
    return f"V{int(match.group(1))}"
