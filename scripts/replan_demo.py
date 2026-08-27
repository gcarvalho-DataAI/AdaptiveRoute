from __future__ import annotations

import json

from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.domain.events import EventType, OperationalEvent
from adaptiveroute.services.replanning import ReplanningService
from adaptiveroute.services.reports import build_dispatch_report, replanning_result_to_dict
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine


def main() -> int:
    base_scenario = build_demo_scenario()

    # This blocks an edge used by the current demo optimum, forcing a real replan.
    event = OperationalEvent(
        type=EventType.BLOCK_ARC,
        payload={"from_node": "C7", "to_node": "C6", "bidirectional": True},
        description="There is an accident between C7 and C6. Avoid that road.",
    )
    result = ReplanningService(PyomoHighsEngine()).replan(base_scenario, event)

    print(build_dispatch_report(result))
    print()
    print(json.dumps(replanning_result_to_dict(result), indent=2, sort_keys=True))
    return 0 if result.succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
