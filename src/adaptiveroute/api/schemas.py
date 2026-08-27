from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CreateConversationRequest(BaseModel):
    title: str | None = None
    scenario_id: str = "demo-cvrp-8"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class AppendMessageRequest(BaseModel):
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentRunResponse(BaseModel):
    id: str
    conversation_id: str
    input_message_id: str
    status: str
    trace: list[dict[str, Any]]
    result: dict[str, Any]
    created_at: datetime


class ContextWindowResponse(BaseModel):
    id: str
    conversation_id: str
    summary: str
    recent_message_ids: list[str]
    facts: list[str]
    open_constraints: list[str]
    last_event: dict[str, Any] | None
    last_plan: dict[str, Any] | None
    updated_at: datetime


class ReplanRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    scenario_id: str = "demo-cvrp-8"


class ReplanResponse(BaseModel):
    conversation_id: str
    input_message_id: str
    assistant_message_id: str
    agent_run_id: str
    assistant_message: str
    agentic_result: dict[str, Any]
    context_window_before: dict[str, Any] | None = None
    context_window: dict[str, Any]
    operational_route: dict[str, Any] | None = None
    trace: list[dict[str, Any]]


class ScenarioResponse(BaseModel):
    id: str
    depot: dict[str, Any]
    customers: list[dict[str, Any]]
    vehicles: list[dict[str, Any]]
    distance_matrix: list[dict[str, Any]]
    blocked_arcs: list[dict[str, Any]]


class SaveScenarioRequest(BaseModel):
    id: str
    depot: dict[str, Any]
    customers: list[dict[str, Any]]
    vehicles: list[dict[str, Any]]
    distance_matrix: list[dict[str, Any]]
    blocked_arcs: list[dict[str, Any]] = Field(default_factory=list)


class OrderLocation(BaseModel):
    address: str
    lat: float
    lng: float


class ScenarioOrder(BaseModel):
    id: str
    pickup: OrderLocation
    delivery: OrderLocation
    weight: float
    weight_unit: str = "kg"
    volume: float | None = None
    volume_unit: str | None = None
    priority: int = 1
    description: str | None = None


class CreateScenarioFromOrdersRequest(BaseModel):
    id: str = "orders-nyc-demo"
    depot: OrderLocation
    orders: list[ScenarioOrder]
    vehicle_count: int = 2
    vehicle_capacity: int = 20
    use_road_distance: bool = True


class CreateOperationalRouteRequest(BaseModel):
    id: str
    driver_id: str
    scenario_id: str = "demo-cvrp-8"
    status: str = "assigned"
    metadata: dict[str, Any] = Field(default_factory=dict)


class OperationalRouteResponse(BaseModel):
    id: str
    driver_id: str
    scenario_id: str
    current_plan: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateDriverRequest(BaseModel):
    id: str
    name: str
    vehicle_id: str
    capacity: int = 20
    status: Literal["available", "on_route", "off_duty", "inactive"] = "available"
    region: str = "NYC"
    shift_start: str | None = None
    shift_end: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateDriverRequest(BaseModel):
    name: str
    vehicle_id: str
    capacity: int = 20
    status: Literal["available", "on_route", "off_duty", "inactive"] = "available"
    region: str = "NYC"
    shift_start: str | None = None
    shift_end: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DriverResponse(BaseModel):
    id: str
    name: str
    vehicle_id: str
    capacity: int
    status: str
    region: str
    shift_start: str | None = None
    shift_end: str | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class DriverLoginRequest(BaseModel):
    username: str
    password: str


class DriverPortalResponse(BaseModel):
    driver: dict[str, Any]
    routes: list[dict[str, Any]]
    access_token: str


class DriverRouteStatusRequest(BaseModel):
    username: str
    password: str
    status: Literal["assigned", "in_progress", "completed", "cancelled"]


class DriverProfileUpdateRequest(BaseModel):
    username: str
    password: str
    new_password: str | None = None
    capacity: int | None = None


class DailyPlanningRequest(BaseModel):
    scenario_id: str = "demo-cvrp-8"
    route_prefix: str = "ROUTE"
    include_demo_drivers: bool = True


class DailyPlanningResponse(BaseModel):
    scenario_id: str
    solver_status: str
    solve_time_ms: float | None = None
    available_driver_count: int
    created_route_count: int
    routes: list[dict[str, Any]]
    plan: dict[str, Any]


class PlanningJobResponse(BaseModel):
    id: str
    scenario_id: str
    route_prefix: str
    include_demo_drivers: bool
    status: str
    stage: str
    progress: int
    message: str
    pid: int | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class RagIngestRequest(BaseModel):
    paths: list[str] = Field(default_factory=lambda: ["README.md", "docs"])


class RagIngestResponse(BaseModel):
    document_count: int
    chunk_count: int
    documents: list[dict[str, Any]]


class RagQueryRequest(BaseModel):
    query: str
    limit: int = 5


class RagQueryResponse(BaseModel):
    query: str
    results: list[dict[str, Any]]


class RouteGeometryRequest(BaseModel):
    plan: dict[str, Any]
    locations: dict[str, dict[str, Any]]
    overview: Literal["full", "simplified"] = "full"


class RouteGeometryResponse(BaseModel):
    source: str
    routes: list[dict[str, Any]]
    warnings: list[str] = Field(default_factory=list)
