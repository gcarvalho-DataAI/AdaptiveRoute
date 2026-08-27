from __future__ import annotations

from typing import Any, TypedDict

from adaptiveroute.domain.events import MutationResult, OperationalEvent
from adaptiveroute.domain.models import RoutingPlan, RoutingScenario, SolverResult, ValidationResult
from adaptiveroute.services.comparison import PlanComparison
from adaptiveroute.services.event_extraction import EventExtractionResult


class RoutingWorkflowState(TypedDict, total=False):
    user_message: str
    context_window: dict[str, Any] | None
    scenario: RoutingScenario

    event_extraction: EventExtractionResult
    event: OperationalEvent

    base_result: SolverResult
    base_plan: RoutingPlan
    base_validation: ValidationResult

    replanning_scenario: RoutingScenario
    mutation: MutationResult

    candidate_plan: RoutingPlan
    candidate_source: str
    candidate_validation: ValidationResult

    repaired_plan: RoutingPlan
    repaired_validation: ValidationResult

    fallback_result: SolverResult
    final_plan: RoutingPlan
    final_validation: ValidationResult
    final_source: str
    comparison: PlanComparison

    trace: list[dict[str, Any]]
    errors: list[str]
    response: dict[str, Any]
