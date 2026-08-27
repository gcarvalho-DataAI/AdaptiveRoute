from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from adaptiveroute.agentic.candidates import (
    ApiRoutingCandidateGenerator,
    RoutingCandidateGenerator,
    SolverBackedCandidateGenerator,
    build_routing_candidate_generator_from_env,
)
from adaptiveroute.agentic.graph import build_routing_graph
from adaptiveroute.config import load_project_env
from adaptiveroute.domain.models import RoutingPlan, RoutingScenario, ValidationResult
from adaptiveroute.llm.openai_compatible import OpenAICompatibleChatClient, OpenAICompatibleSettings
from adaptiveroute.services.event_extraction import EventExtractor, LlmEventExtractor, RuleBasedEventExtractor
from adaptiveroute.solvers.base import RoutingEngine


@dataclass(frozen=True)
class AgenticRoutingResult:
    succeeded: bool
    source: str | None
    plan: RoutingPlan | None
    validation: ValidationResult | None
    response: dict[str, Any]
    state: dict[str, Any]


class AgenticRoutingService:
    def __init__(
        self,
        engine: RoutingEngine,
        *,
        event_extractor: EventExtractor | None = None,
        candidate_generator: RoutingCandidateGenerator | None = None,
    ):
        self._engine = engine
        self._event_extractor = event_extractor or RuleBasedEventExtractor()
        self._candidate_generator = candidate_generator or SolverBackedCandidateGenerator(engine, source="solver_candidate")
        self._graph = build_routing_graph(
            engine=self._engine,
            event_extractor=self._event_extractor,
            candidate_generator=self._candidate_generator,
        )

    @classmethod
    def with_openai_compatible_orchestrator(
        cls,
        engine: RoutingEngine,
        *,
        settings: OpenAICompatibleSettings | None = None,
        candidate_generator: RoutingCandidateGenerator | None = None,
    ) -> "AgenticRoutingService":
        client = OpenAICompatibleChatClient(settings or OpenAICompatibleSettings.from_env())
        return cls(
            engine,
            event_extractor=LlmEventExtractor(client=client, fallback=RuleBasedEventExtractor()),
            candidate_generator=candidate_generator,
        )

    @classmethod
    def with_openai_compatible_models(
        cls,
        engine: RoutingEngine,
        *,
        orchestrator_settings: OpenAICompatibleSettings | None = None,
        routing_policy_settings: OpenAICompatibleSettings | None = None,
    ) -> "AgenticRoutingService":
        orchestrator_client = OpenAICompatibleChatClient(
            orchestrator_settings or OpenAICompatibleSettings.from_env(prefix="ADAPTIVEROUTE_ORCHESTRATOR")
        )
        routing_client = OpenAICompatibleChatClient(
            routing_policy_settings or OpenAICompatibleSettings.from_env(prefix="ADAPTIVEROUTE_ROUTING_POLICY")
        )
        return cls(
            engine,
            event_extractor=LlmEventExtractor(client=orchestrator_client, fallback=RuleBasedEventExtractor()),
            candidate_generator=ApiRoutingCandidateGenerator(client=routing_client),
        )

    @classmethod
    def from_env(cls, engine: RoutingEngine) -> "AgenticRoutingService":
        load_project_env()
        orchestrator_backend = os.getenv("ADAPTIVEROUTE_ORCHESTRATOR_BACKEND", "rules").strip().lower()
        candidate_generator = build_routing_candidate_generator_from_env(engine)
        if orchestrator_backend in {"api", "openai-compatible", "openai_compatible"}:
            return cls.with_openai_compatible_orchestrator(
                engine,
                settings=OpenAICompatibleSettings.from_env(prefix="ADAPTIVEROUTE_ORCHESTRATOR"),
                candidate_generator=candidate_generator,
            )
        if orchestrator_backend in {"rules", "rule", "rule-based", "rule_based", ""}:
            return cls(engine, candidate_generator=candidate_generator)
        raise ValueError(
            "Unsupported ADAPTIVEROUTE_ORCHESTRATOR_BACKEND. "
            "Use one of: rules, api."
        )

    def run(
        self,
        scenario: RoutingScenario,
        user_message: str,
        *,
        context_window: dict[str, Any] | None = None,
    ) -> AgenticRoutingResult:
        state = self._graph.invoke(
            {
                "scenario": scenario,
                "user_message": user_message,
                "context_window": context_window,
                "trace": [],
                "errors": [],
            }
        )
        response = state.get("response", {})
        plan = state.get("final_plan")
        validation = state.get("final_validation")
        return AgenticRoutingResult(
            succeeded=bool(response.get("succeeded", False)),
            source=response.get("source"),
            plan=plan,
            validation=validation,
            response=response,
            state=state,
        )
