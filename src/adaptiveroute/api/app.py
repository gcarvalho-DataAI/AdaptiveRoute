from __future__ import annotations

import json
import logging
import sys
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from adaptiveroute.api.routes import router
from adaptiveroute.api.settings import get_api_settings, is_insecure_jwt_secret, parse_cors_origins


logger = logging.getLogger("adaptiveroute.api")


def configure_logging() -> None:
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.propagate = False


def create_app() -> FastAPI:
    configure_logging()
    settings = get_api_settings()
    if is_insecure_jwt_secret(settings.jwt_secret_key):
        logger.warning(
            json.dumps(
                {
                    "event": "insecure_jwt_secret_replaced",
                    "message": "Configured JWT secret is a placeholder; using a process-local random secret.",
                },
                sort_keys=True,
            )
        )
    app = FastAPI(title="AdaptiveRoute Agentic API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=parse_cors_origins(settings.cors_allow_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        started_at = perf_counter()
        response = await call_next(request)
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
                sort_keys=True,
            )
        )
        response.headers["x-request-id"] = request_id
        return response
    return app


app = create_app()
