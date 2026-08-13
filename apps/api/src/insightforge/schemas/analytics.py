from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import Field

from insightforge.schemas.common import StrictSchema


class AnalyticsRangeView(StrictSchema):
    start: datetime
    end: datetime


class ComparisonMetricView(StrictSchema):
    value: int | float | None
    comparison_value: int | float | None
    change_ratio: float | None
    change_status: Literal[
        "increase",
        "decrease",
        "unchanged",
        "new",
        "not_comparable",
    ]


class AvailabilityMetricView(StrictSchema):
    value: int | float | None = None
    available: bool
    reason: str | None = None


class TimeSeriesPointView(StrictSchema):
    period_start: date
    revenue_minor: int = 0
    order_count: int = 0
    new_customers: int = 0


class BreakdownView(StrictSchema):
    id: uuid.UUID | None = None
    label: str
    revenue_minor: int = 0
    units: int = 0
    count: int = 0
    share_ratio: float | None = None


class RecentTransactionView(StrictSchema):
    id: uuid.UUID
    order_number: str
    customer_name: str
    status: str
    total_minor: int
    currency: str
    ordered_at: datetime


class AnalyticsView(StrictSchema):
    range: AnalyticsRangeView
    comparison_range: AnalyticsRangeView | None
    granularity: Literal["day", "week", "month"]
    time_zone: str
    currency: str
    metric_version: str = "v1"
    source_revision: int
    generated_at: datetime
    data_availability: Literal["available", "empty"]
    metrics: dict[str, ComparisonMetricView] = Field(default_factory=dict)
    revenue_series: list[TimeSeriesPointView] = Field(default_factory=list)
    order_series: list[TimeSeriesPointView] = Field(default_factory=list)
    customer_acquisition: list[TimeSeriesPointView] = Field(default_factory=list)
    categories: list[BreakdownView] = Field(default_factory=list)
    products: list[BreakdownView] = Field(default_factory=list)
    order_statuses: list[BreakdownView] = Field(default_factory=list)
    recent_transactions: list[RecentTransactionView] = Field(default_factory=list)
    conversion_rate: AvailabilityMetricView = Field(
        default_factory=lambda: AvailabilityMetricView(
            available=False,
            reason="Conversion observations are not available for this range.",
        )
    )
    mrr: AvailabilityMetricView = Field(
        default_factory=lambda: AvailabilityMetricView(
            available=False,
            reason="Imported recurring revenue observations are not available for this range.",
        )
    )


class AnalyticsFilterOptionsView(StrictSchema):
    range: AnalyticsRangeView
    comparison_range: AnalyticsRangeView | None
    granularity: Literal["day", "week", "month"]
    time_zone: str
    currency: str
    metric_version: str = "v1"
    source_revision: int
    generated_at: datetime
    categories: list[str]
    order_statuses: list[str]
    sources: list[str]
