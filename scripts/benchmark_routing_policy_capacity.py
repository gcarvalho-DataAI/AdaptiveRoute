#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Iterable

from adaptiveroute.agentic.candidates import build_routing_candidate_generator_from_env
from adaptiveroute.agentic.repair import repair_candidate_plan
from adaptiveroute.config import load_project_env
from adaptiveroute.data.generator import generate_scenario
from adaptiveroute.domain.events import EventType, OperationalEvent
from adaptiveroute.domain.models import RoutingPlan, RoutingScenario, SolveStatus
from adaptiveroute.domain.serialization import validation_to_dict
from adaptiveroute.services.comparison import compare_plans
from adaptiveroute.services.mutations import apply_event, generate_training_event
from adaptiveroute.services.validation import validate_plan
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine
from adaptiveroute.training.dataset_builder import (
    DatasetProfile,
    capacity_slack_for_profile,
    demand_range_for_profile,
)


@dataclass(frozen=True)
class BenchmarkCaseResult:
    seed: int
    profile: str
    num_customers: int
    num_vehicles: int
    event_type: str
    scenario_id: str
    candidate_source: str
    base_status: str
    base_solve_time_ms: float | None
    oracle_status: str | None
    oracle_solve_time_ms: float | None
    candidate_latency_ms: float | None
    candidate_returned_plan: bool
    candidate_valid: bool
    candidate_repaired_valid: bool
    validation_violations: list[dict]
    repaired_validation_violations: list[dict]
    total_distance_before: float | None
    total_distance_candidate: float | None
    total_distance_oracle: float | None
    candidate_distance_delta_vs_base: float | None
    candidate_distance_delta_vs_oracle: float | None
    removed_customers: list[str]
    message: str


def main() -> int:
    args = parse_args()
    if args.env_file:
        load_project_env(args.env_file)
    else:
        load_project_env()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path = Path(args.markdown_out) if args.markdown_out else out_path.with_suffix(".md")

    engine = PyomoHighsEngine(time_limit_seconds=args.solver_time_limit, mip_gap=args.solver_mip_gap)
    candidate_generator = build_routing_candidate_generator_from_env(engine)

    results: list[BenchmarkCaseResult] = []
    for num_customers in parse_int_list(args.customer_grid):
        num_vehicles = args.vehicles or default_vehicle_count(num_customers)
        for sample_idx in range(args.samples_per_size):
            seed = args.seed_start + num_customers * 10_000 + sample_idx
            result = run_case(
                engine=engine,
                candidate_generator=candidate_generator,
                seed=seed,
                num_customers=num_customers,
                num_vehicles=num_vehicles,
                profile=args.profile,
                event_types=parse_event_types(args.event_types),
                with_oracle=args.with_oracle,
            )
            results.append(result)
            print(
                f"{num_customers:>3}c seed={seed} event={result.event_type:<22} "
                f"valid={str(result.candidate_valid):<5} repaired={str(result.candidate_repaired_valid):<5} "
                f"latency_ms={result.candidate_latency_ms} source={result.candidate_source}"
            )

    summary = summarize(results, viability_threshold=args.viability_threshold)
    payload = {
        "config": {
            "customer_grid": parse_int_list(args.customer_grid),
            "samples_per_size": args.samples_per_size,
            "vehicles": args.vehicles,
            "profile": args.profile,
            "event_types": [event.value for event in parse_event_types(args.event_types)],
            "viability_threshold": args.viability_threshold,
            "with_oracle": args.with_oracle,
            "solver_time_limit": args.solver_time_limit,
            "solver_mip_gap": args.solver_mip_gap,
            "routing_policy_backend": os.getenv("ADAPTIVEROUTE_ROUTING_POLICY_BACKEND", "solver"),
            "routing_policy_model": os.getenv("ADAPTIVEROUTE_ROUTING_POLICY_MODEL"),
            "routing_policy_base_url": os.getenv("ADAPTIVEROUTE_ROUTING_POLICY_BASE_URL"),
        },
        "summary": summary,
        "cases": [asdict(result) for result in results],
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    print(f"\nWrote benchmark JSON to {out_path}")
    print(f"Wrote benchmark report to {markdown_path}")
    print(f"Max viable customers: {summary['max_viable_customers']}")
    return 0


def run_case(
    *,
    engine: PyomoHighsEngine,
    candidate_generator,
    seed: int,
    num_customers: int,
    num_vehicles: int,
    profile: DatasetProfile,
    event_types: tuple[EventType, ...],
    with_oracle: bool,
) -> BenchmarkCaseResult:
    rng = random.Random(seed + 20_000)
    scenario = generate_scenario(
        seed=seed,
        num_customers=num_customers,
        num_vehicles=num_vehicles,
        clustered=seed % 2 == 0,
        capacity_slack=capacity_slack_for_profile(profile, rng),
        demand_range=demand_range_for_profile(profile),
    )
    base_result = engine.solve(scenario)
    if base_result.plan is None:
        return BenchmarkCaseResult(
            seed=seed,
            profile=profile,
            num_customers=num_customers,
            num_vehicles=num_vehicles,
            event_type="none",
            scenario_id=scenario.id,
            candidate_source="not_run",
            base_status=base_result.status.value,
            base_solve_time_ms=round_or_none(base_result.solve_time_ms),
            oracle_status=None,
            oracle_solve_time_ms=None,
            candidate_latency_ms=None,
            candidate_returned_plan=False,
            candidate_valid=False,
            candidate_repaired_valid=False,
            validation_violations=[{"code": "base_solve_failed", "message": base_result.message}],
            repaired_validation_violations=[],
            total_distance_before=None,
            total_distance_candidate=None,
            total_distance_oracle=None,
            candidate_distance_delta_vs_base=None,
            candidate_distance_delta_vs_oracle=None,
            removed_customers=[],
            message=base_result.message,
        )

    event = generate_training_event(scenario, base_result.plan, seed=seed + 10_000, event_types=event_types)
    replanning_scenario, _ = apply_event(scenario, event)

    oracle_plan: RoutingPlan | None = None
    oracle_status: str | None = None
    oracle_solve_time_ms: float | None = None
    if with_oracle:
        oracle_result = engine.solve(replanning_scenario)
        oracle_status = oracle_result.status.value
        oracle_solve_time_ms = round_or_none(oracle_result.solve_time_ms)
        if oracle_result.status in {SolveStatus.OPTIMAL, SolveStatus.FEASIBLE}:
            oracle_plan = oracle_result.plan

    started = perf_counter()
    candidate_result = candidate_generator.generate(replanning_scenario, event, base_result.plan)
    candidate_latency_ms = round((perf_counter() - started) * 1000, 2)

    candidate_plan = candidate_result.plan
    if candidate_plan is None:
        return BenchmarkCaseResult(
            seed=seed,
            profile=profile,
            num_customers=num_customers,
            num_vehicles=num_vehicles,
            event_type=event.type.value,
            scenario_id=replanning_scenario.id,
            candidate_source=candidate_result.source,
            base_status=base_result.status.value,
            base_solve_time_ms=round_or_none(base_result.solve_time_ms),
            oracle_status=oracle_status,
            oracle_solve_time_ms=oracle_solve_time_ms,
            candidate_latency_ms=candidate_latency_ms,
            candidate_returned_plan=False,
            candidate_valid=False,
            candidate_repaired_valid=False,
            validation_violations=[{"code": "no_candidate_plan", "message": candidate_result.message}],
            repaired_validation_violations=[],
            total_distance_before=base_result.plan.total_distance,
            total_distance_candidate=None,
            total_distance_oracle=oracle_plan.total_distance if oracle_plan else None,
            candidate_distance_delta_vs_base=None,
            candidate_distance_delta_vs_oracle=None,
            removed_customers=[],
            message=candidate_result.message,
        )

    validation = validate_plan(replanning_scenario, candidate_plan)
    repaired = repair_candidate_plan(replanning_scenario, candidate_plan)
    repaired_validation = validate_plan(replanning_scenario, repaired)
    comparison = compare_plans(scenario, base_result.plan, replanning_scenario, candidate_plan)
    oracle_delta = (
        round(candidate_plan.total_distance - oracle_plan.total_distance, 2)
        if oracle_plan is not None
        else None
    )

    return BenchmarkCaseResult(
        seed=seed,
        profile=profile,
        num_customers=num_customers,
        num_vehicles=num_vehicles,
        event_type=event.type.value,
        scenario_id=replanning_scenario.id,
        candidate_source=candidate_result.source,
        base_status=base_result.status.value,
        base_solve_time_ms=round_or_none(base_result.solve_time_ms),
        oracle_status=oracle_status,
        oracle_solve_time_ms=oracle_solve_time_ms,
        candidate_latency_ms=candidate_latency_ms,
        candidate_returned_plan=True,
        candidate_valid=validation.passed,
        candidate_repaired_valid=repaired_validation.passed,
        validation_violations=validation_to_dict(validation)["violations"],
        repaired_validation_violations=validation_to_dict(repaired_validation)["violations"],
        total_distance_before=base_result.plan.total_distance,
        total_distance_candidate=candidate_plan.total_distance,
        total_distance_oracle=oracle_plan.total_distance if oracle_plan else None,
        candidate_distance_delta_vs_base=comparison.distance_delta,
        candidate_distance_delta_vs_oracle=oracle_delta,
        removed_customers=list(comparison.removed_customers),
        message=candidate_result.message,
    )


def summarize(results: list[BenchmarkCaseResult], *, viability_threshold: float) -> dict:
    by_size: dict[int, list[BenchmarkCaseResult]] = {}
    for result in results:
        by_size.setdefault(result.num_customers, []).append(result)

    rows: list[dict] = []
    max_viable: int | None = None
    for size in sorted(by_size):
        cases = by_size[size]
        attempted = len(cases)
        returned = sum(1 for case in cases if case.candidate_returned_plan)
        valid = sum(1 for case in cases if case.candidate_valid)
        repaired_valid = sum(1 for case in cases if case.candidate_repaired_valid)
        latencies = [case.candidate_latency_ms for case in cases if case.candidate_latency_ms is not None]
        base_times = [case.base_solve_time_ms for case in cases if case.base_solve_time_ms is not None]
        rate = valid / attempted if attempted else 0.0
        repaired_rate = repaired_valid / attempted if attempted else 0.0
        viable = rate >= viability_threshold
        if viable:
            max_viable = size
        rows.append(
            {
                "num_customers": size,
                "cases": attempted,
                "returned_plan_rate": round(returned / attempted, 4) if attempted else 0.0,
                "valid_rate": round(rate, 4),
                "repaired_valid_rate": round(repaired_rate, 4),
                "latency_ms_avg": round(statistics.fmean(latencies), 2) if latencies else None,
                "latency_ms_p95": percentile(latencies, 95),
                "base_solve_ms_avg": round(statistics.fmean(base_times), 2) if base_times else None,
                "viable": viable,
                "top_violation_codes": top_violation_codes(cases),
            }
        )
    return {
        "viability_threshold": viability_threshold,
        "max_viable_customers": max_viable,
        "by_num_customers": rows,
    }


def render_markdown(payload: dict) -> str:
    config = payload["config"]
    summary = payload["summary"]
    lines = [
        "# AdaptiveRoute Routing Policy Capacity Benchmark",
        "",
        "## Configuration",
        "",
        f"- Routing policy backend: `{config.get('routing_policy_backend')}`",
        f"- Routing policy model: `{config.get('routing_policy_model') or 'not set'}`",
        f"- Scenario profile: `{config['profile']}`",
        f"- Event types: `{', '.join(config['event_types'])}`",
        f"- Samples per size: `{config['samples_per_size']}`",
        f"- Viability threshold: `{summary['viability_threshold']:.2%}` valid candidate plans",
        f"- Oracle solver comparison enabled: `{config['with_oracle']}`",
        "",
        "## Result",
        "",
        f"- Maximum viable customer count: `{summary['max_viable_customers']}`",
        "",
        "| Customers | Cases | Returned | Valid | Repaired valid | Avg latency ms | P95 latency ms | Avg base solve ms | Viable | Top violations |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|:---:|---|",
    ]
    for row in summary["by_num_customers"]:
        lines.append(
            "| "
            f"{row['num_customers']} | "
            f"{row['cases']} | "
            f"{row['returned_plan_rate']:.1%} | "
            f"{row['valid_rate']:.1%} | "
            f"{row['repaired_valid_rate']:.1%} | "
            f"{format_optional(row['latency_ms_avg'])} | "
            f"{format_optional(row['latency_ms_p95'])} | "
            f"{format_optional(row['base_solve_ms_avg'])} | "
            f"{'yes' if row['viable'] else 'no'} | "
            f"{format_violations(row['top_violation_codes'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Use `valid_rate` as the strict maximum scenario-size metric for the trained model.",
            "- Use `repaired_valid_rate` only as an engineering safety metric; it includes local structural repair and is not pure model capability.",
            "- If the backend is `solver`, this run validates the harness, not the LoRA model. Start the policy API and rerun with `ADAPTIVEROUTE_ROUTING_POLICY_BACKEND=api` for model capacity.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark maximum viable scenario size for the routing policy model.")
    parser.add_argument("--customer-grid", default="8,12,16,20", help="Comma-separated customer counts.")
    parser.add_argument("--samples-per-size", type=int, default=5)
    parser.add_argument("--vehicles", type=int, default=None, help="Fixed vehicle count. Defaults to ceil(customers / 8).")
    parser.add_argument("--profile", default="balanced", choices=["balanced", "capacity_tight", "blocked_arc", "mixed_hard", "capacity_extreme", "blocked_capacity"])
    parser.add_argument("--event-types", default="block_arc,customer_unavailable")
    parser.add_argument("--seed-start", type=int, default=10_000)
    parser.add_argument("--viability-threshold", type=float, default=0.9)
    parser.add_argument("--solver-time-limit", type=float, default=None)
    parser.add_argument("--solver-mip-gap", type=float, default=None)
    parser.add_argument("--with-oracle", action="store_true", help="Also solve the mutated scenario to compare distance against solver.")
    parser.add_argument("--env-file", default=None, help="Optional env file. Existing environment variables still take precedence.")
    parser.add_argument("--out", default="outputs/evaluations/routing_policy_capacity.json")
    parser.add_argument("--markdown-out", default=None)
    return parser.parse_args()


def parse_int_list(raw: str) -> list[int]:
    values = [int(part.strip()) for part in raw.split(",") if part.strip()]
    if not values:
        raise ValueError("At least one integer is required.")
    return values


def parse_event_types(raw: str) -> tuple[EventType, ...]:
    mapping = {
        "block_arc": EventType.BLOCK_ARC,
        "blocked_arc": EventType.BLOCK_ARC,
        "customer_unavailable": EventType.CUSTOMER_UNAVAILABLE,
        "unavailable": EventType.CUSTOMER_UNAVAILABLE,
        "priority": EventType.CUSTOMER_PRIORITY_CHANGE,
        "customer_priority_change": EventType.CUSTOMER_PRIORITY_CHANGE,
    }
    parsed = tuple(mapping[part.strip().lower()] for part in raw.split(",") if part.strip())
    if not parsed:
        raise ValueError("At least one event type is required.")
    return parsed


def default_vehicle_count(num_customers: int) -> int:
    return max(2, (num_customers + 7) // 8)


def round_or_none(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


def percentile(values: Iterable[float], pct: int) -> float | None:
    sorted_values = sorted(values)
    if not sorted_values:
        return None
    index = min(len(sorted_values) - 1, round((pct / 100) * (len(sorted_values) - 1)))
    return round(sorted_values[index], 2)


def top_violation_codes(cases: list[BenchmarkCaseResult]) -> list[dict]:
    counts: dict[str, int] = {}
    for case in cases:
        for violation in case.validation_violations:
            code = str(violation.get("code", "unknown"))
            counts[code] = counts.get(code, 0) + 1
    return [{"code": code, "count": count} for code, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:5]]


def format_optional(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"


def format_violations(violations: list[dict]) -> str:
    if not violations:
        return "—"
    return ", ".join(f"{item['code']}×{item['count']}" for item in violations)


if __name__ == "__main__":
    raise SystemExit(main())
