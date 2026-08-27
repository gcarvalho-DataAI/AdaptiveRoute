from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.domain.events import EventType, OperationalEvent
from adaptiveroute.services.replanning import ReplanningService
from adaptiveroute.services.reports import build_dispatch_report, replanning_result_to_dict
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine


def test_replanning_service_orchestrates_block_arc_replan() -> None:
    scenario = build_demo_scenario()
    event = OperationalEvent(
        type=EventType.BLOCK_ARC,
        payload={"from_node": "C7", "to_node": "C6", "bidirectional": True},
        description="There is an accident between C7 and C6.",
    )

    result = ReplanningService(PyomoHighsEngine()).replan(scenario, event)

    assert result.succeeded
    assert result.comparison is not None
    assert result.comparison.distance_delta > 0
    assert result.replanned_validation is not None
    assert result.replanned_validation.passed


def test_replanning_result_serializes_and_builds_report() -> None:
    scenario = build_demo_scenario()
    event = OperationalEvent(
        type=EventType.CUSTOMER_UNAVAILABLE,
        payload={"customer_id": "C3"},
        description="Customer C3 cannot receive now.",
    )

    result = ReplanningService(PyomoHighsEngine()).replan(scenario, event)
    payload = replanning_result_to_dict(result)
    report = build_dispatch_report(result)

    assert payload["succeeded"] is True
    assert payload["comparison"]["removed_customers"] == ["C3"]
    assert "AdaptiveRoute Dispatch Report" in report
    assert "C3" in report
