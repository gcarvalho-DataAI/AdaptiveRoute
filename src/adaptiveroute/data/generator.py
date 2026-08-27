from __future__ import annotations

import random
from math import ceil, hypot

from adaptiveroute.domain.models import Customer, Depot, RoutingScenario, Vehicle


def euclidean_distance_matrix(nodes: tuple[Depot | Customer, ...]) -> dict[tuple[str, str], float]:
    matrix: dict[tuple[str, str], float] = {}
    for origin in nodes:
        for destination in nodes:
            if origin.id == destination.id:
                matrix[(origin.id, destination.id)] = 0.0
                continue
            matrix[(origin.id, destination.id)] = round(hypot(origin.x - destination.x, origin.y - destination.y), 2)
    return matrix


def generate_scenario(
    *,
    seed: int,
    num_customers: int = 8,
    num_vehicles: int = 2,
    coordinate_range: tuple[int, int] = (5, 95),
    demand_range: tuple[int, int] = (2, 8),
    priority_ratio: float = 0.25,
    capacity_slack: float = 1.25,
    clustered: bool = False,
) -> RoutingScenario:
    rng = random.Random(seed)
    depot = Depot(id="D0", x=50.0, y=50.0)

    clusters = [(25.0, 70.0), (75.0, 70.0), (50.0, 25.0)]
    customers: list[Customer] = []
    for idx in range(1, num_customers + 1):
        if clustered:
            center_x, center_y = clusters[(idx - 1) % len(clusters)]
            x = max(0.0, min(100.0, rng.gauss(center_x, 9.0)))
            y = max(0.0, min(100.0, rng.gauss(center_y, 9.0)))
        else:
            low, high = coordinate_range
            x = rng.uniform(low, high)
            y = rng.uniform(low, high)
        priority = 3 if rng.random() < priority_ratio else rng.choice([1, 2])
        customers.append(
            Customer(
                id=f"C{idx}",
                x=round(x, 2),
                y=round(y, 2),
                demand=rng.randint(*demand_range),
                priority=priority,
            )
        )

    total_demand = sum(customer.demand for customer in customers)
    capacity = max(max(customer.demand for customer in customers), ceil(total_demand * capacity_slack / num_vehicles))
    vehicles = tuple(Vehicle(id=f"V{idx}", capacity=capacity) for idx in range(1, num_vehicles + 1))
    nodes = (depot, *customers)

    return RoutingScenario(
        id=f"synthetic-{seed}-{num_customers}c-{num_vehicles}v",
        depot=depot,
        customers=tuple(customers),
        vehicles=vehicles,
        distance_matrix=euclidean_distance_matrix(nodes),
    )

