from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    host: str = Field(default="0.0.0.0", alias="ADAPTIVEROUTE_API_HOST")
    port: int = Field(default=8090, alias="ADAPTIVEROUTE_API_PORT")
    cors_allow_origins: str = Field(
        default="http://127.0.0.1:5173,http://localhost:5173",
        alias="ADAPTIVEROUTE_CORS_ALLOW_ORIGINS",
    )
    jwt_secret_key: str = Field(default="adaptiveroute-dev-secret-change-me", alias="ADAPTIVEROUTE_JWT_SECRET_KEY")
    jwt_expires_minutes: int = Field(default=480, alias="ADAPTIVEROUTE_JWT_EXPIRES_MINUTES")
    memory_backend: Literal["memory", "mongo"] = Field(default="memory", alias="ADAPTIVEROUTE_MEMORY_BACKEND")
    mongodb_uri: str = Field(default="mongodb://mongo:27017", alias="MONGODB_URI")
    mongodb_database: str = Field(default="adaptiveroute", alias="MONGODB_DATABASE")
    context_recent_messages: int = Field(default=8, alias="ADAPTIVEROUTE_CONTEXT_RECENT_MESSAGES")
    context_summary_max_chars: int = Field(default=4000, alias="ADAPTIVEROUTE_CONTEXT_SUMMARY_MAX_CHARS")
    rag_backend: Literal["memory", "pgvector"] = Field(default="memory", alias="ADAPTIVEROUTE_RAG_BACKEND")
    rag_postgres_dsn: str = Field(
        default="postgresql://adaptiveroute:adaptiveroute@postgres:5432/adaptiveroute",
        alias="ADAPTIVEROUTE_RAG_POSTGRES_DSN",
    )
    rag_embedding_dim: int = Field(default=384, alias="ADAPTIVEROUTE_RAG_EMBEDDING_DIM")
    rag_chunk_size: int = Field(default=1200, alias="ADAPTIVEROUTE_RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=160, alias="ADAPTIVEROUTE_RAG_CHUNK_OVERLAP")
    map_router_backend: Literal["fallback", "osrm"] = Field(default="fallback", alias="ADAPTIVEROUTE_MAP_ROUTER_BACKEND")
    osrm_base_url: str = Field(default="http://osrm:5000", alias="ADAPTIVEROUTE_OSRM_BASE_URL")
    osrm_timeout_seconds: float = Field(default=8.0, alias="ADAPTIVEROUTE_OSRM_TIMEOUT_SECONDS")
    solver_time_limit_seconds: float | None = Field(default=None, alias="ADAPTIVEROUTE_SOLVER_TIME_LIMIT_SECONDS")
    solver_mip_gap: float | None = Field(default=None, alias="ADAPTIVEROUTE_SOLVER_MIP_GAP")


@lru_cache
def get_api_settings() -> ApiSettings:
    return ApiSettings()


def parse_cors_origins(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]
