from __future__ import annotations

from datetime import UTC, datetime

from insightforge.core.problems import AppError
from insightforge.core.time import utc_now


def _not_found() -> AppError:
    return AppError(
        status=404,
        code="resource_not_found",
        title="Resource not found",
        detail="The requested resource was not found.",
    )


def _duplicate(detail: str) -> AppError:
    return AppError(
        status=409,
        code="duplicate_resource",
        title="Resource already exists",
        detail=detail,
    )


def _normalize_datetime(value: datetime | None) -> datetime:
    if value is None:
        return utc_now()
    if value.tzinfo is None:
        raise AppError(
            status=422,
            code="validation_error",
            title="Request validation failed",
            detail="Timestamps must include a UTC offset.",
        )
    return value.astimezone(UTC)


def _average_minor(total_minor: int, count: int) -> int | None:
    return round(total_minor / count) if count else None
