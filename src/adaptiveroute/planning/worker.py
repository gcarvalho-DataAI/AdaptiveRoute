from __future__ import annotations

import argparse
import sys
from dataclasses import replace

from adaptiveroute.api.dependencies import get_daily_planning_service, get_planning_job_repository
from adaptiveroute.planning.jobs import utc_now


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an AdaptiveRoute planning job.")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--scenario-id", required=True)
    parser.add_argument("--route-prefix", default="ROUTE")
    parser.add_argument("--include-demo-drivers", choices=["true", "false"], default="true")
    args = parser.parse_args(argv)

    repository = get_planning_job_repository()
    job = repository.get_job(args.job_id)
    if job is None:
        return 2

    def update(*, stage: str, progress: int, message: str):
        nonlocal job
        latest = repository.get_job(args.job_id) or job
        job = repository.save_job(
            replace(
                latest,
                status="running",
                stage=stage,
                progress=progress,
                message=message,
                updated_at=utc_now(),
                started_at=latest.started_at or utc_now(),
            )
        )

    try:
        update(stage="loading_scenario", progress=8, message="Loading scenario, fleet and route constraints.")
        service = get_daily_planning_service()
        update(stage="optimizing", progress=18, message="Pyomo + HiGHS is optimizing the route assignment.")
        result = service.run_daily_planning(
            scenario_id=args.scenario_id,
            route_prefix=args.route_prefix,
            include_demo_drivers=args.include_demo_drivers == "true",
        )
        latest = repository.get_job(args.job_id) or job
        repository.save_job(
            replace(
                latest,
                status="completed",
                stage="completed",
                progress=100,
                message=f"Optimization completed. Published {result['created_route_count']} route(s).",
                result=result,
                updated_at=utc_now(),
                completed_at=utc_now(),
            )
        )
        return 0
    except BaseException as exc:
        latest = repository.get_job(args.job_id) or job
        if latest.status == "cancelled":
            return 130
        repository.save_job(
            replace(
                latest,
                status="failed",
                stage="failed",
                progress=max(latest.progress, 1),
                message="Optimization failed.",
                error=str(exc),
                updated_at=utc_now(),
                completed_at=utc_now(),
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
