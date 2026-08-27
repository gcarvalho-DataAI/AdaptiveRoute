from __future__ import annotations

import argparse
import json

from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.services.event_extraction import RuleBasedEventExtractor
from adaptiveroute.services.harness import AdaptiveRouteHarness
from adaptiveroute.services.replanning import ReplanningService
from adaptiveroute.services.reports import build_dispatch_report, replanning_result_to_dict
from adaptiveroute.services.tracing import JsonlTraceLogger
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the AdaptiveRoute harness from natural language input.")
    parser.add_argument(
        "event_text",
        nargs="?",
        default="There was an accident between C7 and C6. Avoid that road.",
    )
    args = parser.parse_args()

    scenario = build_demo_scenario()
    harness = AdaptiveRouteHarness(
        extractor=RuleBasedEventExtractor(),
        replanning_service=ReplanningService(PyomoHighsEngine(), trace_logger=JsonlTraceLogger()),
    )
    result = harness.run(scenario, args.event_text)

    print(f"Extraction method: {result.extraction.method}")
    print(f"Confidence: {result.extraction.confidence:.2f}")
    if result.extraction.error:
        print(f"Extraction error: {result.extraction.error}")
    if result.extraction.event is None or result.replanning is None:
        return 1

    print()
    print(build_dispatch_report(result.replanning))
    print()
    print(json.dumps(replanning_result_to_dict(result.replanning), indent=2, sort_keys=True))
    return 0 if result.succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())

