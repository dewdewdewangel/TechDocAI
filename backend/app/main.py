import logging
import time
import uuid

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.routing import APIRoute
from prometheus_client import make_asgi_app
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.core.observability import HTTP_DURATION, HTTP_REQUESTS

logger = logging.getLogger("app.requests")


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)


@app.middleware("http")
async def observe_request(request: Request, call_next):  # type: ignore[no-untyped-def]
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    started = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        duration = time.perf_counter() - started
        HTTP_REQUESTS.labels(
            method=request.method,
            route=route_path,
            status=str(status_code),
        ).inc()
        HTTP_DURATION.labels(
            method=request.method,
            route=route_path,
        ).observe(duration)
        logger.info(
            "request_completed method=%s route=%s status=%s duration_ms=%.2f request_id=%s",
            request.method,
            route_path,
            status_code,
            duration * 1000,
            request_id,
        )


# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

if settings.METRICS_ENABLED:
    app.mount("/metrics", make_asgi_app())
