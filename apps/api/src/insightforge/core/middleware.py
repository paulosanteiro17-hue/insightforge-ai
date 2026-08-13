from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


def normalized_request_id(value: str | None) -> uuid.UUID:
    if value:
        try:
            return uuid.UUID(value)
        except (ValueError, AttributeError):
            return uuid.uuid4()
    return uuid.uuid4()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = normalized_request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1_000, 2)

        response.headers["X-Request-ID"] = str(request_id)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        if request.headers.get("X-Organization-ID") or request.cookies:
            response.headers.setdefault("Cache-Control", "private, no-store")

        route = request.scope.get("route")
        route_template = getattr(route, "path", request.url.path)
        logger.info(
            "http_request_completed",
            extra={
                "request_id": str(request_id),
                "method": request.method,
                "route": route_template,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
