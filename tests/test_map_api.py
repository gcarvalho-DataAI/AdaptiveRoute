from fastapi.testclient import TestClient

from adaptiveroute.api.app import create_app
from adaptiveroute.api.dependencies import clear_dependency_caches


def test_route_geometry_endpoint_returns_fallback(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVEROUTE_MAP_ROUTER_BACKEND", "fallback")
    clear_dependency_caches()
    client = TestClient(create_app())

    response = client.post(
        "/v1/maps/route-geometry",
        json={
            "plan": {"routes": [{"vehicle_id": "V1", "stops": ["D0", "C1"]}]},
            "locations": {
                "D0": {"lat": 40.0, "lng": -73.0},
                "C1": {"lat": 40.1, "lng": -73.1},
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fallback"
    assert body["routes"][0]["geometry"] == [[40.0, -73.0], [40.1, -73.1]]
