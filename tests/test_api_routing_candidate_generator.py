from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any

from adaptiveroute.agentic.candidates import ApiRoutingCandidateGenerator
from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.domain.events import EventType, OperationalEvent
from adaptiveroute.llm.openai_compatible import OpenAICompatibleChatClient, OpenAICompatibleSettings
from adaptiveroute.services.mutations import apply_event
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine


class FakeRoutingPolicyHandler(BaseHTTPRequestHandler):
    last_payload: dict[str, Any] | None = None
    payloads: list[dict[str, Any]] = []
    responses: list[str] = ['{"routes":{"V1":["D0","C1","C2","C5","C6","D0"],"V2":["D0","C3","C4","C7","C8","D0"]}}']

    def do_GET(self) -> None:
        if self.path == "/v1/models":
            self._send_json({"object": "list", "data": [{"id": "adaptiveroute-routing-policy"}]})
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:
        if self.path == "/v1/chat/completions":
            content_length = int(self.headers.get("Content-Length", "0"))
            self.__class__.last_payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            self.__class__.payloads.append(self.__class__.last_payload)
            content = self.__class__.responses[min(len(self.__class__.payloads) - 1, len(self.__class__.responses) - 1)]
            self._send_json(
                {
                    "id": "chatcmpl-test",
                    "object": "chat.completion",
                    "model": "adaptiveroute-routing-policy",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": content,
                            },
                            "finish_reason": "stop",
                        }
                    ],
                }
            )
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_json(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def test_api_routing_candidate_generator_builds_plan_from_policy_routes() -> None:
    FakeRoutingPolicyHandler.last_payload = None
    FakeRoutingPolicyHandler.payloads = []
    FakeRoutingPolicyHandler.responses = [
        '{"routes":{"V1":["D0","C1","C2","C5","C6","D0"],"V2":["D0","C4","C7","C8","D0"]}}'
    ]
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeRoutingPolicyHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        scenario = build_demo_scenario()
        base_plan = PyomoHighsEngine().solve(scenario).plan
        assert base_plan is not None
        event = OperationalEvent(
            type=EventType.CUSTOMER_UNAVAILABLE,
            payload={"customer_id": "C3"},
            description="Customer C3 is unavailable.",
        )
        mutated_scenario, _ = apply_event(scenario, event)
        client = OpenAICompatibleChatClient(
            OpenAICompatibleSettings(
                base_url=f"http://{host}:{port}/v1",
                api_key="local",
                model="adaptiveroute-routing-policy",
                timeout_seconds=2,
            )
        )
        generator = ApiRoutingCandidateGenerator(client)

        result = generator.generate(mutated_scenario, event, base_plan)

        assert result.plan is not None
        assert result.source == "api_candidate:adaptiveroute-routing-policy"
        assert result.plan.routes[0].vehicle_id == "V1"
        assert result.plan.routes[0].stops == ("D0", "C1", "C2", "C5", "C6", "D0")
        assert result.plan.routes[0].load > 0
        assert result.plan.total_distance > 0
        assert FakeRoutingPolicyHandler.last_payload is not None
        assert FakeRoutingPolicyHandler.last_payload["response_format"] == {"type": "json_object"}
    finally:
        server.shutdown()


def test_api_routing_candidate_generator_retries_with_validation_feedback() -> None:
    FakeRoutingPolicyHandler.last_payload = None
    FakeRoutingPolicyHandler.payloads = []
    FakeRoutingPolicyHandler.responses = [
        '{"routes":{"V1":["D0","C1","D0"]}}',
        '{"routes":{"V1":["D0","C1","C2","C5","C6","D0"],"V2":["D0","C4","C7","C8","D0"]}}',
    ]
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeRoutingPolicyHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        scenario = build_demo_scenario()
        base_plan = PyomoHighsEngine().solve(scenario).plan
        assert base_plan is not None
        event = OperationalEvent(
            type=EventType.CUSTOMER_UNAVAILABLE,
            payload={"customer_id": "C3"},
            description="Customer C3 is unavailable.",
        )
        mutated_scenario, _ = apply_event(scenario, event)
        client = OpenAICompatibleChatClient(
            OpenAICompatibleSettings(
                base_url=f"http://{host}:{port}/v1",
                api_key="local",
                model="adaptiveroute-routing-policy",
                timeout_seconds=2,
            )
        )
        generator = ApiRoutingCandidateGenerator(client, max_retries=1)

        result = generator.generate(mutated_scenario, event, base_plan)

        assert result.plan is not None
        assert len(FakeRoutingPolicyHandler.payloads) == 2
        correction_prompt = FakeRoutingPolicyHandler.payloads[1]["messages"][1]["content"]
        assert "Validation feedback JSON" in correction_prompt
        assert "missing_customer" in correction_prompt
        assert "after 2 attempt(s)" in result.message
    finally:
        server.shutdown()


def test_api_routing_candidate_generator_returns_last_invalid_plan_after_retry_exhaustion() -> None:
    FakeRoutingPolicyHandler.last_payload = None
    FakeRoutingPolicyHandler.payloads = []
    FakeRoutingPolicyHandler.responses = [
        '{"routes":{"V1":["D0","C1","D0"]}}',
        '{"routes":{"V1":["D0","C1","D0"]}}',
    ]
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeRoutingPolicyHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        scenario = build_demo_scenario()
        base_plan = PyomoHighsEngine().solve(scenario).plan
        assert base_plan is not None
        event = OperationalEvent(
            type=EventType.CUSTOMER_UNAVAILABLE,
            payload={"customer_id": "C3"},
            description="Customer C3 is unavailable.",
        )
        mutated_scenario, _ = apply_event(scenario, event)
        client = OpenAICompatibleChatClient(
            OpenAICompatibleSettings(
                base_url=f"http://{host}:{port}/v1",
                api_key="local",
                model="adaptiveroute-routing-policy",
                timeout_seconds=2,
            )
        )
        generator = ApiRoutingCandidateGenerator(client, max_retries=1)

        result = generator.generate(mutated_scenario, event, base_plan)

        assert result.plan is not None
        assert len(FakeRoutingPolicyHandler.payloads) == 2
        assert "failed after 2 attempt(s)" in result.message
    finally:
        server.shutdown()
