from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, cast

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.analytics.ranges import EffectiveAnalyticsRange
from insightforge.core.problems import AppError
from insightforge.models import BackgroundJob
from insightforge.schemas.generation_jobs import (
    GenerationJobStatus,
    GenerationJobType,
    GenerationJobView,
)
from insightforge.services.idempotency import (
    IdempotencyService,
    canonical_request_hash,
    validate_uuid_idempotency_key,
)

if TYPE_CHECKING:
    from insightforge.api.dependencies import TenantContext


def analytics_range_payload(value: EffectiveAnalyticsRange) -> dict[str, object]:
    return {
        "start": value.current.start.isoformat(),
        "end": value.current.end.isoformat(),
        "comparison_start": (
            value.comparison.start.isoformat() if value.comparison is not None else None
        ),
        "comparison_end": (
            value.comparison.end.isoformat() if value.comparison is not None else None
        ),
        "granularity": value.granularity,
        "time_zone": value.time_zone,
    }


def generation_job_view(row: BackgroundJob) -> GenerationJobView:
    result = row.payload.get("result")
    return GenerationJobView(
        id=row.id,
        job_type=cast(GenerationJobType, row.job_type),
        status=cast(GenerationJobStatus, row.status),
        progress=row.progress,
        result=cast(dict[str, object] | None, result if isinstance(result, dict) else None),
        error_code=row.last_error_code,
        created_at=row.created_at,
        started_at=row.started_at,
        completed_at=row.completed_at,
    )


class GenerationJobService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.idempotency = IdempotencyService(db)

    async def enqueue(
        self,
        context: TenantContext,
        *,
        job_type: GenerationJobType,
        effective_range: EffectiveAnalyticsRange,
        idempotency_key: str | None,
    ) -> tuple[GenerationJobView, bool]:
        key = validate_uuid_idempotency_key(idempotency_key)
        range_payload = analytics_range_payload(effective_range)
        request_hash = canonical_request_hash(
            {
                "job_type": job_type,
                "analytics_range": range_payload,
                "source_revision": context.data_revision,
            }
        )
        scope = f"{context.organization_id}:{context.user_id}"
        operation = f"enqueue_{job_type}"
        replay_body = await self.idempotency.replay_response_body(
            scope_key=scope,
            operation=operation,
            key=key,
            request_hash=request_hash,
        )
        if replay_body is not None:
            return GenerationJobView.model_validate(replay_body), True

        record = self.idempotency.start(
            scope_key=scope,
            actor_user_id=context.user_id,
            operation=operation,
            key=key,
            request_hash=request_hash,
        )
        job = BackgroundJob(
            id=uuid.uuid4(),
            organization_id=context.organization_id,
            requested_by_user_id=context.user_id,
            actor_type="demo" if context.is_demo else "user",
            job_type=job_type,
            payload={
                "analytics_range": range_payload,
                "source_revision": context.data_revision,
            },
            progress={"current": 0, "total": 1, "unit": "generation"},
            status="queued",
            idempotency_record_id=record.id,
        )
        self.db.add(job)
        try:
            await self.db.flush()
            view = generation_job_view(job)
            self.idempotency.complete(
                record,
                status_code=202,
                resource_type="background_job",
                resource_id=job.id,
                response_body=view.model_dump(mode="json"),
            )
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            replay_body = await self.idempotency.replay_response_body(
                scope_key=scope,
                operation=operation,
                key=key,
                request_hash=request_hash,
            )
            if replay_body is None:
                raise
            return GenerationJobView.model_validate(replay_body), True
        except Exception:
            await self.db.rollback()
            raise
        return view, False

    async def get(
        self,
        context: TenantContext,
        job_id: uuid.UUID,
        *,
        job_type: GenerationJobType,
    ) -> GenerationJobView:
        row = await self.db.scalar(
            select(BackgroundJob).where(
                BackgroundJob.organization_id == context.organization_id,
                BackgroundJob.id == job_id,
                BackgroundJob.job_type == job_type,
            )
        )
        if row is None:
            raise AppError(
                status=404,
                code="resource_not_found",
                title="Resource not found",
                detail="The requested resource was not found.",
            )
        return generation_job_view(row)
