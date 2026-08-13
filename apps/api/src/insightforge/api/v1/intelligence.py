from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, Query, Response, status

from insightforge.analytics.ranges import EffectiveAnalyticsRange, resolve_analytics_range
from insightforge.api.dependencies import (
    TenantContext,
    get_analytics_service,
    get_generation_job_service,
    get_intelligence_service,
    require_csrf,
    require_permission,
)
from insightforge.api.rate_limits import (
    ASK_DATA,
    INTELLIGENCE_GENERATION,
    RequestRateLimitsDependency,
)
from insightforge.api.v1.analytics import AnalyticsRangeDependency
from insightforge.core.policies import Permission
from insightforge.core.time import utc_now
from insightforge.schemas.common import (
    CollectionEnvelope,
    CollectionMeta,
    DataEnvelope,
    PaginationView,
)
from insightforge.schemas.generation_jobs import GenerationJobView
from insightforge.schemas.intelligence import (
    AskCapabilitiesView,
    AskQuestionRequest,
    AssistantAnswerView,
    InsightView,
    WeeklySummaryView,
)
from insightforge.services.analytics import AnalyticsService
from insightforge.services.generation_jobs import GenerationJobService
from insightforge.services.intelligence import IntelligenceService

router = APIRouter(tags=["Intelligence"])
IntelligenceContext = Annotated[
    TenantContext,
    require_permission(Permission.ASK_ANALYTICS),
]
AnalyticsServiceDependency = Annotated[AnalyticsService, Depends(get_analytics_service)]
IntelligenceServiceDependency = Annotated[
    IntelligenceService,
    Depends(get_intelligence_service),
]
GenerationJobServiceDependency = Annotated[
    GenerationJobService,
    Depends(get_generation_job_service),
]


def _current_week_range(context: TenantContext) -> EffectiveAnalyticsRange:
    now = utc_now()
    local_today = now.astimezone(ZoneInfo(context.time_zone)).date()
    return resolve_analytics_range(
        preset="custom",
        compare="previous_period",
        requested_granularity="day",
        date_from=local_today - timedelta(days=7),
        date_to=local_today,
        time_zone=context.time_zone,
        now=now,
    )


@router.get("/insights", response_model=CollectionEnvelope[InsightView])
async def list_insights(
    context: IntelligenceContext,
    service: IntelligenceServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> CollectionEnvelope[InsightView]:
    result = await service.list_insights(context, page=page, page_size=page_size)
    return CollectionEnvelope(
        data=result.items,
        meta=CollectionMeta(
            pagination=PaginationView.from_values(
                page=result.page,
                page_size=result.page_size,
                total=result.total,
            ),
            filters={"status": "active"},
        ),
    )


@router.post(
    "/insights/generation-jobs",
    response_model=DataEnvelope[GenerationJobView],
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_csrf)],
)
async def create_insight_generation_job(
    response: Response,
    context: IntelligenceContext,
    effective_range: AnalyticsRangeDependency,
    service: GenerationJobServiceDependency,
    rate_limits: RequestRateLimitsDependency,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> DataEnvelope[GenerationJobView]:
    await rate_limits.enforce(
        scope=INTELLIGENCE_GENERATION,
        subject=f"{context.organization_id}:{context.user_id}",
    )
    job, replayed = await service.enqueue(
        context,
        job_type="generate_insights",
        effective_range=effective_range,
        idempotency_key=idempotency_key,
    )
    response.headers["Location"] = f"/api/v1/insights/generation-jobs/{job.id}"
    response.headers["Idempotency-Replayed"] = "true" if replayed else "false"
    return DataEnvelope(data=job)


@router.get(
    "/insights/generation-jobs/{job_id}",
    response_model=DataEnvelope[GenerationJobView],
)
async def get_insight_generation_job(
    job_id: uuid.UUID,
    context: IntelligenceContext,
    service: GenerationJobServiceDependency,
) -> DataEnvelope[GenerationJobView]:
    return DataEnvelope(data=await service.get(context, job_id, job_type="generate_insights"))


@router.get("/insights/{insight_id}", response_model=DataEnvelope[InsightView])
async def get_insight(
    insight_id: uuid.UUID,
    context: IntelligenceContext,
    service: IntelligenceServiceDependency,
) -> DataEnvelope[InsightView]:
    return DataEnvelope(data=await service.get_insight(context, insight_id))


@router.get(
    "/weekly-summary/current",
    response_model=DataEnvelope[WeeklySummaryView],
)
async def get_current_weekly_summary(
    context: IntelligenceContext,
    service: IntelligenceServiceDependency,
) -> DataEnvelope[WeeklySummaryView]:
    effective_range = _current_week_range(context)
    week_start = effective_range.current.start.astimezone(ZoneInfo(context.time_zone)).date()
    return DataEnvelope(data=await service.get_weekly_summary(context, week_start))


@router.post(
    "/weekly-summary/generation-jobs",
    response_model=DataEnvelope[GenerationJobView],
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_csrf)],
)
async def create_weekly_summary_generation_job(
    response: Response,
    context: IntelligenceContext,
    service: GenerationJobServiceDependency,
    rate_limits: RequestRateLimitsDependency,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> DataEnvelope[GenerationJobView]:
    await rate_limits.enforce(
        scope=INTELLIGENCE_GENERATION,
        subject=f"{context.organization_id}:{context.user_id}",
    )
    job, replayed = await service.enqueue(
        context,
        job_type="generate_weekly_summary",
        effective_range=_current_week_range(context),
        idempotency_key=idempotency_key,
    )
    response.headers["Location"] = f"/api/v1/weekly-summary/generation-jobs/{job.id}"
    response.headers["Idempotency-Replayed"] = "true" if replayed else "false"
    return DataEnvelope(data=job)


@router.get(
    "/weekly-summary/generation-jobs/{job_id}",
    response_model=DataEnvelope[GenerationJobView],
)
async def get_weekly_summary_generation_job(
    job_id: uuid.UUID,
    context: IntelligenceContext,
    service: GenerationJobServiceDependency,
) -> DataEnvelope[GenerationJobView]:
    return DataEnvelope(data=await service.get(context, job_id, job_type="generate_weekly_summary"))


@router.get(
    "/ask-data/capabilities",
    response_model=DataEnvelope[AskCapabilitiesView],
)
async def ask_data_capabilities(
    _context: IntelligenceContext,
    service: IntelligenceServiceDependency,
) -> DataEnvelope[AskCapabilitiesView]:
    return DataEnvelope(data=service.capabilities())


@router.post(
    "/ask-data/answers",
    response_model=DataEnvelope[AssistantAnswerView],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_ask_data_answer(
    payload: AskQuestionRequest,
    response: Response,
    context: IntelligenceContext,
    effective_range: AnalyticsRangeDependency,
    analytics: AnalyticsServiceDependency,
    service: IntelligenceServiceDependency,
    rate_limits: RequestRateLimitsDependency,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> DataEnvelope[AssistantAnswerView]:
    await rate_limits.enforce(
        scope=ASK_DATA,
        subject=f"{context.organization_id}:{context.user_id}",
    )
    snapshot = await analytics.snapshot(context, effective_range)
    answer, replayed = await service.ask_idempotent(
        context,
        snapshot,
        payload,
        idempotency_key=idempotency_key,
    )
    response.headers["Location"] = f"/api/v1/ask-data/history#{answer.id}"
    response.headers["Idempotency-Replayed"] = "true" if replayed else "false"
    return DataEnvelope(data=answer)


@router.get(
    "/ask-data/history",
    response_model=CollectionEnvelope[AssistantAnswerView],
)
async def list_ask_data_history(
    context: IntelligenceContext,
    service: IntelligenceServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> CollectionEnvelope[AssistantAnswerView]:
    result = await service.history(context, page=page, page_size=page_size)
    return CollectionEnvelope(
        data=result.items,
        meta=CollectionMeta(
            pagination=PaginationView.from_values(
                page=result.page,
                page_size=result.page_size,
                total=result.total,
            ),
            filters={"requester": str(context.user_id)},
        ),
    )
