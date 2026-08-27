from __future__ import annotations

import pytest

from adaptiveroute.agentic.agents import ApplyEventAgent, ExtractEventAgent, RoutingWorkflowAgent, SolveBaseAgent
from adaptiveroute.data.demo_scenario import build_demo_scenario
from adaptiveroute.services.event_extraction import RuleBasedEventExtractor
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine


def test_base_agent_is_abstract() -> None:
    with pytest.raises(TypeError):
        RoutingWorkflowAgent(name="base")  # type: ignore[abstract]


def test_solve_base_agent_adds_trace_and_valid_plan() -> None:
    agent = SolveBaseAgent(PyomoHighsEngine())

    update = agent({"scenario": build_demo_scenario(), "trace": [], "errors": []})

    assert update["base_plan"].scenario_id == "demo-cvrp-8"
    assert update["base_validation"].passed
    assert update["trace"][-1]["node"] == "solve_base"


def test_event_and_apply_agents_are_composable() -> None:
    scenario = build_demo_scenario()
    extraction_update = ExtractEventAgent(event_extractor=RuleBasedEventExtractor())(
        {
            "scenario": scenario,
            "user_message": "Customer C3 cannot receive now.",
            "trace": [],
            "errors": [],
        }
    )

    assert extraction_update["event"].payload == {"customer_id": "C3"}

    apply_update = ApplyEventAgent()(
        {
            "scenario": scenario,
            "event": extraction_update["event"],
            "trace": extraction_update["trace"],
            "errors": [],
        }
    )

    assert apply_update["replanning_scenario"].id.endswith("unavailable-C3")
    assert apply_update["trace"][-1]["node"] == "apply_event"
