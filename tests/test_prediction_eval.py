from adaptiveroute.training.prediction_eval import parse_prediction_json


def test_parse_prediction_json_accepts_clean_json() -> None:
    parsed = parse_prediction_json('{"routes": {"V1": ["D0", "C1", "D0"]}}')

    assert parsed == {"routes": {"V1": ["D0", "C1", "D0"]}}


def test_parse_prediction_json_extracts_json_from_text() -> None:
    parsed = parse_prediction_json('Here is the answer:\n{"routes": {"V1": ["D0", "C1", "D0"]}}')

    assert parsed == {"routes": {"V1": ["D0", "C1", "D0"]}}


def test_parse_prediction_json_rejects_non_route_json() -> None:
    assert parse_prediction_json('{"foo": 1}') is None
