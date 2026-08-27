#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from adaptiveroute.domain.serialization import scenario_from_dict
from adaptiveroute.services.validation import validate_plan
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine


DEPOT = {
    "address": "Pier 57, 25 11th Ave, New York, NY",
    "lat": 40.7431,
    "lng": -74.0106,
}


LIGHT_NYC_ORDERS = [
    ("Chelsea Market", "75 9th Ave, New York, NY", 40.7424, -74.0060, 2, 0.8, 2),
    ("Flatiron District Office", "175 5th Ave, New York, NY", 40.7411, -73.9897, 3, 1.0, 1),
    ("SoHo Retail Dock", "Prince St & Broadway, New York, NY", 40.7248, -73.9973, 4, 1.4, 3),
    ("Lower East Side Pharmacy", "Delancey St & Essex St, New York, NY", 40.7188, -73.9888, 1, 0.5, 1),
    ("Battery Park Dropoff", "Battery Pl, New York, NY", 40.7033, -74.0170, 2, 0.9, 2),
    ("Tribeca Clinic", "310 Greenwich St, New York, NY", 40.7174, -74.0101, 4, 1.3, 2),
    ("World Trade Center Office", "285 Fulton St, New York, NY", 40.7127, -74.0134, 3, 1.0, 1),
    ("East Village Grocery", "1st Ave & E 9th St, New York, NY", 40.7291, -73.9866, 2, 0.7, 1),
    ("Hudson Yards Tower", "34th St & 11th Ave, New York, NY", 40.7538, -74.0022, 2, 0.8, 2),
    ("Grand Central Office", "89 E 42nd St, New York, NY", 40.7527, -73.9772, 3, 1.0, 1),
    ("Williamsburg Retail", "Bedford Ave & N 7th St, Brooklyn, NY", 40.7179, -73.9575, 2, 0.7, 1),
    ("Downtown Brooklyn Office", "Jay St & Willoughby St, Brooklyn, NY", 40.6926, -73.9875, 3, 1.1, 2),
    ("Park Slope Market", "5th Ave & Union St, Brooklyn, NY", 40.6774, -73.9831, 2, 0.8, 1),
    ("Gowanus Fulfillment", "3rd Ave & 9th St, Brooklyn, NY", 40.6736, -73.9942, 4, 1.3, 3),
    ("Long Island City Dock", "44th Dr & Vernon Blvd, Queens, NY", 40.7474, -73.9548, 3, 1.0, 1),
    ("Astoria Pharmacy", "31st St & Ditmars Blvd, Queens, NY", 40.7766, -73.9126, 2, 0.8, 2),
    ("Sunnyside Grocery", "Queens Blvd & 46th St, Queens, NY", 40.7433, -73.9185, 1, 0.6, 1),
    ("Hoboken Waterfront", "1 Hudson Pl, Hoboken, NJ", 40.7359, -74.0292, 2, 0.8, 1),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed a lighter NYC daily manifest scenario similar to the 36-order scenario.")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8090")
    parser.add_argument("--scenario-id", default="daily-nyc-manifest-18")
    parser.add_argument("--vehicle-count", type=int, default=3)
    parser.add_argument("--vehicle-capacity", type=int, default=18)
    parser.add_argument("--order-count", type=int, default=len(LIGHT_NYC_ORDERS))
    parser.add_argument("--solver-time-limit", type=float, default=60)
    parser.add_argument("--no-road-distance", action="store_true")
    parser.add_argument("--out", default="outputs/scenarios/daily_nyc_manifest_18.json")
    parser.add_argument("--validate-solver", action="store_true")
    args = parser.parse_args()

    payload = build_payload(
        scenario_id=args.scenario_id,
        vehicle_count=args.vehicle_count,
        vehicle_capacity=args.vehicle_capacity,
        use_road_distance=not args.no_road_distance,
        order_count=args.order_count,
    )
    response = post_json(f"{args.api_base_url.rstrip('/')}/v1/scenarios/from-orders", payload)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(response, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Seeded scenario: {response['id']}")
    print(f"Stops: {len(response.get('customers', []))}")
    print(f"Vehicles: {len(response.get('vehicles', []))}")
    print(f"Saved artifact: {out_path}")

    if args.validate_solver:
        scenario = scenario_from_dict(response)
        result = PyomoHighsEngine(time_limit_seconds=args.solver_time_limit).solve(scenario)
        print(f"Solver status: {result.status.value}")
        print(f"Solve time ms: {round(result.solve_time_ms or 0, 2)}")
        if result.plan is None:
            print(f"Solver message: {result.message}")
            return 2
        validation = validate_plan(scenario, result.plan)
        served = {
            stop
            for route in result.plan.routes
            for stop in route.stops
            if stop != scenario.depot.id
        }
        active = {customer.id for customer in scenario.active_customers}
        missing = sorted(active - served, key=lambda value: int(value[1:]))
        print(f"Validation passed: {validation.passed}")
        print(f"Coverage: {len(served)}/{len(active)}")
        print(f"Missing customers: {missing or 'none'}")
        print(f"Total distance: {result.plan.total_distance}")

    return 0


def build_payload(
    *,
    scenario_id: str,
    vehicle_count: int,
    vehicle_capacity: int,
    use_road_distance: bool,
    order_count: int,
) -> dict[str, Any]:
    if order_count < 1 or order_count > len(LIGHT_NYC_ORDERS):
        raise ValueError(f"order_count must be between 1 and {len(LIGHT_NYC_ORDERS)}.")
    selected_orders = LIGHT_NYC_ORDERS[:order_count]
    return {
        "id": scenario_id,
        "depot": DEPOT,
        "orders": [
            {
                "id": f"ORDER-LIGHT-NYC-{index:03d}",
                "pickup": DEPOT,
                "delivery": {
                    "address": address,
                    "lat": lat,
                    "lng": lng,
                },
                "weight": weight,
                "weight_unit": "kg",
                "volume": volume,
                "volume_unit": "m3",
                "priority": priority,
                "description": f"Daily manifest delivery · {label}",
            }
            for index, (label, address, lat, lng, weight, volume, priority) in enumerate(selected_orders, start=1)
        ],
        "vehicle_count": vehicle_count,
        "vehicle_capacity": vehicle_capacity,
        "use_road_distance": use_road_distance,
    }


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {error_body}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
