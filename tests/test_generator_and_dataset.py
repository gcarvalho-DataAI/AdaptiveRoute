from adaptiveroute.data.generator import generate_scenario
from adaptiveroute.domain.serialization import scenario_to_dict
from adaptiveroute.services.validation import validate_plan
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine
from adaptiveroute.training.dataset_builder import build_sft_examples


def test_generated_scenario_solves() -> None:
    scenario = generate_scenario(seed=123, num_customers=7, num_vehicles=2)
    result = PyomoHighsEngine().solve(scenario)

    assert result.plan is not None
    assert validate_plan(scenario, result.plan).passed


def test_scenario_serialization_has_json_safe_distance_matrix() -> None:
    scenario = generate_scenario(seed=123, num_customers=4, num_vehicles=2)
    payload = scenario_to_dict(scenario)

    assert isinstance(payload["distance_matrix"], list)
    assert {"from", "to", "distance"} <= set(payload["distance_matrix"][0])


def test_build_sft_examples_writes_valid_rows() -> None:
    examples, stats = build_sft_examples(n=3, seed_start=200, num_customers=6, num_vehicles=2)

    assert stats.written == 3
    assert len(examples) == 3
    assert examples[0]["instruction"]
    assert examples[0]["input"]["base_scenario"]
    assert examples[0]["input"]["event"]["type"] in {"BLOCK_ARC", "CUSTOMER_UNAVAILABLE"}
    assert examples[0]["output"]["routes"]
    assert examples[0]["metadata"]["validation"]["passed"] is True


def test_build_sft_examples_supports_compact_format() -> None:
    examples, stats = build_sft_examples(
        n=2,
        seed_start=300,
        num_customers=6,
        num_vehicles=2,
        output_format="compact",
    )

    assert stats.written == 2
    row = examples[0]
    assert row["metadata"]["format"] == "compact"
    assert "distance_matrix" not in row["input"]
    assert {"depot", "vehicles", "customers", "base_routes", "event"} <= set(row["input"])
    assert row["output"]["routes"]
