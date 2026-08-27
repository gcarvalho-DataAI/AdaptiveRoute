from __future__ import annotations

import argparse
import json
from typing import Any
from urllib import request


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a realistic driver conversation against the AdaptiveRoute API.")
    parser.add_argument("--api-base", default="http://127.0.0.1:8090")
    parser.add_argument("--scenario-id", default="driver-shift-001")
    args = parser.parse_args()

    api = ApiClient(args.api_base.rstrip("/"))

    demo = api.post("/v1/scenarios/demo", {})
    scenario = dict(demo)
    scenario["id"] = args.scenario_id
    api.put(f"/v1/scenarios/{args.scenario_id}", scenario)
    api.post(
        "/v1/operational-routes",
        {
            "id": "ROUTE-001",
            "driver_id": "DRIVER-001",
            "scenario_id": args.scenario_id,
            "status": "in_progress",
            "metadata": {"shift": "morning", "vehicle_id": "V1"},
        },
    )

    turn1 = api.post(
        "/v1/agentic/replan",
        {
            "message": (
                "Preciso que refaça minha rota ROUTE-001, há um bloqueio entre C1 e C3 "
                "por causa de um acidente."
            ),
        },
    )
    conversation_id = turn1["conversation_id"]

    turn2 = api.post(
        "/v1/agentic/replan",
        {
            "conversation_id": conversation_id,
            "message": (
                "Before I move on route ROUTE-001, confirm the route count, total distance impact, "
                "and whether every active customer is still served."
            ),
        },
    )

    messages = api.get(f"/v1/conversations/{conversation_id}/messages")
    context = api.get(f"/v1/conversations/{conversation_id}/context")

    print(
        json.dumps(
            {
                "conversation_id": conversation_id,
                "scenario_id": args.scenario_id,
                "operational_route": api.get("/v1/operational-routes/ROUTE-001"),
                "turns": [
                    _summarize_turn("driver_reports_blocked_road", turn1),
                    _summarize_turn("driver_asks_follow_up", turn2),
                ],
                "message_count": len(messages),
                "messages": [{"role": item["role"], "content": item["content"]} for item in messages],
                "context": {
                    "summary": context["summary"],
                    "last_event": context["last_event"],
                    "last_plan_present": context["last_plan"] is not None,
                    "recent_message_count": len(context["recent_message_ids"]),
                },
            },
            indent=2,
        )
    )
    return 0


class ApiClient:
    def __init__(self, base_url: str):
        self._base_url = base_url

    def get(self, path: str) -> Any:
        with request.urlopen(f"{self._base_url}{path}", timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        return self._send("POST", path, payload)

    def put(self, path: str, payload: dict[str, Any]) -> Any:
        return self._send("PUT", path, payload)

    def _send(self, method: str, path: str, payload: dict[str, Any]) -> Any:
        req = request.Request(
            url=f"{self._base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method=method,
        )
        with request.urlopen(req, timeout=240) as response:
            return json.loads(response.read().decode("utf-8"))


def _summarize_turn(name: str, turn: dict[str, Any]) -> dict[str, Any]:
    result = turn["agentic_result"]
    candidate = result.get("candidate") or {}
    return {
        "name": name,
        "assistant_message": turn["assistant_message"],
        "succeeded": result.get("succeeded"),
        "source": result.get("source"),
        "event": result.get("event"),
        "event_extractor": ((result.get("trace") or [{}])[0].get("payload") or {}).get("method"),
        "candidate_source": candidate.get("source"),
        "candidate_validation": candidate.get("validation"),
        "final_validation": result.get("final_validation"),
        "comparison": result.get("comparison"),
        "trace_nodes": [item.get("node") for item in result.get("trace", [])],
        "errors": result.get("errors"),
    }


if __name__ == "__main__":
    raise SystemExit(main())
