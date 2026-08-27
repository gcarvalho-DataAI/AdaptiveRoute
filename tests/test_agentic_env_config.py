from __future__ import annotations

import os

from adaptiveroute.agentic.candidates import (
    ApiRoutingCandidateGenerator,
    LocalLoraRoutingCandidateGenerator,
    SolverBackedCandidateGenerator,
    build_routing_candidate_generator_from_env,
)
from adaptiveroute.config import load_project_env
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine


def test_load_project_env_does_not_override_existing_env(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "ADAPTIVEROUTE_ROUTING_POLICY_BACKEND=local",
                "EXISTING_VALUE=from_file",
                "QUOTED_VALUE=\"quoted\"",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("EXISTING_VALUE", "from_env")
    monkeypatch.delenv("ADAPTIVEROUTE_ROUTING_POLICY_BACKEND", raising=False)
    monkeypatch.delenv("QUOTED_VALUE", raising=False)

    load_project_env(env_file)

    assert os.environ["ADAPTIVEROUTE_ROUTING_POLICY_BACKEND"] == "local"
    assert os.environ["EXISTING_VALUE"] == "from_env"
    assert os.environ["QUOTED_VALUE"] == "quoted"


def test_routing_candidate_generator_factory_defaults_to_solver(monkeypatch) -> None:
    monkeypatch.delenv("ADAPTIVEROUTE_ROUTING_POLICY_BACKEND", raising=False)

    generator = build_routing_candidate_generator_from_env(PyomoHighsEngine())

    assert isinstance(generator, SolverBackedCandidateGenerator)


def test_routing_candidate_generator_factory_can_select_api(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVEROUTE_ROUTING_POLICY_BACKEND", "api")
    monkeypatch.setenv("ADAPTIVEROUTE_ROUTING_POLICY_BASE_URL", "http://127.0.0.1:1/v1")
    monkeypatch.setenv("ADAPTIVEROUTE_ROUTING_POLICY_API_KEY", "local")
    monkeypatch.setenv("ADAPTIVEROUTE_ROUTING_POLICY_MODEL", "adaptiveroute-routing-policy")

    generator = build_routing_candidate_generator_from_env(PyomoHighsEngine())

    assert isinstance(generator, ApiRoutingCandidateGenerator)


def test_routing_candidate_generator_factory_can_select_local_without_loading(monkeypatch) -> None:
    monkeypatch.setenv("ADAPTIVEROUTE_ROUTING_POLICY_BACKEND", "local")
    monkeypatch.setenv("ADAPTIVEROUTE_ROUTING_POLICY_LOCAL_LOAD_AT_STARTUP", "false")

    generator = build_routing_candidate_generator_from_env(PyomoHighsEngine())

    assert isinstance(generator, LocalLoraRoutingCandidateGenerator)
    assert not generator.loaded
