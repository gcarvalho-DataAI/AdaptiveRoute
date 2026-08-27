from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.services.event_extraction import RuleBasedEventExtractor
from adaptiveroute.services.harness import AdaptiveRouteHarness
from adaptiveroute.services.replanning import ReplanningService
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine


def test_harness_runs_natural_language_replanning() -> None:
    scenario = build_demo_scenario()
    harness = AdaptiveRouteHarness(
        extractor=RuleBasedEventExtractor(),
        replanning_service=ReplanningService(PyomoHighsEngine()),
    )

    result = harness.run(scenario, "There was an accident between C7 and C6. Avoid that road.")

    assert result.succeeded
    assert result.extraction.event is not None
    assert result.replanning is not None
    assert result.replanning.comparison is not None
    assert result.replanning.comparison.distance_delta > 0


def test_harness_stops_when_extraction_fails() -> None:
    scenario = build_demo_scenario()
    harness = AdaptiveRouteHarness(
        extractor=RuleBasedEventExtractor(),
        replanning_service=ReplanningService(PyomoHighsEngine()),
    )

    result = harness.run(scenario, "Can you make this more optimized somehow?")

    assert not result.succeeded
    assert result.extraction.event is None
    assert result.replanning is None
