from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from insightforge.api.health import router as health_router
from insightforge.api.rate_limits import RequestRateLimits
from insightforge.api.v1.router import router as v1_router
from insightforge.core.config import Settings, get_settings
from insightforge.core.logging import configure_logging
from insightforge.core.middleware import RequestBodyLimitMiddleware, RequestContextMiddleware
from insightforge.core.problems import install_exception_handlers
from insightforge.db.session import get_engine


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()
    configure_logging(runtime_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await get_engine(runtime_settings.database_url).dispose()

    application = FastAPI(
        title=runtime_settings.app_name,
        version=runtime_settings.build_version,
        docs_url=runtime_settings.docs_url,
        redoc_url=None,
        openapi_url=f"{runtime_settings.api_prefix}/openapi.json",
        lifespan=lifespan,
    )
    application.state.request_rate_limits = RequestRateLimits(runtime_settings)
    if settings is not None:
        application.dependency_overrides[get_settings] = lambda: runtime_settings

    install_exception_handlers(application)
    application.add_middleware(
        RequestBodyLimitMiddleware,
        max_bytes=runtime_settings.request_max_bytes,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=runtime_settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Content-Type",
            "Idempotency-Key",
            "If-Match",
            "X-CSRF-Token",
            "X-Organization-ID",
            "X-Request-ID",
        ],
        expose_headers=[
            "ETag",
            "Idempotency-Replayed",
            "Location",
            "Retry-After",
            "X-Request-ID",
        ],
    )
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=runtime_settings.allowed_hosts,
    )
    application.add_middleware(
        RequestContextMiddleware,
        enable_hsts=runtime_settings.environment in {"staging", "production"},
    )
    application.include_router(health_router)
    application.include_router(v1_router, prefix=runtime_settings.api_prefix)
    return application


app = create_app()
