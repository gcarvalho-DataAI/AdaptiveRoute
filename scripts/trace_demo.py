from __future__ import annotations

from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.domain.events import EventType, OperationalEvent
from adaptiveroute.services.replanning import ReplanningService
from adaptiveroute.services.tracing import JsonlTraceLogger
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine


def main() -> int:
    scenario = build_demo_scenario()
    event = OperationalEvent(
        type=EventType.BLOCK_ARC,
        payload={"from_node": "C7", "to_node": "C6", "bidirectional": True},
        description="There is an accident between C7 and C6. Avoid that road.",
    )
    logger = JsonlTraceLogger()
    result = ReplanningService(PyomoHighsEngine(), trace_logger=logger).replan(scenario, event)
    print(f"Trace ID: {result.trace_id}")
    print(f"Trace file: outputs/traces/{result.trace_id}.jsonl")
    print(f"Succeeded: {result.succeeded}")
    return 0 if result.succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
