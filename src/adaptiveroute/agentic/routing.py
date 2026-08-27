from __future__ import annotations

from adaptiveroute.agentic.state import RoutingWorkflowState


def route_after_event_extraction(state: RoutingWorkflowState) -> str:
    return "solve_base" if state.get("event") is not None else "compose_response"


def route_after_base_validation(state: RoutingWorkflowState) -> str:
    validation = state.get("base_validation")
    if validation is None or not validation.passed:
        return "compose_response"
    return "apply_event"


def route_after_candidate_validation(state: RoutingWorkflowState) -> str:
    validation = state.get("candidate_validation")
    if validation is not None and validation.passed:
        return "compose_response"
    return "repair_candidate"


def route_after_repair_validation(state: RoutingWorkflowState) -> str:
    validation = state.get("repaired_validation")
    if validation is not None and validation.passed:
        return "compose_response"
    return "solver_fallback"
