from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from adaptiveroute.agentic.candidates import RoutingCandidateGenerator
from adaptiveroute.agentic.repair import repair_candidate_plan
from adaptiveroute.agentic.state import RoutingWorkflowState
from adaptiveroute.domain.serialization import (
    event_to_dict,
    plan_to_dict,
    scenario_to_dict,
    validation_to_dict,
)
from adaptiveroute.services.comparison import compare_plans, comparison_to_dict
from adaptiveroute.services.event_extraction import EventExtractor
from adaptiveroute.services.mutations import apply_event
from adaptiveroute.services.validation import validate_plan
from adaptiveroute.solvers.base import RoutingEngine


@dataclass(frozen=True)
class RoutingWorkflowAgent(ABC):
    """Base class for all LangGraph node agents in the routing workflow."""

    name: str

    def __call__(self, state: RoutingWorkflowState) -> RoutingWorkflowState:
        return self.run(state)

    @abstractmethod
    def run(self, state: RoutingWorkflowState) -> RoutingWorkflowState:
        """Execute one workflow step and return a partial state update."""

    def trace(self, state: RoutingWorkflowState, payload: dict[str, Any]) -> list[dict[str, Any]]:
        return [*state.get("trace", []), {"node": self.name, "payload": payload}]

    def errors(self, state: RoutingWorkflowState, message: str) -> list[str]:
        return [*state.get("errors", []), message]


class ExtractEventAgent(RoutingWorkflowAgent):
    def __init__(self, event_extractor: EventExtractor):
        super().__init__(name="extract_event")
        self._event_extractor = event_extractor

    def run(self, state: RoutingWorkflowState) -> RoutingWorkflowState:
        scenario = state["scenario"]
        result = self._event_extractor.extract(state.get("user_message", ""), scenario)
        update: RoutingWorkflowState = {
            "event_extraction": result,
            "trace": self.trace(state, {"method": result.method, "confidence": result.confidence}),
        }
        if result.event is not None:
            update["event"] = result.event
        else:
            update["errors"] = self.errors(state, result.error or "Could not extract an operational event.")
        return update


class SolveBaseAgent(RoutingWorkflowAgent):
    def __init__(self, engine: RoutingEngine):
        super().__init__(name="solve_base")
        self._engine = engine

    def run(self, state: RoutingWorkflowState) -> RoutingWorkflowState:
        scenario = state["scenario"]
        result = self._engine.solve(scenario)
        update: RoutingWorkflowState = {
            "base_result": result,
            "trace": self.trace(state, {"status": result.status.value, "solve_time_ms": result.solve_time_ms}),
        }
        if result.plan is None:
            update["errors"] = self.errors(state, result.message or "Base scenario solve failed.")
            return update

        validation = validate_plan(scenario, result.plan)
        update["base_plan"] = result.plan
        update["base_validation"] = validation
        if not validation.passed:
            update["errors"] = self.errors(state, "Base plan failed deterministic validation.")
        return update


class ApplyEventAgent(RoutingWorkflowAgent):
    def __init__(self):
        super().__init__(name="apply_event")

    def run(self, state: RoutingWorkflowState) -> RoutingWorkflowState:
        replanning_scenario, mutation = apply_event(state["scenario"], state["event"])
        return {
            "replanning_scenario": replanning_scenario,
            "mutation": mutation,
            "trace": self.trace(state, {"event": event_to_dict(state["event"]), "mutation_diff": mutation.diff}),
        }


class GenerateCandidateAgent(RoutingWorkflowAgent):
    def __init__(self, candidate_generator: RoutingCandidateGenerator):
        super().__init__(name="generate_candidate")
        self._candidate_generator = candidate_generator

    def run(self, state: RoutingWorkflowState) -> RoutingWorkflowState:
        result = self._candidate_generator.generate(
            scenario=state["replanning_scenario"],
            event=state["event"],
            base_plan=state["base_plan"],
        )
        update: RoutingWorkflowState = {
            "candidate_source": result.source,
            "trace": self.trace(state, {"source": result.source, "message": result.message}),
        }
        if result.plan is None:
            update["errors"] = self.errors(state, result.message or "Candidate generation failed.")
        else:
            update["candidate_plan"] = result.plan
        return update


class ValidateCandidateAgent(RoutingWorkflowAgent):
    def __init__(self):
        super().__init__(name="validate_candidate")

    def run(self, state: RoutingWorkflowState) -> RoutingWorkflowState:
        plan = state.get("candidate_plan")
        if plan is None:
            return {"trace": self.trace(state, {"passed": False, "reason": "missing_candidate"})}

        validation = validate_plan(state["replanning_scenario"], plan)
        update: RoutingWorkflowState = {
            "candidate_validation": validation,
            "trace": self.trace(state, validation_to_dict(validation)),
        }
        if validation.passed:
            update["final_plan"] = plan
            update["final_validation"] = validation
            update["final_source"] = state.get("candidate_source", "candidate")
            update["comparison"] = compare_plans(
                state["scenario"],
                state["base_plan"],
                state["replanning_scenario"],
                plan,
            )
        return update


class RepairCandidateAgent(RoutingWorkflowAgent):
    def __init__(self):
        super().__init__(name="repair_candidate")

    def run(self, state: RoutingWorkflowState) -> RoutingWorkflowState:
        plan = state.get("candidate_plan")
        if plan is None:
            return {"trace": self.trace(state, {"attempted": False, "reason": "missing_candidate"})}

        repaired = repair_candidate_plan(state["replanning_scenario"], plan)
        validation = validate_plan(state["replanning_scenario"], repaired)
        update: RoutingWorkflowState = {
            "repaired_plan": repaired,
            "repaired_validation": validation,
            "trace": self.trace(state, validation_to_dict(validation)),
        }
        if validation.passed:
            update["final_plan"] = repaired
            update["final_validation"] = validation
            update["final_source"] = f"{state.get('candidate_source', 'candidate')}_repaired"
            update["comparison"] = compare_plans(
                state["scenario"],
                state["base_plan"],
                state["replanning_scenario"],
                repaired,
            )
        return update


class SolverFallbackAgent(RoutingWorkflowAgent):
    def __init__(self, engine: RoutingEngine):
        super().__init__(name="solver_fallback")
        self._engine = engine

    def run(self, state: RoutingWorkflowState) -> RoutingWorkflowState:
        result = self._engine.solve(state["replanning_scenario"])
        update: RoutingWorkflowState = {
            "fallback_result": result,
            "trace": self.trace(state, {"status": result.status.value, "solve_time_ms": result.solve_time_ms}),
        }
        if result.plan is None:
            update["errors"] = self.errors(state, result.message or "Solver fallback failed.")
            return update

        validation = validate_plan(state["replanning_scenario"], result.plan)
        update["final_plan"] = result.plan
        update["final_validation"] = validation
        update["final_source"] = "solver_fallback"
        if validation.passed:
            update["comparison"] = compare_plans(
                state["scenario"],
                state["base_plan"],
                state["replanning_scenario"],
                result.plan,
            )
        else:
            update["errors"] = self.errors(state, "Solver fallback produced an invalid plan.")
        return update


class ComposeResponseAgent(RoutingWorkflowAgent):
    def __init__(self):
        super().__init__(name="compose_response")

    def run(self, state: RoutingWorkflowState) -> RoutingWorkflowState:
        if state.get("event") is None and state.get("context_window"):
            trace = self.trace(state, {"succeeded": True, "mode": "context_follow_up"})
            context_window = state.get("context_window") or {}
            response: dict[str, Any] = {
                "succeeded": True,
                "source": "context_window",
                "errors": [],
                "event": context_window.get("last_event"),
                "base_plan": None,
                "replanning_scenario": None,
                "candidate": {"source": None, "plan": None, "validation": None},
                "repaired": {"plan": None, "validation": None},
                "final_plan": context_window.get("last_plan"),
                "final_validation": None,
                "comparison": None,
                "context_summary": context_window.get("summary"),
                "trace": trace,
            }
            return {"response": response, "trace": trace}

        final_plan = state.get("final_plan")
        final_validation = state.get("final_validation")
        succeeded = bool(final_plan is not None and final_validation is not None and final_validation.passed)
        trace = self.trace(state, {"succeeded": succeeded})
        response: dict[str, Any] = {
            "succeeded": succeeded,
            "source": state.get("final_source"),
            "errors": state.get("errors", []),
            "event": event_to_dict(state["event"]) if state.get("event") else None,
            "base_plan": plan_to_dict(state["base_plan"]) if state.get("base_plan") else None,
            "replanning_scenario": scenario_to_dict(state["replanning_scenario"])
            if state.get("replanning_scenario")
            else None,
            "candidate": {
                "source": state.get("candidate_source"),
                "plan": plan_to_dict(state["candidate_plan"]) if state.get("candidate_plan") else None,
                "validation": validation_to_dict(state["candidate_validation"])
                if state.get("candidate_validation")
                else None,
            },
            "repaired": {
                "plan": plan_to_dict(state["repaired_plan"]) if state.get("repaired_plan") else None,
                "validation": validation_to_dict(state["repaired_validation"])
                if state.get("repaired_validation")
                else None,
            },
            "final_plan": plan_to_dict(final_plan) if final_plan else None,
            "final_validation": validation_to_dict(final_validation) if final_validation else None,
            "comparison": comparison_to_dict(state["comparison"]) if state.get("comparison") else None,
            "trace": trace,
        }
        return {"response": response, "trace": trace}
