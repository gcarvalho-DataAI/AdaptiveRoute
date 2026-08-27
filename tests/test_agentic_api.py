from __future__ import annotations

from fastapi.testclient import TestClient

from adaptiveroute.api.app import create_app
from adaptiveroute.api.dependencies import clear_dependency_caches


def test_fastapi_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_fastapi_cors_allows_delete_preflight() -> None:
    client = TestClient(create_app())

    response = client.options(
        "/v1/conversations/test-id",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "DELETE",
        },
    )

    assert response.status_code == 200
    assert "DELETE" in response.headers["access-control-allow-methods"]


def test_fastapi_replan_creates_conversation_and_context(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVEROUTE_MEMORY_BACKEND", "memory")
    monkeypatch.setenv("ADAPTIVEROUTE_ORCHESTRATOR_BACKEND", "rules")
    monkeypatch.setenv("ADAPTIVEROUTE_ROUTING_POLICY_BACKEND", "solver")
    clear_dependency_caches()
    client = TestClient(create_app())

    response = client.post("/v1/agentic/replan", json={"message": "Customer C3 cannot receive now."})

    assert response.status_code == 200
    body = response.json()
    assert body["conversation_id"]
    assert body["agentic_result"]["succeeded"] is True
    assert body["context_window"]["last_event"]["payload"] == {"customer_id": "C3"}

    messages_response = client.get(f"/v1/conversations/{body['conversation_id']}/messages")
    assert messages_response.status_code == 200
    assert [message["role"] for message in messages_response.json()] == ["user", "assistant"]

    context_response = client.get(f"/v1/conversations/{body['conversation_id']}/context")
    assert context_response.status_code == 200
    assert context_response.json()["last_plan"] is not None

    runs_response = client.get(f"/v1/conversations/{body['conversation_id']}/agent-runs")
    assert runs_response.status_code == 200
    assert len(runs_response.json()) == 1
    assert runs_response.json()[0]["result"]["succeeded"] is True
    clear_dependency_caches()


def test_fastapi_can_create_and_append_to_conversation(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVEROUTE_MEMORY_BACKEND", "memory")
    clear_dependency_caches()
    client = TestClient(create_app())

    create_response = client.post("/v1/conversations", json={"title": "Manual session"})
    assert create_response.status_code == 200
    conversation_id = create_response.json()["id"]

    append_response = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        json={"role": "system", "content": "Manual context note."},
    )

    assert append_response.status_code == 200
    assert append_response.json()["role"] == "system"
    clear_dependency_caches()


def test_fastapi_can_delete_conversation_history(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVEROUTE_MEMORY_BACKEND", "memory")
    clear_dependency_caches()
    client = TestClient(create_app())

    create_response = client.post("/v1/conversations", json={"title": "Delete me"})
    assert create_response.status_code == 200
    conversation_id = create_response.json()["id"]
    append_response = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        json={"role": "user", "content": "hello"},
    )
    assert append_response.status_code == 200

    delete_response = client.delete(f"/v1/conversations/{conversation_id}")

    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True
    assert client.get(f"/v1/conversations/{conversation_id}").status_code == 404
    assert client.get(f"/v1/conversations/{conversation_id}/messages").status_code == 404
    clear_dependency_caches()


def test_fastapi_scenario_database_feeds_replan(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVEROUTE_MEMORY_BACKEND", "memory")
    monkeypatch.setenv("ADAPTIVEROUTE_ORCHESTRATOR_BACKEND", "rules")
    monkeypatch.setenv("ADAPTIVEROUTE_ROUTING_POLICY_BACKEND", "solver")
    clear_dependency_caches()
    client = TestClient(create_app())

    demo_response = client.post("/v1/scenarios/demo")
    assert demo_response.status_code == 200
    scenario = demo_response.json()
    scenario["id"] = "driver-shift-001"

    save_response = client.put("/v1/scenarios/driver-shift-001", json=scenario)
    assert save_response.status_code == 200

    replan_response = client.post(
        "/v1/agentic/replan",
        json={
            "message": "Accident between C1 and C3. Avoid that road.",
            "scenario_id": "driver-shift-001",
        },
    )

    assert replan_response.status_code == 200
    body = replan_response.json()
    assert body["agentic_result"]["succeeded"] is True
    assert body["agentic_result"]["replanning_scenario"]["id"] == "driver-shift-001-block-C1-C3"

    clear_dependency_caches()


def test_fastapi_replan_rejects_unknown_scenario(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVEROUTE_MEMORY_BACKEND", "memory")
    monkeypatch.setenv("ADAPTIVEROUTE_ORCHESTRATOR_BACKEND", "rules")
    monkeypatch.setenv("ADAPTIVEROUTE_ROUTING_POLICY_BACKEND", "solver")
    clear_dependency_caches()
    client = TestClient(create_app())

    response = client.post(
        "/v1/agentic/replan",
        json={"message": "Customer C1 is unavailable.", "scenario_id": "missing-scenario"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Routing scenario not found: missing-scenario"
    clear_dependency_caches()


def test_fastapi_operational_route_id_drives_replan(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVEROUTE_MEMORY_BACKEND", "memory")
    monkeypatch.setenv("ADAPTIVEROUTE_ORCHESTRATOR_BACKEND", "rules")
    monkeypatch.setenv("ADAPTIVEROUTE_ROUTING_POLICY_BACKEND", "solver")
    clear_dependency_caches()
    client = TestClient(create_app())

    route_response = client.post(
        "/v1/operational-routes",
        json={"id": "ROUTE-001", "driver_id": "DRIVER-001", "scenario_id": "demo-cvrp-8"},
    )
    assert route_response.status_code == 200
    assert route_response.json()["current_plan"]["scenario_id"] == "demo-cvrp-8"

    replan_response = client.post(
        "/v1/agentic/replan",
        json={"message": "Preciso que refaça minha rota ROUTE-001, há um bloqueio entre C1 e C3."},
    )
    assert replan_response.status_code == 200
    body = replan_response.json()
    assert body["operational_route"]["id"] == "ROUTE-001"
    assert body["operational_route"]["driver_id"] == "DRIVER-001"
    assert body["agentic_result"]["succeeded"] is True
    assert body["agentic_result"]["comparison"]["scenario_id_before"] == "demo-cvrp-8"

    updated_route_response = client.get("/v1/operational-routes/ROUTE-001")
    assert updated_route_response.status_code == 200
    updated_route = updated_route_response.json()
    assert updated_route["scenario_id"] == "demo-cvrp-8-block-C1-C3"
    assert updated_route["current_plan"]["scenario_id"] == "demo-cvrp-8-block-C1-C3"

    saved_scenario_response = client.get("/v1/scenarios/demo-cvrp-8-block-C1-C3")
    assert saved_scenario_response.status_code == 200
    assert {"from": "C1", "to": "C3"} in saved_scenario_response.json()["blocked_arcs"]
    clear_dependency_caches()


def test_fastapi_replan_rejects_unknown_operational_route(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVEROUTE_MEMORY_BACKEND", "memory")
    monkeypatch.setenv("ADAPTIVEROUTE_ORCHESTRATOR_BACKEND", "rules")
    monkeypatch.setenv("ADAPTIVEROUTE_ROUTING_POLICY_BACKEND", "solver")
    clear_dependency_caches()
    client = TestClient(create_app())

    response = client.post(
        "/v1/agentic/replan",
        json={"message": "Preciso que refaça minha rota ROUTE-MISSING, há um bloqueio entre C1 e C3."},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Operational route not found: ROUTE-MISSING"
    clear_dependency_caches()
