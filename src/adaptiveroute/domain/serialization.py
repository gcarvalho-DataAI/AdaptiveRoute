from __future__ import annotations

from typing import Any

from adaptiveroute.domain.events import OperationalEvent
from adaptiveroute.domain.models import (
    Customer,
    Depot,
    RoutingPlan,
    RoutingScenario,
    ValidationResult,
    Vehicle,
    VehicleRoute,
)


def depot_to_dict(depot: Depot) -> dict[str, Any]:
    return {"id": depot.id, "x": depot.x, "y": depot.y}


def customer_to_dict(customer: Customer) -> dict[str, Any]:
    return {
        "id": customer.id,
        "x": customer.x,
        "y": customer.y,
        "demand": customer.demand,
        "required": customer.required,
        "priority": customer.priority,
        "active": customer.active,
    }


def vehicle_to_dict(vehicle: Vehicle) -> dict[str, Any]:
    return {"id": vehicle.id, "capacity": vehicle.capacity}


def scenario_to_dict(scenario: RoutingScenario) -> dict[str, Any]:
    return {
        "id": scenario.id,
        "depot": depot_to_dict(scenario.depot),
        "customers": [customer_to_dict(customer) for customer in scenario.customers],
        "vehicles": [vehicle_to_dict(vehicle) for vehicle in scenario.vehicles],
        "distance_matrix": [
            {"from": origin, "to": destination, "distance": distance}
            for (origin, destination), distance in sorted(scenario.distance_matrix.items())
        ],
        "blocked_arcs": [{"from": origin, "to": destination} for origin, destination in sorted(scenario.blocked_arcs)],
    }


def scenario_from_dict(payload: dict[str, Any]) -> RoutingScenario:
    depot_payload = payload["depot"]
    depot = Depot(
        id=str(depot_payload["id"]),
        x=float(depot_payload["x"]),
        y=float(depot_payload["y"]),
    )
    customers = tuple(
        Customer(
            id=str(customer["id"]),
            x=float(customer["x"]),
            y=float(customer["y"]),
            demand=int(customer["demand"]),
            required=bool(customer.get("required", True)),
            priority=int(customer.get("priority", 1)),
            active=bool(customer.get("active", True)),
        )
        for customer in payload.get("customers", [])
    )
    vehicles = tuple(
        Vehicle(id=str(vehicle["id"]), capacity=int(vehicle["capacity"]))
        for vehicle in payload.get("vehicles", [])
    )
    distance_matrix = {
        (str(item["from"]), str(item["to"])): float(item["distance"])
        for item in payload.get("distance_matrix", [])
    }
    blocked_arcs = frozenset(
        (str(item["from"]), str(item["to"]))
        for item in payload.get("blocked_arcs", [])
    )
    return RoutingScenario(
        id=str(payload["id"]),
        depot=depot,
        customers=customers,
        vehicles=vehicles,
        distance_matrix=distance_matrix,
        blocked_arcs=blocked_arcs,
    )


def vehicle_route_to_dict(route: VehicleRoute) -> dict[str, Any]:
    return {
        "vehicle_id": route.vehicle_id,
        "stops": list(route.stops),
        "load": route.load,
        "distance": route.distance,
    }


def plan_to_dict(plan: RoutingPlan) -> dict[str, Any]:
    return {
        "scenario_id": plan.scenario_id,
        "routes": [vehicle_route_to_dict(route) for route in plan.routes],
        "total_distance": plan.total_distance,
    }


def event_to_dict(event: OperationalEvent) -> dict[str, Any]:
    return {
        "type": event.type.value,
        "payload": event.payload,
        "description": event.description,
    }


def validation_to_dict(validation: ValidationResult) -> dict[str, Any]:
    return {
        "passed": validation.passed,
        "violations": [
            {"code": violation.code, "message": violation.message, "severity": violation.severity}
            for violation in validation.violations
        ],
    }
