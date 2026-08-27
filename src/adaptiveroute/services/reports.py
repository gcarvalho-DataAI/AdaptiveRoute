from __future__ import annotations

from adaptiveroute.domain.serialization import event_to_dict, plan_to_dict, scenario_to_dict, validation_to_dict
from adaptiveroute.services.comparison import comparison_to_dict
from adaptiveroute.services.replanning import ReplanningResult


def replanning_result_to_dict(result: ReplanningResult) -> dict:
    return {
        "succeeded": result.succeeded,
        "trace_id": result.trace_id,
        "event": event_to_dict(result.event),
        "base_scenario": scenario_to_dict(result.base_scenario),
        "replanning_scenario": scenario_to_dict(result.replanning_scenario) if result.replanning_scenario else None,
        "mutation": {
            "event": event_to_dict(result.mutation.event),
            "diff": result.mutation.diff,
        }
        if result.mutation
        else None,
        "base_solver": {
            "status": result.base_result.status.value,
            "message": result.base_result.message,
            "solve_time_ms": result.base_result.solve_time_ms,
        },
        "replanned_solver": {
            "status": result.replanned_result.status.value,
            "message": result.replanned_result.message,
            "solve_time_ms": result.replanned_result.solve_time_ms,
        }
        if result.replanned_result
        else None,
        "base_plan": plan_to_dict(result.base_result.plan) if result.base_result.plan else None,
        "replanned_plan": plan_to_dict(result.replanned_result.plan)
        if result.replanned_result and result.replanned_result.plan
        else None,
        "base_validation": validation_to_dict(result.base_validation) if result.base_validation else None,
        "replanned_validation": validation_to_dict(result.replanned_validation) if result.replanned_validation else None,
        "comparison": comparison_to_dict(result.comparison) if result.comparison else None,
    }


def build_dispatch_report(result: ReplanningResult) -> str:
    if not result.succeeded or result.comparison is None or result.replanned_result is None or result.replanned_result.plan is None:
        return "Replanning did not produce a valid dispatch plan."

    comparison = result.comparison
    lines = [
        "AdaptiveRoute Dispatch Report",
        "",
        f"Event: {result.event.description}",
        f"Distance impact: {comparison.total_distance_before:.2f} -> {comparison.total_distance_after:.2f} ({comparison.distance_delta:+.2f})",
    ]
    if comparison.removed_customers:
        lines.append(f"Removed customers: {', '.join(comparison.removed_customers)}")
    if comparison.blocked_arcs_after:
        blocked = ", ".join(f"{origin}->{destination}" for origin, destination in comparison.blocked_arcs_after)
        lines.append(f"Blocked arcs avoided: {blocked}")
    lines.append("")
    lines.append("Replanned routes:")
    for route in result.replanned_result.plan.routes:
        lines.append(f"- {route.vehicle_id}: {' -> '.join(route.stops)} | load {route.load} | distance {route.distance:.2f}")
    return "\n".join(lines)
