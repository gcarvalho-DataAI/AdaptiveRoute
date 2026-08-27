from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

from adaptiveroute.domain.events import EventType, OperationalEvent
from adaptiveroute.domain.models import RoutingScenario
from adaptiveroute.domain.serialization import scenario_to_dict
from adaptiveroute.llm.openai_compatible import OpenAICompatibleChatClient


@dataclass(frozen=True)
class EventExtractionResult:
    event: OperationalEvent | None
    confidence: float
    method: str
    error: str = ""


class EventExtractor(Protocol):
    def extract(self, text: str, scenario: RoutingScenario) -> EventExtractionResult:
        """Extract a structured operational event from user text."""


class RuleBasedEventExtractor:
    def extract(self, text: str, scenario: RoutingScenario) -> EventExtractionResult:
        normalized = " ".join(text.strip().split())
        if not normalized:
            return EventExtractionResult(event=None, confidence=0.0, method="rule_based", error="Empty input.")

        known_node_ids = {scenario.depot.id, *(customer.id for customer in scenario.customers)}
        customer_ids = {customer.id for customer in scenario.customers}
        upper_text = normalized.upper()

        block_result = self._extract_block_arc(normalized, upper_text, known_node_ids)
        if block_result:
            return block_result

        unavailable_result = self._extract_customer_unavailable(normalized, upper_text, customer_ids)
        if unavailable_result:
            return unavailable_result

        priority_result = self._extract_priority_change(normalized, upper_text, customer_ids)
        if priority_result:
            return priority_result

        return EventExtractionResult(
            event=None,
            confidence=0.0,
            method="rule_based",
            error="Could not map text to a supported event.",
        )

    def _extract_block_arc(
        self,
        original_text: str,
        upper_text: str,
        node_ids: set[str],
    ) -> EventExtractionResult | None:
        if not any(
            keyword in upper_text
            for keyword in (
                "ACCIDENT",
                "BLOCK",
                "BLOCKED",
                "CLOSED",
                "AVOID",
                "TRAFFIC",
                "SEGMENT",
                "LEG",
                "ROAD",
                "STREET",
                "UNAVAILABLE",
                "BECOMES UNAVAILABLE",
                "ACIDENTE",
                "BLOQUEIO",
                "BLOQUEADA",
                "BLOQUEADO",
                "FECHADA",
                "FECHADO",
                "EVITAR",
                "TRÂNSITO",
                "TRANSITO",
                "TRECHO",
                "VIA",
                "RUA",
            )
        ):
            return None
        ids = _ordered_ids(upper_text)
        valid_ids = [node_id for node_id in ids if node_id in node_ids]
        if len(valid_ids) < 2:
            if any(keyword in upper_text for keyword in ("CUSTOMER", "DELIVERY", "RECEIVE", "CLIENTE", "ENTREGA", "RECEBER")):
                return None
            return EventExtractionResult(
                event=None,
                confidence=0.2,
                method="rule_based",
                error="Blockage event detected, but two valid nodes were not found.",
            )
        from_node, to_node = valid_ids[0], valid_ids[1]
        return EventExtractionResult(
            event=OperationalEvent(
                type=EventType.BLOCK_ARC,
                payload={"from_node": from_node, "to_node": to_node, "bidirectional": True},
                description=original_text,
            ),
            confidence=0.85,
            method="rule_based",
        )

    def _extract_customer_unavailable(
        self,
        original_text: str,
        upper_text: str,
        customer_ids: set[str],
    ) -> EventExtractionResult | None:
        unavailable_keywords = (
            "UNAVAILABLE",
            "CANNOT RECEIVE",
            "CAN'T RECEIVE",
            "NOT AVAILABLE",
            "CLOSED",
            "INDISPONÍVEL",
            "INDISPONIVEL",
            "NÃO PODE RECEBER",
            "NAO PODE RECEBER",
            "NÃO CONSEGUE RECEBER",
            "NAO CONSEGUE RECEBER",
            "FECHADO",
            "FECHADA",
        )
        if not any(keyword in upper_text for keyword in unavailable_keywords):
            return None
        ids = [node_id for node_id in _ordered_ids(upper_text) if node_id in customer_ids]
        if not ids:
            return EventExtractionResult(
                event=None,
                confidence=0.2,
                method="rule_based",
                error="Unavailable customer event detected, but no valid customer was found.",
            )
        return EventExtractionResult(
            event=OperationalEvent(
                type=EventType.CUSTOMER_UNAVAILABLE,
                payload={"customer_id": ids[0]},
                description=original_text,
            ),
            confidence=0.9,
            method="rule_based",
        )

    def _extract_priority_change(
        self,
        original_text: str,
        upper_text: str,
        customer_ids: set[str],
    ) -> EventExtractionResult | None:
        if not any(keyword in upper_text for keyword in ("URGENT", "PRIORITY", "HIGH PRIORITY", "URGENTE", "PRIORIDADE")):
            return None
        ids = [node_id for node_id in _ordered_ids(upper_text) if node_id in customer_ids]
        if not ids:
            return EventExtractionResult(
                event=None,
                confidence=0.2,
                method="rule_based",
                error="Priority event detected, but no valid customer was found.",
            )
        return EventExtractionResult(
            event=OperationalEvent(
                type=EventType.CUSTOMER_PRIORITY_CHANGE,
                payload={"customer_id": ids[0], "priority": 3},
                description=original_text,
            ),
            confidence=0.8,
            method="rule_based",
        )


class LlmEventExtractor:
    """Provider-backed event extractor with deterministic fallback.

    The LLM is allowed to propose only a structured event. The event is checked
    against the current scenario before it is accepted. If the provider is not
    configured, unavailable, or returns invalid JSON, extraction falls back to
    the rule-based implementation.
    """

    def __init__(self, client: OpenAICompatibleChatClient | None = None, fallback: EventExtractor | None = None):
        self._client = client
        self._fallback = fallback or RuleBasedEventExtractor()

    def extract(self, text: str, scenario: RoutingScenario) -> EventExtractionResult:
        if _looks_like_context_follow_up(text):
            deterministic = self._fallback.extract(text, scenario)
            if deterministic.event is None:
                return EventExtractionResult(
                    event=None,
                    confidence=0.7,
                    method="context_follow_up",
                    error="No new operational event detected.",
                )

        if self._client is None:
            return self._fallback_with_method(text, scenario, method="llm_not_configured_with_rule_fallback")

        try:
            response = self._client.chat(
                system=_EVENT_EXTRACTION_SYSTEM_PROMPT,
                user=json.dumps(
                    {
                        "user_message": text,
                        "scenario": _scenario_event_context(scenario),
                    },
                    separators=(",", ":"),
                ),
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            payload = _extract_json_object(response.content)
            event = _event_from_llm_payload(payload, text, scenario)
            if event is None:
                return self._fallback_with_method(text, scenario, method="llm_invalid_with_rule_fallback")
            return EventExtractionResult(event=event, confidence=0.75, method=f"llm:{response.model}")
        except Exception as exc:
            fallback = self._fallback.extract(text, scenario)
            return EventExtractionResult(
                event=fallback.event,
                confidence=fallback.confidence,
                method="llm_error_with_rule_fallback",
                error=fallback.error or str(exc),
            )

    def _fallback_with_method(self, text: str, scenario: RoutingScenario, method: str) -> EventExtractionResult:
        fallback = self._fallback.extract(text, scenario)
        if fallback.event is None:
            return EventExtractionResult(
                event=None,
                confidence=fallback.confidence,
                method=method,
                error=fallback.error,
            )
        return EventExtractionResult(
            event=fallback.event,
            confidence=fallback.confidence,
            method=method,
        )


def _ordered_ids(text: str) -> list[str]:
    return [match.group(0).upper() for match in re.finditer(r"\b(?:D|C)\d+\b", text)]


def _looks_like_context_follow_up(text: str) -> bool:
    upper_text = " ".join(text.strip().upper().split())
    if not upper_text:
        return False

    follow_up_markers = (
        "CONFIRM",
        "EXPLAIN",
        "SHOW",
        "SUMMARIZE",
        "SUMMARY",
        "WHAT IS",
        "WHETHER",
        "ANTES",
        "CONFIRME",
        "EXPLIQUE",
        "MOSTRE",
        "RESUMA",
        "QUAL",
        "QUAIS",
    )
    event_markers = (
        "ACCIDENT",
        "BLOCK",
        "BLOCKED",
        "CLOSED",
        "AVOID",
        "TRAFFIC",
        "UNAVAILABLE",
        "CANNOT RECEIVE",
        "CAN'T RECEIVE",
        "NOT AVAILABLE",
        "URGENT",
        "PRIORITY",
        "ACIDENTE",
        "BLOQUEIO",
        "BLOQUEADA",
        "BLOQUEADO",
        "FECHADA",
        "FECHADO",
        "EVITAR",
        "TRÂNSITO",
        "TRANSITO",
        "INDISPONÍVEL",
        "INDISPONIVEL",
        "NÃO PODE RECEBER",
        "NAO PODE RECEBER",
        "URGENTE",
        "PRIORIDADE",
    )
    return any(marker in upper_text for marker in follow_up_markers) and not any(
        marker in upper_text for marker in event_markers
    )


_EVENT_EXTRACTION_SYSTEM_PROMPT = """You extract operational routing events from user messages.
Return only a JSON object with this schema:
{"type":"BLOCK_ARC|CUSTOMER_UNAVAILABLE|CUSTOMER_PRIORITY_CHANGE|null","payload":{}}

Rules:
- Use only node/customer ids present in the scenario.
- BLOCK_ARC payload: {"from_node":"...","to_node":"...","bidirectional":true}
- CUSTOMER_UNAVAILABLE payload: {"customer_id":"..."}
- CUSTOMER_PRIORITY_CHANGE payload: {"customer_id":"...","priority":3}
- Treat "segment/leg/road between Cx and Cy is unavailable", "traffic between Cx and Cy",
  "blocked road between Cx and Cy", and equivalent phrasing as BLOCK_ARC.
- Treat "customer Cx cannot receive/is unavailable" as CUSTOMER_UNAVAILABLE.
- If no supported event is present, return {"type":null,"payload":{}}.
"""


def _scenario_event_context(scenario: RoutingScenario) -> dict[str, Any]:
    payload = scenario_to_dict(scenario)
    return {
        "id": payload["id"],
        "depot": payload["depot"]["id"],
        "customers": [
            {"id": customer["id"], "active": customer["active"], "demand": customer["demand"]}
            for customer in payload["customers"]
        ],
        "vehicles": payload["vehicles"],
        "blocked_arcs": payload["blocked_arcs"],
    }


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    decoded = json.loads(stripped)
    if not isinstance(decoded, dict):
        raise ValueError("LLM event extraction output must be a JSON object.")
    return decoded


def _event_from_llm_payload(payload: dict[str, Any], original_text: str, scenario: RoutingScenario) -> OperationalEvent | None:
    event_type = payload.get("type")
    event_payload = payload.get("payload")
    if event_type is None or event_type == "null":
        return None
    if not isinstance(event_type, str) or not isinstance(event_payload, dict):
        return None

    try:
        parsed_type = EventType(event_type)
    except ValueError:
        return None

    known_node_ids = {scenario.depot.id, *(customer.id for customer in scenario.customers)}
    customer_ids = {customer.id for customer in scenario.customers}

    if parsed_type == EventType.BLOCK_ARC:
        from_node = str(event_payload.get("from_node", "")).upper()
        to_node = str(event_payload.get("to_node", "")).upper()
        if from_node not in known_node_ids or to_node not in known_node_ids or from_node == to_node:
            return None
        return OperationalEvent(
            type=parsed_type,
            payload={
                "from_node": from_node,
                "to_node": to_node,
                "bidirectional": bool(event_payload.get("bidirectional", True)),
            },
            description=original_text,
        )

    if parsed_type == EventType.CUSTOMER_UNAVAILABLE:
        customer_id = str(event_payload.get("customer_id", "")).upper()
        if customer_id not in customer_ids:
            return None
        return OperationalEvent(type=parsed_type, payload={"customer_id": customer_id}, description=original_text)

    if parsed_type == EventType.CUSTOMER_PRIORITY_CHANGE:
        customer_id = str(event_payload.get("customer_id", "")).upper()
        if customer_id not in customer_ids:
            return None
        return OperationalEvent(
            type=parsed_type,
            payload={"customer_id": customer_id, "priority": int(event_payload.get("priority", 3))},
            description=original_text,
        )

    return None
