from __future__ import annotations

import logging
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AppError(Exception):
    status: int
    code: str
    title: str
    detail: str
    errors: list[dict[str, str]] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        Exception.__init__(self, self.detail)


def request_id_from(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def problem_response(
    request: Request,
    *,
    status: int,
    code: str,
    title: str,
    detail: str,
    errors: list[dict[str, str]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    slug = code.replace("_", "-")
    body: dict[str, Any] = {
        "type": f"https://docs.insightforge.example/problems/{slug}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        "code": code,
        "request_id": request_id_from(request),
    }
    if errors:
        body["errors"] = errors
    return JSONResponse(
        status_code=status,
        content=body,
        media_type="application/problem+json",
        headers=headers,
    )


def validation_fields(exc: RequestValidationError) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", ()) if part not in {"body", "query"}]
        error_type = str(error.get("type", "invalid_value")).replace(".", "_")
        fields.append(
            {
                "field": ".".join(location) or "request",
                "code": error_type,
                "message": "This value is invalid.",
            }
        )
    return fields


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return problem_response(
            request,
            status=exc.status,
            code=exc.code,
            title=exc.title,
            detail=exc.detail,
            errors=exc.errors,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return problem_response(
            request,
            status=422,
            code="validation_error",
            title="Request validation failed",
            detail="One or more fields are invalid.",
            errors=validation_fields(exc),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        status = exc.status_code
        if status == 404:
            code = "resource_not_found"
            detail = "The requested resource was not found."
        elif status == 405:
            code = "method_not_allowed"
            detail = "The requested method is not allowed for this resource."
        else:
            code = "bad_request" if status < 500 else "internal_error"
            detail = HTTPStatus(status).phrase
        return problem_response(
            request,
            status=status,
            code=code,
            title=HTTPStatus(status).phrase,
            detail=detail,
            headers=dict(exc.headers or {}),
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception(
            "database_request_failed",
            extra={"request_id": request_id_from(request)},
        )
        return problem_response(
            request,
            status=503,
            code="service_unavailable",
            title="Service temporarily unavailable",
            detail="The service is temporarily unable to complete this request.",
            headers={"Retry-After": "2"},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_request_error",
            extra={"request_id": request_id_from(request)},
        )
        return problem_response(
            request,
            status=500,
            code="internal_error",
            title="Internal server error",
            detail="An unexpected error occurred. Use the request ID when contacting support.",
        )
