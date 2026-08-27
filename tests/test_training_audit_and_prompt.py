from adaptiveroute.training.audit import validate_sft_row
from adaptiveroute.training.dataset_builder import build_sft_examples
from adaptiveroute.training.prompt_format import to_messages_row, to_prompt_completion_row


def test_compact_sft_row_validates_against_deterministic_validator() -> None:
    examples, _ = build_sft_examples(n=1, seed_start=900, num_customers=6, output_format="compact")

    assert validate_sft_row(examples[0])


def test_prompt_format_messages_row() -> None:
    examples, _ = build_sft_examples(n=1, seed_start=901, num_customers=6, output_format="compact")
    row = to_messages_row(examples[0])

    assert row["messages"][0]["role"] == "system"
    assert row["messages"][1]["role"] == "user"
    assert row["messages"][2]["role"] == "assistant"
    assert '"routes"' in row["messages"][2]["content"]


def test_prompt_completion_row() -> None:
    examples, _ = build_sft_examples(n=1, seed_start=902, num_customers=6, output_format="compact")
    row = to_prompt_completion_row(examples[0])

    assert "prompt" in row
    assert "completion" in row
    assert "Input JSON" in row["prompt"]
