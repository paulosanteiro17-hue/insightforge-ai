from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from insightforge.core.problems import AppError

RangePreset = Literal["7d", "30d", "90d", "year_to_date", "custom"]
ComparisonMode = Literal["previous_period", "previous_year", "none"]
Granularity = Literal["day", "week", "month"]


@dataclass(frozen=True, slots=True)
class DateTimeRange:
    start: datetime
    end: datetime


@dataclass(frozen=True, slots=True)
class EffectiveAnalyticsRange:
    current: DateTimeRange
    comparison: DateTimeRange | None
    granularity: Granularity
    time_zone: str


def _validation(detail: str, field: str) -> AppError:
    return AppError(
        status=422,
        code="validation_error",
        title="Request validation failed",
        detail=detail,
        errors=[{"field": field, "code": "invalid_range", "message": detail}],
    )


def _replace_year(value: datetime, year: int) -> datetime:
    try:
        return value.replace(year=year)
    except ValueError:
        return value.replace(year=year, day=28)


def resolve_analytics_range(
    *,
    preset: RangePreset,
    compare: ComparisonMode,
    requested_granularity: Granularity | None,
    date_from: date | None,
    date_to: date | None,
    time_zone: str,
    now: datetime,
) -> EffectiveAnalyticsRange:
    try:
        zone = ZoneInfo(time_zone)
    except ZoneInfoNotFoundError as exc:
        raise _validation("The organization time zone is invalid.", "time_zone") from exc
    local_now = now.astimezone(zone)
    if preset == "custom":
        if date_from is None or date_to is None:
            raise _validation(
                "Custom ranges require both date_from and date_to.",
                "date_from",
            )
        current_start_local = datetime.combine(date_from, datetime.min.time(), zone)
        current_end_local = datetime.combine(date_to, datetime.min.time(), zone)
    else:
        if date_from is not None or date_to is not None:
            raise _validation(
                "Preset ranges do not accept custom dates.",
                "date_from",
            )
        current_end_local = local_now
        if preset == "7d":
            current_start_local = current_end_local - timedelta(days=7)
        elif preset == "30d":
            current_start_local = current_end_local - timedelta(days=30)
        elif preset == "90d":
            current_start_local = current_end_local - timedelta(days=90)
        else:
            current_start_local = datetime(local_now.year, 1, 1, tzinfo=zone)
    if current_start_local >= current_end_local:
        raise _validation("date_to must be later than date_from.", "date_to")
    duration = current_end_local - current_start_local
    if duration > timedelta(days=730):
        raise _validation("Analytics ranges cannot exceed 730 days.", "date_to")

    if requested_granularity is not None:
        granularity = requested_granularity
    elif duration <= timedelta(days=45):
        granularity = "day"
    elif duration <= timedelta(days=180):
        granularity = "week"
    else:
        granularity = "month"
    if granularity == "day" and duration > timedelta(days=120):
        raise _validation("Day granularity supports ranges up to 120 days.", "granularity")
    if granularity == "week" and duration < timedelta(days=14):
        raise _validation("Week granularity requires at least 14 days.", "granularity")
    if granularity == "month" and duration < timedelta(days=60):
        raise _validation("Month granularity requires at least 60 days.", "granularity")

    comparison_local: tuple[datetime, datetime] | None
    if compare == "none":
        comparison_local = None
    elif compare == "previous_year":
        comparison_local = (
            _replace_year(current_start_local, current_start_local.year - 1),
            _replace_year(current_end_local, current_end_local.year - 1),
        )
    else:
        comparison_local = (current_start_local - duration, current_start_local)

    return EffectiveAnalyticsRange(
        current=DateTimeRange(
            start=current_start_local.astimezone(UTC),
            end=current_end_local.astimezone(UTC),
        ),
        comparison=(
            DateTimeRange(
                start=comparison_local[0].astimezone(UTC),
                end=comparison_local[1].astimezone(UTC),
            )
            if comparison_local is not None
            else None
        ),
        granularity=granularity,
        time_zone=time_zone,
    )
