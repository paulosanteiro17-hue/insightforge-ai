from __future__ import annotations

import logging
import time
import uuid
from http import HTTPStatus

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)


class RequestBodyLimitMiddleware:
    """Reject oversized declared or streamed request bodies before application parsing."""

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        if max_bytes < 1:
            raise ValueError("The request body limit must be positive.")
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = self._content_length(scope)
        if content_length is None:
            await self._stream_with_limit(scope, receive, send)
            return
        if content_length < 0:
            await self._send_problem(
                scope,
                receive,
                send,
                status=400,
                code="invalid_content_length",
            )
            return
        if content_length > self.max_bytes:
            await self._send_problem(scope, receive, send, status=413, code="request_too_large")
            return
        await self._stream_with_limit(scope, receive, send)

    @staticmethod
    def _content_length(scope: Scope) -> int | None:
        values = [value for key, value in scope.get("headers", []) if key == b"content-length"]
        if not values:
            return None
        try:
            if len(values) != 1:
                return -1
            return int(values[0].decode("ascii"))
        except (UnicodeDecodeError, ValueError):
            return -1

    async def _stream_with_limit(self, scope: Scope, receive: Receive, send: Send) -> None:
        received = 0
        exceeded = False
        response_started = False

        async def limited_receive() -> Message:
            nonlocal exceeded, received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    exceeded = True
                    return {"type": "http.disconnect"}
            return message

        async def guarded_send(message: Message) -> None:
            nonlocal response_started
            if exceeded:
                return
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except Exception:
            if not exceeded:
                raise
        if exceeded and not response_started:
            await self._send_problem(
                scope,
                receive,
                send,
                status=413,
                code="request_too_large",
            )

    @staticmethod
    async def _send_problem(
        scope: Scope,
        receive: Receive,
        send: Send,
        *,
        status: int,
        code: str,
    ) -> None:
        request = Request(scope, receive=receive)
        detail = (
            "The request body exceeds the configured limit."
            if status == 413
            else "The Content-Length header is invalid."
        )
        response = JSONResponse(
            status_code=status,
            media_type="application/problem+json",
            content={
                "type": f"https://docs.insightforge.example/problems/{code.replace('_', '-')}",
                "title": HTTPStatus(status).phrase,
                "status": status,
                "detail": detail,
                "instance": request.url.path,
                "code": code,
                "request_id": str(getattr(request.state, "request_id", "unknown")),
            },
        )
        await response(scope, receive, send)


def normalized_request_id(value: str | None) -> uuid.UUID:
    if value:
        try:
            return uuid.UUID(value)
        except (ValueError, AttributeError):
            return uuid.uuid4()
    return uuid.uuid4()


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, enable_hsts: bool = False) -> None:
        super().__init__(app)
        self.enable_hsts = enable_hsts

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = normalized_request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1_000, 2)

        response.headers["X-Request-ID"] = str(request_id)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        if self.enable_hsts:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        if (
            request.headers.get("X-Organization-ID")
            or request.cookies
            or "set-cookie" in response.headers
        ):
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
