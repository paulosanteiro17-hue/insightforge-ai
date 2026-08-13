from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar

from insightforge.core.problems import AppError

ItemT = TypeVar("ItemT")


@dataclass(frozen=True, slots=True)
class PageResult(Generic[ItemT]):
    items: list[ItemT]
    page: int
    page_size: int
    total: int


@dataclass(frozen=True, slots=True)
class SortField:
    name: str
    descending: bool


def parse_sort(
    value: str | None,
    *,
    allowed: frozenset[str],
    default: tuple[SortField, ...],
) -> tuple[SortField, ...]:
    if value is None or not value.strip():
        return default
    fields: list[SortField] = []
    seen: set[str] = set()
    for raw_field in value.split(","):
        token = raw_field.strip()
        descending = token.startswith("-")
        name = token[1:] if descending else token
        if not name or name not in allowed or name in seen:
            raise AppError(
                status=422,
                code="validation_error",
                title="Request validation failed",
                detail="One or more sort fields are invalid.",
                errors=[
                    {
                        "field": "sort",
                        "code": "unsupported_sort",
                        "message": "Choose only documented sort fields.",
                    }
                ],
            )
        seen.add(name)
        fields.append(SortField(name=name, descending=descending))
    return tuple(fields)


def validate_time_range(start: datetime | None, end: datetime | None) -> None:
    if any(
        value is not None and (value.tzinfo is None or value.utcoffset() is None)
        for value in (start, end)
    ):
        raise AppError(
            status=422,
            code="validation_error",
            title="Request validation failed",
            detail="Date-time filters must include a UTC offset.",
            errors=[
                {
                    "field": "date_range",
                    "code": "timezone_required",
                    "message": "Include a UTC offset in each date-time filter.",
                }
            ],
        )
    if start is not None and end is not None and start >= end:
        raise AppError(
            status=422,
            code="validation_error",
            title="Request validation failed",
            detail="The start of a range must be earlier than its end.",
            errors=[
                {
                    "field": "created_to",
                    "code": "invalid_range",
                    "message": "The upper bound must be later than the lower bound.",
                }
            ],
        )
