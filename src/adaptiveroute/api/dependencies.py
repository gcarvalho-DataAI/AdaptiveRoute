from __future__ import annotations

from functools import lru_cache

from adaptiveroute.agentic import AgenticRoutingService
from adaptiveroute.api.settings import ApiSettings, get_api_settings
from adaptiveroute.drivers import DriverService, InMemoryDriverRepository, MongoDriverRepository, DriverRepository
from adaptiveroute.memory.repository import ConversationRepository, InMemoryConversationRepository, MongoConversationRepository
from adaptiveroute.memory.service import ConversationService
from adaptiveroute.maps import MapRoutingService
from adaptiveroute.operations.repository import (
    InMemoryOperationalRouteRepository,
    MongoOperationalRouteRepository,
    OperationalRouteRepository,
)
from adaptiveroute.operations.service import OperationalRouteService
from adaptiveroute.planning import (
    DailyPlanningService,
    InMemoryPlanningJobRepository,
    MongoPlanningJobRepository,
    PlanningJobRepository,
    PlanningJobService,
)
from adaptiveroute.rag.embeddings import build_embedding_client
from adaptiveroute.rag.repository import InMemoryRagRepository, PgVectorRagRepository, RagRepository
from adaptiveroute.rag.service import RagService
from adaptiveroute.scenarios.repository import InMemoryScenarioRepository, MongoScenarioRepository, ScenarioRepository
from adaptiveroute.scenarios.service import ScenarioService
from adaptiveroute.solvers.pyomo_highs import PyomoHighsEngine


def get_solver_engine() -> PyomoHighsEngine:
    settings = get_api_settings()
    return PyomoHighsEngine(time_limit_seconds=settings.solver_time_limit_seconds, mip_gap=settings.solver_mip_gap)


@lru_cache
def get_repository() -> ConversationRepository:
    settings = get_api_settings()
    if settings.memory_backend == "mongo":
        return MongoConversationRepository(uri=settings.mongodb_uri, database=settings.mongodb_database)
    return InMemoryConversationRepository()


@lru_cache
def get_agentic_service() -> AgenticRoutingService:
    return AgenticRoutingService.from_env(get_solver_engine())


def get_conversation_service() -> ConversationService:
    settings: ApiSettings = get_api_settings()
    scenario_service = get_scenario_service()
    operational_route_service = get_operational_route_service()
    return ConversationService(
        repository=get_repository(),
        agentic_service=get_agentic_service(),
        scenario_resolver=scenario_service.get_scenario,
        scenario_saver=scenario_service.save_scenario,
        route_resolver=operational_route_service.get_route,
        route_plan_updater=operational_route_service.update_current_plan,
        rag_query=lambda query, limit: get_rag_service().query(query, limit=limit),
        recent_message_limit=settings.context_recent_messages,
        summary_max_chars=settings.context_summary_max_chars,
    )


@lru_cache
def get_scenario_repository() -> ScenarioRepository:
    settings = get_api_settings()
    if settings.memory_backend == "mongo":
        return MongoScenarioRepository(uri=settings.mongodb_uri, database=settings.mongodb_database)
    repository = InMemoryScenarioRepository()
    return repository


def get_scenario_service() -> ScenarioService:
    service = ScenarioService(get_scenario_repository())
    service.get_or_seed_demo_scenario()
    return service


@lru_cache
def get_operational_route_repository() -> OperationalRouteRepository:
    settings = get_api_settings()
    if settings.memory_backend == "mongo":
        return MongoOperationalRouteRepository(uri=settings.mongodb_uri, database=settings.mongodb_database)
    return InMemoryOperationalRouteRepository()


def get_operational_route_service() -> OperationalRouteService:
    return OperationalRouteService(
        repository=get_operational_route_repository(),
        scenario_service=get_scenario_service(),
        engine=get_solver_engine(),
    )


@lru_cache
def get_driver_repository() -> DriverRepository:
    settings = get_api_settings()
    if settings.memory_backend == "mongo":
        return MongoDriverRepository(uri=settings.mongodb_uri, database=settings.mongodb_database)
    return InMemoryDriverRepository()


def get_driver_service() -> DriverService:
    return DriverService(get_driver_repository())


def get_daily_planning_service() -> DailyPlanningService:
    return DailyPlanningService(
        driver_service=get_driver_service(),
        scenario_service=get_scenario_service(),
        operational_route_service=get_operational_route_service(),
        engine=get_solver_engine(),
    )


@lru_cache
def get_planning_job_repository() -> PlanningJobRepository:
    settings = get_api_settings()
    if settings.memory_backend == "mongo":
        return MongoPlanningJobRepository(uri=settings.mongodb_uri, database=settings.mongodb_database)
    return InMemoryPlanningJobRepository()


def get_planning_job_service() -> PlanningJobService:
    return PlanningJobService(get_planning_job_repository())


@lru_cache
def get_rag_repository() -> RagRepository:
    settings = get_api_settings()
    if settings.rag_backend == "pgvector":
        return PgVectorRagRepository(dsn=settings.rag_postgres_dsn, embedding_dim=settings.rag_embedding_dim)
    return InMemoryRagRepository()


def get_rag_service() -> RagService:
    settings = get_api_settings()
    return RagService(
        repository=get_rag_repository(),
        embedding_client=build_embedding_client(),
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
    )


def get_map_routing_service() -> MapRoutingService:
    settings = get_api_settings()
    return MapRoutingService(
        backend=settings.map_router_backend,
        osrm_base_url=settings.osrm_base_url,
        timeout_seconds=settings.osrm_timeout_seconds,
    )


def clear_dependency_caches() -> None:
    get_api_settings.cache_clear()
    get_repository.cache_clear()
    get_agentic_service.cache_clear()
    get_scenario_repository.cache_clear()
    get_operational_route_repository.cache_clear()
    get_driver_repository.cache_clear()
    get_planning_job_repository.cache_clear()
    get_rag_repository.cache_clear()
