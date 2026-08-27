from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from adaptiveroute.domain.events import MutationResult, OperationalEvent
from adaptiveroute.domain.models import RoutingPlan, RoutingScenario, SolverResult, ValidationResult
from adaptiveroute.domain.serialization import event_to_dict, plan_to_dict, scenario_to_dict, validation_to_dict
from adaptiveroute.services.comparison import PlanComparison, compare_plans
from adaptiveroute.services.comparison import comparison_to_dict
from adaptiveroute.services.mutations import apply_event
from adaptiveroute.services.tracing import InMemoryTraceLogger
from adaptiveroute.services.validation import validate_plan
from adaptiveroute.solvers.base import RoutingEngine


@dataclass(frozen=True)
class ReplanningResult:
    base_scenario: RoutingScenario
    replanning_scenario: RoutingScenario | None
    event: OperationalEvent
    mutation: MutationResult | None
    base_result: SolverResult
    replanned_result: SolverResult | None
    base_validation: ValidationResult | None
    replanned_validation: ValidationResult | None
    comparison: PlanComparison | None
    trace_id: str

    @property
    def succeeded(self) -> bool:
        return (
            self.base_result.plan is not None
            and self.replanned_result is not None
            and self.replanned_result.plan is not None
            and self.base_validation is not None
            and self.base_validation.passed
            and self.replanned_validation is not None
            and self.replanned_validation.passed
            and self.comparison is not None
        )


class ReplanningService:
    def __init__(self, engine: RoutingEngine, trace_logger: InMemoryTraceLogger | None = None):
        self._engine = engine
        self._trace_logger = trace_logger

    def replan(self, scenario: RoutingScenario, event: OperationalEvent) -> ReplanningResult:
        trace_id = str(uuid4())
        self._trace(
            trace_id,
            "replan:start",
            {"scenario_id": scenario.id, "event": event_to_dict(event)},
        )
        base_result = self._engine.solve(scenario)
        self._trace(
            trace_id,
            "solver:base",
            {
                "status": base_result.status.value,
                "message": base_result.message,
                "solve_time_ms": base_result.solve_time_ms,
                "plan": plan_to_dict(base_result.plan) if base_result.plan else None,
            },
        )
        if base_result.plan is None:
            self._trace(trace_id, "replan:failed", {"reason": "base_solve_failed"})
            return ReplanningResult(
                base_scenario=scenario,
                replanning_scenario=None,
                event=event,
                mutation=None,
                base_result=base_result,
                replanned_result=None,
                base_validation=None,
                replanned_validation=None,
                comparison=None,
                trace_id=trace_id,
            )

        base_validation = validate_plan(scenario, base_result.plan)
        self._trace(trace_id, "validation:base", validation_to_dict(base_validation))
        if not base_validation.passed:
            self._trace(trace_id, "replan:failed", {"reason": "base_validation_failed"})
            return ReplanningResult(
                base_scenario=scenario,
                replanning_scenario=None,
                event=event,
                mutation=None,
                base_result=base_result,
                replanned_result=None,
                base_validation=base_validation,
                replanned_validation=None,
                comparison=None,
                trace_id=trace_id,
            )

        replanning_scenario, mutation = apply_event(scenario, event)
        self._trace(
            trace_id,
            "mutation:applied",
            {
                "mutation_diff": mutation.diff,
                "replanning_scenario": scenario_to_dict(replanning_scenario),
            },
        )
        replanned_result = self._engine.solve(replanning_scenario)
        self._trace(
            trace_id,
            "solver:replanned",
            {
                "status": replanned_result.status.value,
                "message": replanned_result.message,
                "solve_time_ms": replanned_result.solve_time_ms,
                "plan": plan_to_dict(replanned_result.plan) if replanned_result.plan else None,
            },
        )
        if replanned_result.plan is None:
            self._trace(trace_id, "replan:failed", {"reason": "replanned_solve_failed"})
            return ReplanningResult(
                base_scenario=scenario,
                replanning_scenario=replanning_scenario,
                event=event,
                mutation=mutation,
                base_result=base_result,
                replanned_result=replanned_result,
                base_validation=base_validation,
                replanned_validation=None,
                comparison=None,
                trace_id=trace_id,
            )

        replanned_validation = validate_plan(replanning_scenario, replanned_result.plan)
        self._trace(trace_id, "validation:replanned", validation_to_dict(replanned_validation))
        comparison = (
            compare_plans(scenario, base_result.plan, replanning_scenario, replanned_result.plan)
            if replanned_validation.passed
            else None
        )
        if comparison:
            self._trace(trace_id, "comparison:completed", comparison_to_dict(comparison))
            self._trace(trace_id, "replan:succeeded", {"scenario_id": replanning_scenario.id})
        else:
            self._trace(trace_id, "replan:failed", {"reason": "replanned_validation_failed"})

        return ReplanningResult(
            base_scenario=scenario,
            replanning_scenario=replanning_scenario,
            event=event,
            mutation=mutation,
            base_result=base_result,
            replanned_result=replanned_result,
            base_validation=base_validation,
            replanned_validation=replanned_validation,
            comparison=comparison,
            trace_id=trace_id,
        )

    def _trace(self, trace_id: str, event: str, payload: dict) -> None:
        if self._trace_logger is None:
            return
        self._trace_logger.write(event=event, payload=payload, trace_id=trace_id)


def plan_or_none(result: SolverResult) -> RoutingPlan | None:
    return result.plan
