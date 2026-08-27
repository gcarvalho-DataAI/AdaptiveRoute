from __future__ import annotations

import os
import signal
import subprocess
import sys
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from typing import Any, Literal, Protocol
from uuid import uuid4


PlanningJobStatus = Literal["queued", "running", "completed", "failed", "cancelled"]


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class PlanningJobRecord:
    id: str
    scenario_id: str
    route_prefix: str
    include_demo_drivers: bool
    status: PlanningJobStatus = "queued"
    stage: str = "queued"
    progress: int = 0
    message: str = "Queued for optimization."
    pid: int | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class PlanningJobRepository(Protocol):
    def save_job(self, job: PlanningJobRecord) -> PlanningJobRecord: ...
    def get_job(self, job_id: str) -> PlanningJobRecord | None: ...
    def list_jobs(self) -> list[PlanningJobRecord]: ...
    def delete_job(self, job_id: str) -> bool: ...


class InMemoryPlanningJobRepository:
    def __init__(self):
        self._jobs: dict[str, PlanningJobRecord] = {}

    def save_job(self, job: PlanningJobRecord) -> PlanningJobRecord:
        self._jobs[job.id] = job
        return job

    def get_job(self, job_id: str) -> PlanningJobRecord | None:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[PlanningJobRecord]:
        return sorted(self._jobs.values(), key=lambda item: item.updated_at, reverse=True)

    def delete_job(self, job_id: str) -> bool:
        return self._jobs.pop(job_id, None) is not None


class MongoPlanningJobRepository:
    def __init__(self, *, uri: str, database: str):
        from pymongo import DESCENDING, MongoClient

        self._client = MongoClient(uri)
        self._collection = self._client[database]["planning_jobs"]
        self._collection.create_index([("scenario_id", DESCENDING), ("updated_at", DESCENDING)])
        self._collection.create_index([("status", DESCENDING), ("updated_at", DESCENDING)])

    def save_job(self, job: PlanningJobRecord) -> PlanningJobRecord:
        self._collection.replace_one({"_id": job.id}, _to_document(job), upsert=True)
        return job

    def get_job(self, job_id: str) -> PlanningJobRecord | None:
        document = self._collection.find_one({"_id": job_id})
        return _job_from_document(document) if document else None

    def list_jobs(self) -> list[PlanningJobRecord]:
        return [_job_from_document(document) for document in self._collection.find().sort("updated_at", -1)]

    def delete_job(self, job_id: str) -> bool:
        result = self._collection.delete_one({"_id": job_id})
        return result.deleted_count > 0


class PlanningJobService:
    def __init__(self, repository: PlanningJobRepository):
        self._repository = repository

    def create_job(self, *, scenario_id: str, route_prefix: str, include_demo_drivers: bool = True) -> PlanningJobRecord:
        job = PlanningJobRecord(
            id=f"plan-{uuid4().hex[:12]}",
            scenario_id=scenario_id,
            route_prefix=route_prefix,
            include_demo_drivers=include_demo_drivers,
        )
        self._repository.save_job(job)
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "adaptiveroute.planning.worker",
                "--job-id",
                job.id,
                "--scenario-id",
                scenario_id,
                "--route-prefix",
                route_prefix,
                "--include-demo-drivers",
                "true" if include_demo_drivers else "false",
            ],
            env=os.environ.copy(),
            start_new_session=True,
        )
        return self._repository.save_job(
            replace(job, pid=process.pid, status="running", stage="starting", progress=2, message="Starting solver process.", updated_at=utc_now())
        )

    def get_job(self, job_id: str) -> PlanningJobRecord | None:
        return self._repository.get_job(job_id)

    def list_jobs(self) -> list[PlanningJobRecord]:
        return self._repository.list_jobs()

    def cancel_job(self, job_id: str) -> PlanningJobRecord | None:
        job = self._repository.get_job(job_id)
        if job is None:
            return None
        if job.status in {"completed", "failed", "cancelled"}:
            return job
        if job.pid:
            try:
                os.killpg(job.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            except PermissionError:
                os.kill(job.pid, signal.SIGTERM)
        return self._repository.save_job(
            replace(
                job,
                status="cancelled",
                stage="cancelled",
                message="Optimization cancelled by operator.",
                progress=max(job.progress, 1),
                updated_at=utc_now(),
                completed_at=utc_now(),
            )
        )

    def delete_job(self, job_id: str) -> bool:
        job = self._repository.get_job(job_id)
        if job and job.status in {"queued", "running"}:
            self.cancel_job(job_id)
        return self._repository.delete_job(job_id)


def planning_job_to_dict(job: PlanningJobRecord) -> dict[str, Any]:
    return asdict(job)


def _to_document(job: PlanningJobRecord) -> dict[str, Any]:
    document = asdict(job)
    document["_id"] = document.pop("id")
    return document


def _job_from_document(document: dict[str, Any]) -> PlanningJobRecord:
    return PlanningJobRecord(
        id=document["_id"],
        scenario_id=document["scenario_id"],
        route_prefix=document.get("route_prefix", "ROUTE"),
        include_demo_drivers=bool(document.get("include_demo_drivers", True)),
        status=document.get("status", "queued"),
        stage=document.get("stage", "queued"),
        progress=int(document.get("progress", 0)),
        message=document.get("message", ""),
        pid=document.get("pid"),
        result=document.get("result"),
        error=document.get("error"),
        created_at=_dt(document["created_at"]),
        updated_at=_dt(document["updated_at"]),
        started_at=_optional_dt(document.get("started_at")),
        completed_at=_optional_dt(document.get("completed_at")),
    )


def _optional_dt(value: datetime | str | None) -> datetime | None:
    return _dt(value) if value else None


def _dt(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
