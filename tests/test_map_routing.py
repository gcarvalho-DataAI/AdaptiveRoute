from adaptiveroute.maps import MapRoutingService


def test_map_routing_service_returns_fallback_geometry() -> None:
    service = MapRoutingService(backend="fallback")
    response = service.route_geometry(
        plan={
            "routes": [
                {
                    "vehicle_id": "V1",
                    "stops": ["D0", "C1", "D0"],
                }
            ]
        },
        locations={
            "D0": {"lat": 40.0, "lng": -73.0},
            "C1": {"lat": 40.1, "lng": -73.1},
        },
    )

    assert response["source"] == "fallback"
    assert response["routes"][0]["vehicle_id"] == "V1"
    assert response["routes"][0]["geometry"] == [[40.0, -73.0], [40.1, -73.1], [40.0, -73.0]]


def test_map_routing_service_falls_back_when_osrm_is_unavailable() -> None:
    service = MapRoutingService(backend="osrm", osrm_base_url="http://127.0.0.1:1", timeout_seconds=0.01)
    response = service.route_geometry(
        plan={
            "routes": [
                {
                    "vehicle_id": "V1",
                    "stops": ["D0", "C1"],
                }
            ]
        },
        locations={
            "D0": {"lat": 40.0, "lng": -73.0},
            "C1": {"lat": 40.1, "lng": -73.1},
        },
    )

    assert response["source"] == "mixed"
    assert response["routes"][0]["source"] == "fallback"
    assert response["warnings"]
