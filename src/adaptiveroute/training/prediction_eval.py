from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from adaptiveroute.training.audit import event_from_compact_input, scenario_from_compact_input
from adaptiveroute.services.counterfactual import build_plan_from_route_sequences
from adaptiveroute.services.mutations import apply_event
from adaptiveroute.services.validation import validate_plan


@dataclass(frozen=True)
class PredictionEvalSummary:
    total: int
    valid_json: int
    feasible: int
    exact_match: int
    violation_counts: dict[str, int]

    @property
    def valid_json_rate(self) -> float:
        return self.valid_json / self.total if self.total else 0.0

    @property
    def feasible_rate(self) -> float:
        return self.feasible / self.total if self.total else 0.0

    @property
    def exact_match_rate(self) -> float:
        return self.exact_match / self.total if self.total else 0.0


def evaluate_predictions(dataset_path: Path, predictions_path: Path) -> tuple[PredictionEvalSummary, list[dict[str, Any]]]:
    dataset_rows = list(iter_jsonl(dataset_path))
    prediction_rows = list(iter_jsonl(predictions_path))
    violation_counts: Counter[str] = Counter()
    details: list[dict[str, Any]] = []
    valid_json = 0
    feasible = 0
    exact_match = 0

    for prediction in prediction_rows:
        row_index = int(prediction["row_index"])
        dataset_row = dataset_rows[row_index]
        parsed = parse_prediction_json(prediction["prediction_text"])
        if parsed is None:
            violation_counts["invalid_json"] += 1
            details.append({"row_index": row_index, "valid_json": False, "feasible": False, "violations": ["invalid_json"]})
            continue

        valid_json += 1
        scenario = scenario_from_compact_input(dataset_row["input"])
        event = event_from_compact_input(dataset_row["input"]["event"])
        mutated_scenario, _ = apply_event(scenario, event)

        try:
            candidate_plan = build_plan_from_route_sequences(mutated_scenario, parsed["routes"])
            validation = validate_plan(mutated_scenario, candidate_plan)
        except Exception as exc:
            violation_counts["plan_build_error"] += 1
            details.append(
                {
                    "row_index": row_index,
                    "valid_json": True,
                    "feasible": False,
                    "violations": ["plan_build_error"],
                    "error": str(exc),
                }
            )
            continue

        violation_codes = [violation.code for violation in validation.violations]
        for code in violation_codes:
            violation_counts[code] += 1
        if validation.passed:
            feasible += 1
        if normalize_routes(parsed.get("routes", {})) == normalize_routes(dataset_row["output"].get("routes", {})):
            exact_match += 1

        details.append(
            {
                "row_index": row_index,
                "valid_json": True,
                "feasible": validation.passed,
                "exact_match": normalize_routes(parsed.get("routes", {}))
                == normalize_routes(dataset_row["output"].get("routes", {})),
                "violations": violation_codes,
            }
        )

    summary = PredictionEvalSummary(
        total=len(prediction_rows),
        valid_json=valid_json,
        feasible=feasible,
        exact_match=exact_match,
        violation_counts=dict(sorted(violation_counts.items())),
    )
    return summary, details


def parse_prediction_json(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    candidates = [stripped]
    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if match:
        candidates.append(match.group(0))
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and isinstance(parsed.get("routes"), dict):
            return parsed
    return None


def normalize_routes(routes: dict[str, list[str]]) -> dict[str, list[str]]:
    return {vehicle_id: list(stops) for vehicle_id, stops in sorted(routes.items())}


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                yield json.loads(line)


def summary_to_dict(summary: PredictionEvalSummary) -> dict[str, Any]:
    return {
        "total": summary.total,
        "valid_json": summary.valid_json,
        "valid_json_rate": round(summary.valid_json_rate, 4),
        "feasible": summary.feasible,
        "feasible_rate": round(summary.feasible_rate, 4),
        "exact_match": summary.exact_match,
        "exact_match_rate": round(summary.exact_match_rate, 4),
        "violation_counts": summary.violation_counts,
    }

