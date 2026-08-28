from __future__ import annotations

from dataclasses import asdict

import jwt
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from adaptiveroute.api.schemas import (
    AgentRunResponse,
    AppendMessageRequest,
    ContextWindowResponse,
    ConversationResponse,
    CreateDriverRequest,
    CreateOperationalRouteRequest,
    CreateConversationRequest,
    CreateScenarioFromOrdersRequest,
    DailyPlanningRequest,
    DailyPlanningResponse,
    DriverLoginRequest,
    DriverPortalResponse,
    DriverProfileUpdateRequest,
    DriverRouteStatusRequest,
    DriverResponse,
    MessageResponse,
    OperationalRouteResponse,
    PlanningJobResponse,
    RagIngestRequest,
    RagIngestResponse,
    RagQueryRequest,
    RagQueryResponse,
    RouteGeometryRequest,
    RouteGeometryResponse,
    ReplanRequest,
    ReplanResponse,
    SaveScenarioRequest,
    ScenarioResponse,
    UpdateDriverRequest,
)
from adaptiveroute.domain.models import Customer, Depot, RoutingScenario, Vehicle
from adaptiveroute.api.dependencies import (
    get_conversation_service,
    get_daily_planning_service,
    get_driver_service,
    get_operational_route_service,
    get_map_routing_service,
    get_planning_job_service,
    get_rag_service,
    get_scenario_service,
)
from adaptiveroute.api.security import create_access_token, decode_access_token
from adaptiveroute.api.settings import get_api_settings
from adaptiveroute.domain.serialization import scenario_from_dict, scenario_to_dict
from adaptiveroute.drivers import DriverService, driver_to_dict
from adaptiveroute.memory.service import ConversationService
from adaptiveroute.maps import MapRoutingService
from adaptiveroute.operations.service import OperationalRouteService, route_to_dict
from adaptiveroute.orders import parse_orders_spreadsheet
from adaptiveroute.planning import DailyPlanningService, PlanningJobService, planning_job_to_dict
from adaptiveroute.rag.service import RagService
from adaptiveroute.scenarios.service import ScenarioService

router = APIRouter()
driver_bearer = HTTPBearer(auto_error=False)


def _paginate(items: list, *, skip: int, limit: int) -> list:
    return items[skip : skip + limit]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/v1/conversations", response_model=ConversationResponse)
def create_conversation(
    payload: CreateConversationRequest,
    service: ConversationService = Depends(get_conversation_service),
) -> dict:
    return asdict(
        service.create_conversation(
            title=payload.title,
            scenario_id=payload.scenario_id,
            metadata=payload.metadata,
        )
    )


@router.get("/v1/conversations", response_model=list[ConversationResponse])
def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    service: ConversationService = Depends(get_conversation_service),
) -> list[dict]:
    return _paginate([asdict(conversation) for conversation in service.list_conversations()], skip=skip, limit=limit)


@router.get("/v1/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: str,
    service: ConversationService = Depends(get_conversation_service),
) -> dict:
    conversation = service.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return asdict(conversation)


@router.delete("/v1/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    service: ConversationService = Depends(get_conversation_service),
) -> dict:
    deleted = service.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"deleted": True, "conversation_id": conversation_id}


@router.get("/v1/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
def list_messages(
    conversation_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    service: ConversationService = Depends(get_conversation_service),
) -> list[dict]:
    try:
        return _paginate([asdict(message) for message in service.list_messages(conversation_id)], skip=skip, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/v1/conversations/{conversation_id}/agent-runs", response_model=list[AgentRunResponse])
def list_agent_runs(
    conversation_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    service: ConversationService = Depends(get_conversation_service),
) -> list[dict]:
    try:
        if service.get_conversation(conversation_id) is None:
            raise ValueError(f"Conversation not found: {conversation_id}")
        return _paginate([asdict(run) for run in service.list_agent_runs(conversation_id)], skip=skip, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/v1/conversations/{conversation_id}/messages", response_model=MessageResponse)
def append_message(
    conversation_id: str,
    payload: AppendMessageRequest,
    service: ConversationService = Depends(get_conversation_service),
) -> dict:
    try:
        return asdict(
            service.append_message(
                conversation_id=conversation_id,
                role=payload.role,
                content=payload.content,
                metadata=payload.metadata,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc)) from exc


@router.get("/v1/conversations/{conversation_id}/context", response_model=ContextWindowResponse | None)
def get_context_window(
    conversation_id: str,
    service: ConversationService = Depends(get_conversation_service),
) -> dict | None:
    try:
        context = service.get_context_window(conversation_id)
        return asdict(context) if context else None
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/v1/agentic/replan", response_model=ReplanResponse)
def replan(
    payload: ReplanRequest,
    service: ConversationService = Depends(get_conversation_service),
) -> dict:
    try:
        return service.replan(
            message=payload.message,
            conversation_id=payload.conversation_id,
            scenario_id=payload.scenario_id,
        )
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.post("/v1/scenarios/demo", response_model=ScenarioResponse)
def seed_demo_scenario(service: ScenarioService = Depends(get_scenario_service)) -> dict:
    return scenario_to_dict(service.seed_demo_scenario())


@router.get("/v1/scenarios", response_model=list[ScenarioResponse])
def list_scenarios(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    service: ScenarioService = Depends(get_scenario_service),
) -> list[dict]:
    return _paginate([scenario_to_dict(scenario) for scenario in service.list_scenarios()], skip=skip, limit=limit)


@router.get("/v1/scenarios/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(
    scenario_id: str,
    service: ScenarioService = Depends(get_scenario_service),
) -> dict:
    scenario = service.get_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Routing scenario not found.")
    return scenario_to_dict(scenario)


@router.delete("/v1/scenarios/{scenario_id}")
def delete_scenario(
    scenario_id: str,
    service: ScenarioService = Depends(get_scenario_service),
) -> dict:
    try:
        deleted = service.delete_scenario(scenario_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Routing scenario not found.")
    return {"deleted": True, "scenario_id": scenario_id}


@router.put("/v1/scenarios/{scenario_id}", response_model=ScenarioResponse)
def save_scenario(
    scenario_id: str,
    payload: SaveScenarioRequest,
    service: ScenarioService = Depends(get_scenario_service),
) -> dict:
    if scenario_id != payload.id:
        raise HTTPException(status_code=400, detail="Path scenario_id must match payload id.")
    try:
        scenario = service.save_scenario(scenario_from_dict(payload.model_dump()))
        return scenario_to_dict(scenario)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/v1/scenarios/from-orders", response_model=ScenarioResponse)
def create_scenario_from_orders(
    payload: CreateScenarioFromOrdersRequest,
    scenario_service: ScenarioService = Depends(get_scenario_service),
    map_service: MapRoutingService = Depends(get_map_routing_service),
) -> dict:
    try:
        return _save_order_scenario(payload, scenario_service=scenario_service, map_service=map_service)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/v1/scenarios/from-orders-file", response_model=ScenarioResponse)
async def create_scenario_from_orders_file(
    file: UploadFile = File(...),
    scenario_id: str = Form("orders-upload"),
    depot_address: str = Form(...),
    depot_lat: float = Form(...),
    depot_lng: float = Form(...),
    vehicle_count: int = Form(2),
    vehicle_capacity: int = Form(20),
    use_road_distance: bool = Form(True),
    scenario_service: ScenarioService = Depends(get_scenario_service),
    map_service: MapRoutingService = Depends(get_map_routing_service),
) -> dict:
    try:
        content = await file.read()
        orders = parse_orders_spreadsheet(content, file.filename or "orders.csv")
        payload = CreateScenarioFromOrdersRequest(
            id=scenario_id,
            depot={"address": depot_address, "lat": depot_lat, "lng": depot_lng},
            orders=orders,
            vehicle_count=vehicle_count,
            vehicle_capacity=vehicle_capacity,
            use_road_distance=use_road_distance,
        )
        return _save_order_scenario(payload, scenario_service=scenario_service, map_service=map_service)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _save_order_scenario(
    payload: CreateScenarioFromOrdersRequest,
    *,
    scenario_service: ScenarioService,
    map_service: MapRoutingService,
) -> dict:
    locations: dict[str, dict[str, float]] = {
        "D0": {"lat": payload.depot.lat, "lng": payload.depot.lng},
    }
    customers: list[Customer] = []
    for index, order in enumerate(payload.orders, start=1):
        customer_id = f"C{index}"
        locations[customer_id] = {"lat": order.delivery.lat, "lng": order.delivery.lng}
        customers.append(
            Customer(
                id=customer_id,
                x=order.delivery.lng,
                y=order.delivery.lat,
                demand=max(1, round(order.weight)),
                priority=order.priority,
            )
        )

    distance_service = map_service if payload.use_road_distance else MapRoutingService(backend="fallback")
    scenario = RoutingScenario(
        id=payload.id,
        depot=Depot(id="D0", x=payload.depot.lng, y=payload.depot.lat),
        customers=tuple(customers),
        vehicles=tuple(Vehicle(id=f"V{index}", capacity=payload.vehicle_capacity) for index in range(1, payload.vehicle_count + 1)),
        distance_matrix=distance_service.distance_matrix(locations),
    )
    return scenario_to_dict(scenario_service.save_scenario(scenario))


@router.post("/v1/operational-routes", response_model=OperationalRouteResponse)
def create_operational_route(
    payload: CreateOperationalRouteRequest,
    service: OperationalRouteService = Depends(get_operational_route_service),
) -> dict:
    try:
        return route_to_dict(
            service.create_route(
                route_id=payload.id,
                driver_id=payload.driver_id,
                scenario_id=payload.scenario_id,
                status=payload.status,
                metadata=payload.metadata,
            )
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/v1/operational-routes", response_model=list[OperationalRouteResponse])
def list_operational_routes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    service: OperationalRouteService = Depends(get_operational_route_service),
) -> list[dict]:
    return _paginate([route_to_dict(route) for route in service.list_routes()], skip=skip, limit=limit)


@router.get("/v1/operational-routes/{route_id}", response_model=OperationalRouteResponse)
def get_operational_route(
    route_id: str,
    service: OperationalRouteService = Depends(get_operational_route_service),
) -> dict:
    route = service.get_route(route_id)
    if route is None:
        raise HTTPException(status_code=404, detail="Operational route not found.")
    return route_to_dict(route)


@router.post("/v1/drivers", response_model=DriverResponse)
def create_driver(
    payload: CreateDriverRequest,
    service: DriverService = Depends(get_driver_service),
) -> dict:
    try:
        return driver_to_dict(
            service.create_driver(
                driver_id=payload.id,
                name=payload.name,
                vehicle_id=payload.vehicle_id,
                capacity=payload.capacity,
                status=payload.status,
                region=payload.region,
                shift_start=payload.shift_start,
                shift_end=payload.shift_end,
                metadata=payload.metadata,
            )
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/v1/drivers", response_model=list[DriverResponse])
def list_drivers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    service: DriverService = Depends(get_driver_service),
) -> list[dict]:
    return _paginate([driver_to_dict(driver) for driver in service.list_drivers()], skip=skip, limit=limit)


@router.get("/v1/drivers/{driver_id}", response_model=DriverResponse)
def get_driver(driver_id: str, service: DriverService = Depends(get_driver_service)) -> dict:
    driver = service.get_driver(driver_id)
    if driver is None:
        raise HTTPException(status_code=404, detail="Driver not found.")
    return driver_to_dict(driver)


@router.put("/v1/drivers/{driver_id}", response_model=DriverResponse)
def update_driver(
    driver_id: str,
    payload: UpdateDriverRequest,
    service: DriverService = Depends(get_driver_service),
) -> dict:
    try:
        return driver_to_dict(
            service.update_driver(
                driver_id,
                name=payload.name,
                vehicle_id=payload.vehicle_id,
                capacity=payload.capacity,
                status=payload.status,
                region=payload.region,
                shift_start=payload.shift_start,
                shift_end=payload.shift_end,
                metadata=payload.metadata,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/v1/drivers/{driver_id}")
def delete_driver(
    driver_id: str,
    service: DriverService = Depends(get_driver_service),
    route_service: OperationalRouteService = Depends(get_operational_route_service),
) -> dict:
    driver = service.get_driver(driver_id)
    if driver is None:
        raise HTTPException(status_code=404, detail="Driver not found.")
    updated_routes = route_service.mark_driver_removed(driver_id, driver_snapshot=driver_to_dict(driver))
    deleted = service.delete_driver(driver_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Driver not found.")
    return {"deleted": True, "id": driver_id, "updated_routes": updated_routes}


@router.post("/v1/driver-portal/login", response_model=DriverPortalResponse)
def driver_portal_login(
    payload: DriverLoginRequest,
    driver_service: DriverService = Depends(get_driver_service),
    route_service: OperationalRouteService = Depends(get_operational_route_service),
) -> dict:
    driver = driver_service.authenticate(username=payload.username, password=payload.password)
    if driver is None:
        raise HTTPException(status_code=401, detail="Invalid driver credentials.")
    routes = route_service.list_routes_by_driver(driver.id)
    settings = get_api_settings()
    return {
        "driver": driver_to_dict(driver),
        "routes": [route_to_dict(route) for route in routes],
        "access_token": create_access_token(
            subject=driver.id,
            role="driver",
            secret_key=settings.jwt_secret_key,
            expires_minutes=settings.jwt_expires_minutes,
            extra_claims={"username": driver.metadata.get("username")},
        ),
    }


@router.post("/v1/driver-portal/routes/{route_id}/status", response_model=OperationalRouteResponse)
def driver_update_own_route_status(
    route_id: str,
    payload: DriverRouteStatusRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(driver_bearer),
    driver_service: DriverService = Depends(get_driver_service),
    route_service: OperationalRouteService = Depends(get_operational_route_service),
) -> dict:
    driver = _authenticate_driver(payload, credentials, driver_service)
    route = route_service.get_route(route_id)
    if route is None:
        raise HTTPException(status_code=404, detail="Operational route not found.")
    if route.driver_id != driver.id:
        raise HTTPException(status_code=403, detail="Driver can only edit assigned routes.")
    updated = route_service.update_status(route_id, payload.status)
    if updated is None:
        raise HTTPException(status_code=404, detail="Operational route not found.")
    return route_to_dict(updated)


@router.put("/v1/driver-portal/profile", response_model=DriverResponse)
def driver_update_own_profile(
    payload: DriverProfileUpdateRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(driver_bearer),
    driver_service: DriverService = Depends(get_driver_service),
) -> dict:
    driver = _authenticate_driver(payload, credentials, driver_service)
    metadata = dict(driver.metadata or {})
    if payload.new_password:
        if len(payload.new_password) < 8:
            raise HTTPException(status_code=400, detail="New password must contain at least 8 characters.")
        metadata["temporary_password"] = payload.new_password
    capacity = payload.capacity if payload.capacity is not None else driver.capacity
    if capacity <= 0:
        raise HTTPException(status_code=400, detail="Vehicle capacity must be positive.")
    updated = driver_service.update_driver(
        driver.id,
        name=driver.name,
        vehicle_id=driver.vehicle_id,
        capacity=capacity,
        status=driver.status,
        region=driver.region,
        shift_start=driver.shift_start,
        shift_end=driver.shift_end,
        metadata=metadata,
    )
    return driver_to_dict(updated)


def _authenticate_driver(
    payload: DriverRouteStatusRequest | DriverProfileUpdateRequest,
    credentials: HTTPAuthorizationCredentials | None,
    driver_service: DriverService,
):
    if credentials:
        settings = get_api_settings()
        try:
            claims = decode_access_token(credentials.credentials, secret_key=settings.jwt_secret_key)
        except jwt.PyJWTError as exc:
            raise HTTPException(status_code=401, detail="Invalid driver token.") from exc
        if claims.get("role") != "driver" or not claims.get("sub"):
            raise HTTPException(status_code=403, detail="Invalid driver role.")
        driver = driver_service.get_driver(str(claims["sub"]))
        if driver is None:
            raise HTTPException(status_code=401, detail="Driver no longer exists.")
        return driver

    if not payload.username or not payload.password:
        raise HTTPException(status_code=401, detail="Driver credentials are required.")
    driver = driver_service.authenticate(username=payload.username, password=payload.password)
    if driver is None:
        raise HTTPException(status_code=401, detail="Invalid driver credentials.")
    return driver


@router.post("/v1/planning/daily", response_model=DailyPlanningResponse)
def run_daily_planning(
    payload: DailyPlanningRequest,
    service: DailyPlanningService = Depends(get_daily_planning_service),
) -> dict:
    try:
        return service.run_daily_planning(
            scenario_id=payload.scenario_id,
            route_prefix=payload.route_prefix,
            include_demo_drivers=payload.include_demo_drivers,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/v1/planning/jobs", response_model=PlanningJobResponse)
def start_planning_job(
    payload: DailyPlanningRequest,
    service: PlanningJobService = Depends(get_planning_job_service),
) -> dict:
    try:
        return planning_job_to_dict(
            service.create_job(
                scenario_id=payload.scenario_id,
                route_prefix=payload.route_prefix,
                include_demo_drivers=payload.include_demo_drivers,
            )
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/v1/planning/jobs", response_model=list[PlanningJobResponse])
def list_planning_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    service: PlanningJobService = Depends(get_planning_job_service),
) -> list[dict]:
    return _paginate([planning_job_to_dict(job) for job in service.list_jobs()], skip=skip, limit=limit)


@router.get("/v1/planning/jobs/{job_id}", response_model=PlanningJobResponse)
def get_planning_job(job_id: str, service: PlanningJobService = Depends(get_planning_job_service)) -> dict:
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Planning job not found.")
    return planning_job_to_dict(job)


@router.post("/v1/planning/jobs/{job_id}/cancel", response_model=PlanningJobResponse)
def cancel_planning_job(job_id: str, service: PlanningJobService = Depends(get_planning_job_service)) -> dict:
    job = service.cancel_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Planning job not found.")
    return planning_job_to_dict(job)


@router.delete("/v1/planning/jobs/{job_id}")
def delete_planning_job(job_id: str, service: PlanningJobService = Depends(get_planning_job_service)) -> dict:
    deleted = service.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Planning job not found.")
    return {"deleted": True, "job_id": job_id}


@router.post("/v1/rag/ingest", response_model=RagIngestResponse)
def ingest_rag_documents(
    payload: RagIngestRequest,
    service: RagService = Depends(get_rag_service),
) -> dict:
    try:
        return service.ingest_paths(payload.paths)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/v1/rag/documents")
def list_rag_documents(service: RagService = Depends(get_rag_service)) -> dict:
    return {"documents": service.list_documents(), "chunk_count": service.count_chunks()}


@router.post("/v1/rag/query", response_model=RagQueryResponse)
def query_rag(
    payload: RagQueryRequest,
    service: RagService = Depends(get_rag_service),
) -> dict:
    try:
        return service.query(payload.query, limit=payload.limit)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/v1/maps/route-geometry", response_model=RouteGeometryResponse)
def route_geometry(
    payload: RouteGeometryRequest,
    service: MapRoutingService = Depends(get_map_routing_service),
) -> dict:
    try:
        return service.route_geometry(
            plan=payload.plan,
            locations=payload.locations,
            overview=payload.overview,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
