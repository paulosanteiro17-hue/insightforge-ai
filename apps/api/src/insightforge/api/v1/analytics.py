from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from insightforge.analytics.ranges import EffectiveAnalyticsRange, resolve_analytics_range
from insightforge.api.dependencies import (
    TenantContextDependency,
    get_analytics_service,
)
from insightforge.core.time import utc_now
from insightforge.schemas.analytics import AnalyticsFilterOptionsView, AnalyticsView
from insightforge.schemas.common import DataEnvelope
from insightforge.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])
AnalyticsServiceDependency = Annotated[AnalyticsService, Depends(get_analytics_service)]


def effective_analytics_range(
    context: TenantContextDependency,
    range_value: Annotated[
        Literal["7d", "30d", "90d", "year_to_date", "custom"],
        Query(alias="range"),
    ] = "30d",
    compare: Literal["previous_period", "previous_year", "none"] = "previous_period",
    granularity: Literal["day", "week", "month"] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> EffectiveAnalyticsRange:
    return resolve_analytics_range(
        preset=range_value,
        compare=compare,
        requested_granularity=granularity,
        date_from=date_from,
        date_to=date_to,
        time_zone=context.organization.timezone,
        now=utc_now(),
    )


AnalyticsRangeDependency = Annotated[
    EffectiveAnalyticsRange,
    Depends(effective_analytics_range),
]


@router.get("/overview", response_model=DataEnvelope[AnalyticsView])
@router.get("/revenue", response_model=DataEnvelope[AnalyticsView])
@router.get("/sales", response_model=DataEnvelope[AnalyticsView])
@router.get("/customers", response_model=DataEnvelope[AnalyticsView])
@router.get("/products", response_model=DataEnvelope[AnalyticsView])
@router.get("/orders", response_model=DataEnvelope[AnalyticsView])
@router.get("/mrr", response_model=DataEnvelope[AnalyticsView])
@router.get("/categories", response_model=DataEnvelope[AnalyticsView])
@router.get("/order-statuses", response_model=DataEnvelope[AnalyticsView])
@router.get("/acquisition", response_model=DataEnvelope[AnalyticsView])
@router.get("/recent-transactions", response_model=DataEnvelope[AnalyticsView])
async def analytics_snapshot(
    context: TenantContextDependency,
    effective_range: AnalyticsRangeDependency,
    service: AnalyticsServiceDependency,
) -> DataEnvelope[AnalyticsView]:
    return DataEnvelope(data=await service.snapshot(context, effective_range))


@router.get(
    "/filter-options",
    response_model=DataEnvelope[AnalyticsFilterOptionsView],
)
async def analytics_filter_options(
    context: TenantContextDependency,
    effective_range: AnalyticsRangeDependency,
    service: AnalyticsServiceDependency,
) -> DataEnvelope[AnalyticsFilterOptionsView]:
    return DataEnvelope(data=await service.filter_options(context, effective_range))
