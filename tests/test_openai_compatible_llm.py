from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any

from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.domain.events import EventType
from adaptiveroute.llm.openai_compatible import OpenAICompatibleChatClient, OpenAICompatibleSettings
from adaptiveroute.services.event_extraction import LlmEventExtractor


class FakeOpenAICompatibleHandler(BaseHTTPRequestHandler):
    chat_payload: dict[str, Any] = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": "qwen-local-32b",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": '{"type":"CUSTOMER_UNAVAILABLE","payload":{"customer_id":"C3"}}',
                },
                "finish_reason": "stop",
            }
        ],
    }

    def do_GET(self) -> None:
        if self.path == "/v1/models":
            self._send_json({"object": "list", "data": [{"id": "qwen-local-14b"}, {"id": "qwen-local-32b"}]})
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:
        if self.path == "/v1/chat/completions":
            content_length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(content_length).decode("utf-8"))
            assert body["model"] == "qwen-local-32b"
            assert body["messages"][0]["role"] == "system"
            assert body["messages"][1]["role"] == "user"
            self._send_json(self.chat_payload)
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


def test_openai_compatible_client_lists_models_and_chats() -> None:
    server, base_url = _start_fake_server()
    try:
        client = OpenAICompatibleChatClient(
            OpenAICompatibleSettings(base_url=base_url, api_key="local", model="auto", timeout_seconds=2)
        )

        assert client.selected_model == "qwen-local-32b"
        assert client.available_models() == ["qwen-local-14b", "qwen-local-32b"]
        response = client.chat(system="Return JSON.", user="Customer C3 is unavailable.")

        assert response.model == "qwen-local-32b"
        assert json.loads(response.content)["type"] == "CUSTOMER_UNAVAILABLE"
    finally:
        server.shutdown()


def test_llm_event_extractor_accepts_valid_provider_event() -> None:
    server, base_url = _start_fake_server()
    try:
        client = OpenAICompatibleChatClient(
            OpenAICompatibleSettings(base_url=base_url, api_key="local", model="qwen-local-32b", timeout_seconds=2)
        )
        extractor = LlmEventExtractor(client=client)

        result = extractor.extract("The client on stop three is closed.", build_demo_scenario())

        assert result.event is not None
        assert result.event.type == EventType.CUSTOMER_UNAVAILABLE
        assert result.event.payload == {"customer_id": "C3"}
        assert result.method == "llm:qwen-local-32b"
    finally:
        server.shutdown()


def test_llm_event_extractor_falls_back_on_invalid_provider_event() -> None:
    server, base_url = _start_fake_server(
        {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "model": "qwen-local-32b",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": '{"type":"CUSTOMER_UNAVAILABLE","payload":{"customer_id":"C999"}}'},
                    "finish_reason": "stop",
                }
            ],
        }
    )
    try:
        client = OpenAICompatibleChatClient(
            OpenAICompatibleSettings(base_url=base_url, api_key="local", model="qwen-local-32b", timeout_seconds=2)
        )
        extractor = LlmEventExtractor(client=client)

        result = extractor.extract("Customer C3 cannot receive now.", build_demo_scenario())

        assert result.event is not None
        assert result.event.type == EventType.CUSTOMER_UNAVAILABLE
        assert result.event.payload == {"customer_id": "C3"}
        assert result.method == "llm_invalid_with_rule_fallback"
    finally:
        server.shutdown()


def test_llm_event_extractor_does_not_turn_context_follow_up_into_event() -> None:
    server, base_url = _start_fake_server(
        {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "model": "qwen-local-32b",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": '{"type":"BLOCK_ARC","payload":{"from_node":"C1","to_node":"C3","bidirectional":true}}'},
                    "finish_reason": "stop",
                }
            ],
        }
    )
    try:
        client = OpenAICompatibleChatClient(
            OpenAICompatibleSettings(base_url=base_url, api_key="local", model="qwen-local-32b", timeout_seconds=2)
        )
        extractor = LlmEventExtractor(client=client)

        result = extractor.extract(
            "Before I move on route ROUTE-001, confirm the route count and distance impact.",
            build_demo_scenario(),
        )

        assert result.event is None
        assert result.method == "context_follow_up"
    finally:
        server.shutdown()


def _start_fake_server(chat_payload: dict[str, Any] | None = None) -> tuple[ThreadingHTTPServer, str]:
    FakeOpenAICompatibleHandler.chat_payload = chat_payload or {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": "qwen-local-32b",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": '{"type":"CUSTOMER_UNAVAILABLE","payload":{"customer_id":"C3"}}',
                },
                "finish_reason": "stop",
            }
        ],
    }
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOpenAICompatibleHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, f"http://{host}:{port}/v1"
