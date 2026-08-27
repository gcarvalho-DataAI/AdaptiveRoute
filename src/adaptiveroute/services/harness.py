from __future__ import annotations

from dataclasses import dataclass

from adaptiveroute.domain.models import RoutingScenario
from adaptiveroute.services.event_extraction import EventExtractionResult, EventExtractor
from adaptiveroute.services.replanning import ReplanningResult, ReplanningService


@dataclass(frozen=True)
class HarnessRunResult:
    extraction: EventExtractionResult
    replanning: ReplanningResult | None

    @property
    def succeeded(self) -> bool:
        return self.extraction.event is not None and self.replanning is not None and self.replanning.succeeded


class AdaptiveRouteHarness:
    def __init__(self, extractor: EventExtractor, replanning_service: ReplanningService):
        self._extractor = extractor
        self._replanning_service = replanning_service

    def run(self, scenario: RoutingScenario, user_text: str) -> HarnessRunResult:
        extraction = self._extractor.extract(user_text, scenario)
        if extraction.event is None:
            return HarnessRunResult(extraction=extraction, replanning=None)
        replanning = self._replanning_service.replan(scenario, extraction.event)
        return HarnessRunResult(extraction=extraction, replanning=replanning)

