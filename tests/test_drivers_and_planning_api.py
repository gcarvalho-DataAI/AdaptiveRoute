import jwt
import logging
import pytest
from fastapi.testclient import TestClient

from adaptiveroute.api.app import create_app, logger as api_logger
from adaptiveroute.api.dependencies import clear_dependency_caches


def test_driver_crud_and_daily_planning(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVEROUTE_MEMORY_BACKEND", "memory")
    monkeypatch.setenv("ADAPTIVEROUTE_MAP_ROUTER_BACKEND", "fallback")
    clear_dependency_caches()
    client = TestClient(create_app())

    for index in range(1, 3):
        response = client.post(
            "/v1/drivers",
            json={
                "id": f"DRIVER-{index:03d}",
                "name": f"Driver {index}",
                "vehicle_id": f"V{index}",
                "capacity": 20,
                "metadata": {"username": f"driver{index:03d}", "temporary_password": "demo"},
            },
        )
        assert response.status_code == 200

    drivers_response = client.get("/v1/drivers")
    assert drivers_response.status_code == 200
    assert len(drivers_response.json()) == 2

    plan_response = client.post(
        "/v1/planning/daily",
        json={"scenario_id": "demo-cvrp-8", "route_prefix": "TEST-ROUTE", "include_demo_drivers": False},
    )
    assert plan_response.status_code == 200
    body = plan_response.json()
    assert body["created_route_count"] == 2
    assert {route["driver_id"] for route in body["routes"]} == {"DRIVER-001", "DRIVER-002"}

    clear_dependency_caches()


def test_list_endpoints_support_pagination(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVEROUTE_MEMORY_BACKEND", "memory")
    monkeypatch.setenv("ADAPTIVEROUTE_MAP_ROUTER_BACKEND", "fallback")
    clear_dependency_caches()
    client = TestClient(create_app())

    for index in range(1, 4):
        response = client.post(
            "/v1/drivers",
            json={
                "id": f"PAGE-DRIVER-{index:03d}",
                "name": f"Page Driver {index}",
                "vehicle_id": f"V{index}",
                "capacity": 20,
                "metadata": {"username": f"page-driver-{index}", "temporary_password": "demo"},
            },
        )
        assert response.status_code == 200

    paged_drivers = client.get("/v1/drivers?skip=1&limit=1")
    assert paged_drivers.status_code == 200
    assert [driver["id"] for driver in paged_drivers.json()] == ["PAGE-DRIVER-002"]

    client.post("/v1/scenarios/demo")
    paged_scenarios = client.get("/v1/scenarios?skip=0&limit=1")
    assert paged_scenarios.status_code == 200
    assert len(paged_scenarios.json()) == 1

    clear_dependency_caches()


def test_api_logger_emits_info_after_app_start(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVEROUTE_MEMORY_BACKEND", "memory")
    monkeypatch.setenv("ADAPTIVEROUTE_MAP_ROUTER_BACKEND", "fallback")
    clear_dependency_caches()

    create_app()

    assert api_logger.isEnabledFor(logging.INFO)
    assert api_logger.handlers

    clear_dependency_caches()


def test_placeholder_jwt_secret_is_not_used_for_signing(monkeypatch) -> None:
    placeholder_secret = "change-this-secret-for-non-local-runs"
    monkeypatch.setenv("ADAPTIVEROUTE_MEMORY_BACKEND", "memory")
    monkeypatch.setenv("ADAPTIVEROUTE_MAP_ROUTER_BACKEND", "fallback")
    monkeypatch.setenv("ADAPTIVEROUTE_JWT_SECRET_KEY", placeholder_secret)
    clear_dependency_caches()
    client = TestClient(create_app())

    client.post(
        "/v1/drivers",
        json={
            "id": "DRIVER-PLACEHOLDER-JWT",
            "name": "Placeholder JWT Driver",
            "vehicle_id": "V1",
            "capacity": 20,
            "metadata": {"username": "placeholder-jwt-driver", "temporary_password": "secret"},
        },
    )
    client.post(
        "/v1/operational-routes",
        json={
            "id": "PLACEHOLDER-JWT-ROUTE",
            "driver_id": "DRIVER-PLACEHOLDER-JWT",
            "scenario_id": "demo-cvrp-8",
        },
    )
    login_response = client.post(
        "/v1/driver-portal/login",
        json={"username": "placeholder-jwt-driver", "password": "secret"},
    )
    assert login_response.status_code == 200

    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(login_response.json()["access_token"], placeholder_secret, algorithms=["HS256"])

    forged_token = jwt.encode(
        {"sub": "DRIVER-PLACEHOLDER-JWT", "role": "driver"},
        placeholder_secret,
        algorithm="HS256",
    )
    forged_response = client.post(
        "/v1/driver-portal/routes/PLACEHOLDER-JWT-ROUTE/status",
        headers={"Authorization": f"Bearer {forged_token}"},
        json={"status": "in_progress"},
    )
    assert forged_response.status_code == 401

    clear_dependency_caches()


def test_create_scenario_from_orders(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVEROUTE_MEMORY_BACKEND", "memory")
    monkeypatch.setenv("ADAPTIVEROUTE_MAP_ROUTER_BACKEND", "fallback")
    clear_dependency_caches()
    client = TestClient(create_app())

    response = client.post(
        "/v1/scenarios/from-orders",
        json={
            "id": "orders-test",
            "depot": {"address": "Depot", "lat": 40.0, "lng": -73.0},
            "orders": [
                {
                    "id": "ORDER-001",
                    "pickup": {"address": "Depot", "lat": 40.0, "lng": -73.0},
                    "delivery": {"address": "Customer", "lat": 40.1, "lng": -73.1},
                    "weight": 4,
                    "weight_unit": "kg",
                    "priority": 2,
                }
            ],
            "vehicle_count": 1,
            "vehicle_capacity": 10,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "orders-test"
    assert body["customers"][0]["demand"] == 4
    assert len(body["distance_matrix"]) == 4

    clear_dependency_caches()


def test_create_scenario_from_orders_file_csv(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVEROUTE_MEMORY_BACKEND", "memory")
    monkeypatch.setenv("ADAPTIVEROUTE_MAP_ROUTER_BACKEND", "fallback")
    clear_dependency_caches()
    client = TestClient(create_app())

    csv_content = (
        "order_id,pickup_address,pickup_lat,pickup_lng,delivery_address,delivery_lat,delivery_lng,weight,volume,priority\n"
        "ORDER-CSV-001,Depot,40.0,-73.0,Customer A,40.1,-73.1,5,1.2,2\n"
        "ORDER-CSV-002,Depot,40.0,-73.0,Customer B,40.2,-73.2,3,0.8,1\n"
    )
    response = client.post(
        "/v1/scenarios/from-orders-file",
        data={
            "scenario_id": "orders-csv-test",
            "depot_address": "Depot",
            "depot_lat": "40.0",
            "depot_lng": "-73.0",
            "vehicle_count": "2",
            "vehicle_capacity": "10",
            "use_road_distance": "false",
        },
        files={"file": ("orders.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "orders-csv-test"
    assert [customer["demand"] for customer in body["customers"]] == [5, 3]
    assert {vehicle["id"] for vehicle in body["vehicles"]} == {"V1", "V2"}
    assert len(body["distance_matrix"]) == 9

    clear_dependency_caches()


def test_driver_portal_login_and_own_route_update(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVEROUTE_MEMORY_BACKEND", "memory")
    monkeypatch.setenv("ADAPTIVEROUTE_MAP_ROUTER_BACKEND", "fallback")
    monkeypatch.setenv("ADAPTIVEROUTE_JWT_SECRET_KEY", "test-secret-with-at-least-32-bytes")
    clear_dependency_caches()
    client = TestClient(create_app())

    create_response = client.post(
        "/v1/drivers",
        json={
            "id": "DRIVER-PORTAL-1",
            "name": "Portal Driver",
            "vehicle_id": "V1",
            "capacity": 20,
            "metadata": {"username": "portal-driver", "temporary_password": "secret"},
        },
    )
    assert create_response.status_code == 200
    assert "temporary_password" not in create_response.json()["metadata"]
    assert "password_hash" not in create_response.json()["metadata"]
    assert create_response.json()["metadata"]["has_password"] is True
    client.post(
        "/v1/operational-routes",
        json={"id": "PORTAL-ROUTE-001", "driver_id": "DRIVER-PORTAL-1", "scenario_id": "demo-cvrp-8"},
    )

    login_response = client.post(
        "/v1/driver-portal/login",
        json={"username": "portal-driver", "password": "secret"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["routes"][0]["id"] == "PORTAL-ROUTE-001"
    token = login_response.json()["access_token"]
    assert not token.startswith("mock-driver-token:")
    claims = jwt.decode(token, "test-secret-with-at-least-32-bytes", algorithms=["HS256"])
    assert claims["sub"] == "DRIVER-PORTAL-1"
    assert claims["role"] == "driver"
    assert claims["username"] == "portal-driver"
    assert "password_hash" not in login_response.json()["driver"]["metadata"]

    update_response = client.post(
        "/v1/driver-portal/routes/PORTAL-ROUTE-001/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "in_progress"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "in_progress"

    profile_response = client.put(
        "/v1/driver-portal/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"capacity": 22, "new_password": "new-secret"},
    )
    assert profile_response.status_code == 200
    assert profile_response.json()["capacity"] == 22
    assert "password_hash" not in profile_response.json()["metadata"]
    assert profile_response.json()["metadata"]["has_password"] is True

    relogin_response = client.post(
        "/v1/driver-portal/login",
        json={"username": "portal-driver", "password": "new-secret"},
    )
    assert relogin_response.status_code == 200

    clear_dependency_caches()


def test_delete_driver_keeps_assigned_route_as_removed(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVEROUTE_MEMORY_BACKEND", "memory")
    monkeypatch.setenv("ADAPTIVEROUTE_MAP_ROUTER_BACKEND", "fallback")
    clear_dependency_caches()
    client = TestClient(create_app())

    driver_response = client.post(
        "/v1/drivers",
        json={
            "id": "DRIVER-REMOVED-1",
            "name": "Removed Driver",
            "vehicle_id": "V1",
            "capacity": 20,
            "metadata": {"username": "removed-driver", "temporary_password": "secret"},
        },
    )
    assert driver_response.status_code == 200

    route_response = client.post(
        "/v1/operational-routes",
        json={"id": "REMOVED-ROUTE-001", "driver_id": "DRIVER-REMOVED-1", "scenario_id": "demo-cvrp-8"},
    )
    assert route_response.status_code == 200

    delete_response = client.delete("/v1/drivers/DRIVER-REMOVED-1")
    assert delete_response.status_code == 200
    assert delete_response.json()["updated_routes"] == 1

    route_after_delete = client.get("/v1/operational-routes/REMOVED-ROUTE-001")
    assert route_after_delete.status_code == 200
    body = route_after_delete.json()
    assert body["driver_id"] == "removed:DRIVER-REMOVED-1"
    assert body["metadata"]["driver_removed"] is True
    assert body["metadata"]["removed_driver"]["id"] == "DRIVER-REMOVED-1"

    login_response = client.post(
        "/v1/driver-portal/login",
        json={"username": "removed-driver", "password": "secret"},
    )
    assert login_response.status_code == 401

    clear_dependency_caches()


def test_route_question_answers_without_replanning_event(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVEROUTE_MEMORY_BACKEND", "memory")
    monkeypatch.setenv("ADAPTIVEROUTE_MAP_ROUTER_BACKEND", "fallback")
    monkeypatch.setenv("ADAPTIVEROUTE_ORCHESTRATOR_BASE_URL", "http://127.0.0.1:1/v1")
    clear_dependency_caches()
    client = TestClient(create_app())

    client.post(
        "/v1/drivers",
        json={
            "id": "DRIVER-QA-1",
            "name": "QA Driver",
            "vehicle_id": "V1",
            "capacity": 20,
            "metadata": {"username": "qa-driver", "temporary_password": "secret"},
        },
    )
    client.post(
        "/v1/operational-routes",
        json={"id": "QA-ROUTE-001", "driver_id": "DRIVER-QA-1", "scenario_id": "demo-cvrp-8"},
    )

    response = client.post(
        "/v1/agentic/replan",
        json={"message": "For route QA-ROUTE-001, summarize the stops, load, distance and feasibility."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["agentic_result"]["mode"] == "route_qa"
    assert body["agentic_result"]["succeeded"] is True
    assert body["agentic_result"]["route_id"] == "QA-ROUTE-001"
    assert body["agentic_result"]["route_facts"]["total_distance"] == 293.36
    assert "No new operational event detected" not in body["assistant_message"]

    clear_dependency_caches()


def test_route_question_uses_retrieved_rag_context(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVEROUTE_MEMORY_BACKEND", "memory")
    monkeypatch.setenv("ADAPTIVEROUTE_MAP_ROUTER_BACKEND", "fallback")
    monkeypatch.setenv("ADAPTIVEROUTE_RAG_BACKEND", "memory")
    monkeypatch.setenv("ADAPTIVEROUTE_RAG_EMBEDDING_BACKEND", "hash")
    monkeypatch.setenv("ADAPTIVEROUTE_RAG_EMBEDDING_DIM", "64")
    monkeypatch.setenv("ADAPTIVEROUTE_ORCHESTRATOR_BACKEND", "rules")
    monkeypatch.setenv("ADAPTIVEROUTE_ROUTE_QA_REQUIRE_LLM", "false")
    monkeypatch.setenv("ADAPTIVEROUTE_ORCHESTRATOR_BASE_URL", "http://127.0.0.1:1/v1")
    clear_dependency_caches()
    client = TestClient(create_app())

    doc = tmp_path / "route_qa.md"
    doc.write_text(
        "Route Q&A policy: the first delivery stop is the first customer node after the depot. "
        "The depot is not a delivery stop.",
        encoding="utf-8",
    )
    ingest_response = client.post("/v1/rag/ingest", json={"paths": [str(doc)]})
    assert ingest_response.status_code == 200

    client.post(
        "/v1/drivers",
        json={
            "id": "DRIVER-RAG-QA-1",
            "name": "RAG QA Driver",
            "vehicle_id": "V1",
            "capacity": 20,
            "metadata": {"username": "rag-qa-driver", "temporary_password": "secret"},
        },
    )
    client.post(
        "/v1/operational-routes",
        json={"id": "RAG-QA-ROUTE-001", "driver_id": "DRIVER-RAG-QA-1", "scenario_id": "demo-cvrp-8"},
    )

    response = client.post(
        "/v1/agentic/replan",
        json={"message": "For route RAG-QA-ROUTE-001, what is the first delivery stop after the depot?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["agentic_result"]["mode"] == "route_qa"
    assert body["agentic_result"]["succeeded"] is True
    assert body["agentic_result"]["rag_context"]
    assert body["agentic_result"]["rag_context"][0]["source_path"] == str(doc)
    assert any(item["node"] == "route_qa_rag" and item["payload"]["result_count"] >= 1 for item in body["agentic_result"]["trace"])

    clear_dependency_caches()
