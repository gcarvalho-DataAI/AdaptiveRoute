from __future__ import annotations

from adaptiveroute.agentic import AgenticRoutingService
from adaptiveroute.agentic.candidates import CandidateGenerationResult
from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.domain.events import OperationalEvent
from adaptiveroute.domain.models import RoutingPlan, RoutingScenario, VehicleRoute
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine


class InvalidCandidateGenerator:
    def generate(
        self,
        scenario: RoutingScenario,
        event: OperationalEvent,
        base_plan: RoutingPlan,
    ) -> CandidateGenerationResult:
        plan = RoutingPlan(
            scenario_id=scenario.id,
            routes=(VehicleRoute(vehicle_id="V1", stops=("D0", "C1", "D0"), load=4, distance=10.0),),
            total_distance=10.0,
        )
        return CandidateGenerationResult(plan=plan, source="invalid_test_model")


def test_agentic_routing_service_accepts_valid_candidate() -> None:
    service = AgenticRoutingService(PyomoHighsEngine())

    result = service.run(build_demo_scenario(), "There is an accident between C7 and C6.")

    assert result.succeeded
    assert result.source == "solver_candidate"
    assert result.plan is not None
    assert result.validation is not None
    assert result.validation.passed
    assert result.response["candidate"]["source"] == "solver_candidate"
    assert [entry["node"] for entry in result.response["trace"]] == [
        "extract_event",
        "solve_base",
        "apply_event",
        "generate_candidate",
        "validate_candidate",
        "compose_response",
    ]


def test_agentic_routing_service_falls_back_when_candidate_is_invalid() -> None:
    service = AgenticRoutingService(
        PyomoHighsEngine(),
        candidate_generator=InvalidCandidateGenerator(),
    )

    result = service.run(build_demo_scenario(), "Customer C3 cannot receive now.")

    assert result.succeeded
    assert result.source == "solver_fallback"
    assert result.plan is not None
    assert result.validation is not None
    assert result.validation.passed
    assert result.response["candidate"]["source"] == "invalid_test_model"
    assert result.response["candidate"]["validation"]["passed"] is False
    assert any(
        violation["code"] == "missing_customer"
        for violation in result.response["candidate"]["validation"]["violations"]
    )
    assert "solver_fallback" in [entry["node"] for entry in result.response["trace"]]


def test_agentic_routing_service_reports_event_extraction_failure() -> None:
    service = AgenticRoutingService(PyomoHighsEngine())

    result = service.run(build_demo_scenario(), "Please optimize today's delivery plan.")

    assert not result.succeeded
    assert result.source is None
    assert result.plan is None
    assert result.response["event"] is None
    assert result.response["errors"] == ["Could not map text to a supported event."]
