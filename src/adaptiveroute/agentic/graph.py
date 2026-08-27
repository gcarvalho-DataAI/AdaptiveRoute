from __future__ import annotations

from langgraph.graph import END, StateGraph

from adaptiveroute.agentic.agents import (
    ApplyEventAgent,
    ComposeResponseAgent,
    ExtractEventAgent,
    GenerateCandidateAgent,
    RepairCandidateAgent,
    SolveBaseAgent,
    SolverFallbackAgent,
    ValidateCandidateAgent,
)
from adaptiveroute.agentic.candidates import RoutingCandidateGenerator
from adaptiveroute.agentic.routing import (
    route_after_base_validation,
    route_after_candidate_validation,
    route_after_event_extraction,
    route_after_repair_validation,
)
from adaptiveroute.agentic.state import RoutingWorkflowState
from adaptiveroute.services.event_extraction import EventExtractor
from adaptiveroute.solvers.base import RoutingEngine


def build_routing_graph(
    *,
    engine: RoutingEngine,
    event_extractor: EventExtractor,
    candidate_generator: RoutingCandidateGenerator,
):
    graph = StateGraph(RoutingWorkflowState)

    graph.add_node("extract_event", ExtractEventAgent(event_extractor))
    graph.add_node("solve_base", SolveBaseAgent(engine))
    graph.add_node("apply_event", ApplyEventAgent())
    graph.add_node("generate_candidate", GenerateCandidateAgent(candidate_generator))
    graph.add_node("validate_candidate", ValidateCandidateAgent())
    graph.add_node("repair_candidate", RepairCandidateAgent())
    graph.add_node("solver_fallback", SolverFallbackAgent(engine))
    graph.add_node("compose_response", ComposeResponseAgent())

    graph.set_entry_point("extract_event")
    graph.add_conditional_edges(
        "extract_event",
        route_after_event_extraction,
        {"solve_base": "solve_base", "compose_response": "compose_response"},
    )
    graph.add_conditional_edges(
        "solve_base",
        route_after_base_validation,
        {"apply_event": "apply_event", "compose_response": "compose_response"},
    )
    graph.add_edge("apply_event", "generate_candidate")
    graph.add_edge("generate_candidate", "validate_candidate")
    graph.add_conditional_edges(
        "validate_candidate",
        route_after_candidate_validation,
        {"repair_candidate": "repair_candidate", "compose_response": "compose_response"},
    )
    graph.add_conditional_edges(
        "repair_candidate",
        route_after_repair_validation,
        {"solver_fallback": "solver_fallback", "compose_response": "compose_response"},
    )
    graph.add_edge("solver_fallback", "compose_response")
    graph.add_edge("compose_response", END)

    return graph.compile()
