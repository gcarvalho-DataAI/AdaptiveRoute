from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.domain.events import EventType, OperationalEvent
from adaptiveroute.services.replanning import ReplanningService
from adaptiveroute.services.reports import replanning_result_to_dict
from adaptiveroute.services.tracing import InMemoryTraceLogger
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine


def test_replanning_service_emits_trace_records() -> None:
    logger = InMemoryTraceLogger()
    scenario = build_demo_scenario()
    event = OperationalEvent(
        type=EventType.BLOCK_ARC,
        payload={"from_node": "C7", "to_node": "C6", "bidirectional": True},
        description="There is an accident between C7 and C6.",
    )

    result = ReplanningService(PyomoHighsEngine(), trace_logger=logger).replan(scenario, event)

    assert result.succeeded
    assert len(logger.records) >= 7
    assert {record.event for record in logger.records} >= {
        "replan:start",
        "solver:base",
        "validation:base",
        "mutation:applied",
        "solver:replanned",
        "validation:replanned",
        "comparison:completed",
        "replan:succeeded",
    }
    assert {record.trace_id for record in logger.records} == {result.trace_id}


def test_replanning_report_includes_trace_id() -> None:
    logger = InMemoryTraceLogger()
    scenario = build_demo_scenario()
    event = OperationalEvent(
        type=EventType.CUSTOMER_UNAVAILABLE,
        payload={"customer_id": "C3"},
        description="Customer C3 cannot receive now.",
    )

    result = ReplanningService(PyomoHighsEngine(), trace_logger=logger).replan(scenario, event)
    payload = replanning_result_to_dict(result)

    assert payload["trace_id"] == result.trace_id
