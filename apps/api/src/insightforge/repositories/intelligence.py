from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.ai.schemas import InsightBundle
from insightforge.ai.schemas import WeeklySummary as GeneratedWeeklySummary
from insightforge.core.pagination import PageResult
from insightforge.models import (
    AIInsight,
    AssistantQuery,
    Customer,
    Order,
    Organization,
    WeeklySummary,
)
from insightforge.repositories.commerce import REVENUE_STATUSES

if TYPE_CHECKING:
    from insightforge.api.dependencies import TenantContext


@dataclass(frozen=True, slots=True)
class RankedCustomerResult:
    name: str
    revenue_minor: int
    order_count: int


class IntelligenceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _lock_organization(self, organization_id: uuid.UUID) -> None:
        await self.db.scalar(
            select(Organization.id).where(Organization.id == organization_id).with_for_update()
        )

    async def list_insights(
        self,
        context: TenantContext,
        *,
        page: int,
        page_size: int,
        status: str = "active",
    ) -> PageResult[AIInsight]:
        filters = (
            AIInsight.organization_id == context.organization_id,
            AIInsight.status == status,
        )
        total = int(await self.db.scalar(select(func.count(AIInsight.id)).where(*filters)) or 0)
        items = list(
            (
                await self.db.scalars(
                    select(AIInsight)
                    .where(*filters)
                    .order_by(AIInsight.generated_at.desc(), AIInsight.category.asc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return PageResult(items=items, page=page, page_size=page_size, total=total)

    async def get_insight(
        self,
        context: TenantContext,
        insight_id: uuid.UUID,
    ) -> AIInsight | None:
        return cast(
            AIInsight | None,
            await self.db.scalar(
                select(AIInsight).where(
                    AIInsight.organization_id == context.organization_id,
                    AIInsight.id == insight_id,
                )
            ),
        )

    async def replace_insights(
        self,
        *,
        organization_id: uuid.UUID,
        bundle: InsightBundle,
        period_start: date,
        period_end: date,
        source_revision: int,
        provider: str,
        model: str | None,
        prompt_version: str,
        generation_mode: str,
        generated_at: datetime,
        expires_at: datetime,
    ) -> list[AIInsight]:
        await self._lock_organization(organization_id)
        await self.db.execute(
            update(AIInsight)
            .where(
                AIInsight.organization_id == organization_id,
                AIInsight.period_start == period_start,
                AIInsight.period_end == period_end,
                AIInsight.status == "active",
            )
            .values(status="superseded", superseded_at=generated_at)
        )
        rows: list[AIInsight] = []
        for insight in bundle.insights:
            supporting_metrics = [
                metric.model_dump(mode="json") for metric in insight.supporting_metrics
            ]
            supporting_metrics.append(
                {
                    "key": "_source_revision",
                    "value": source_revision,
                    "unit": "revision",
                }
            )
            rows.append(
                AIInsight(
                    id=uuid.uuid4(),
                    organization_id=organization_id,
                    title=insight.title,
                    description=insight.description,
                    category=insight.category.value,
                    severity=insight.severity.value,
                    supporting_metrics=supporting_metrics,
                    provider=provider,
                    model=model,
                    prompt_version=prompt_version,
                    generation_mode=generation_mode,
                    status="active",
                    period_start=period_start,
                    period_end=period_end,
                    generated_at=generated_at,
                    expires_at=expires_at,
                )
            )
        self.db.add_all(rows)
        await self.db.flush()
        return rows

    async def get_weekly_summary(
        self,
        context: TenantContext,
        week_start: date,
        *,
        for_update: bool = False,
    ) -> WeeklySummary | None:
        statement = select(WeeklySummary).where(
            WeeklySummary.organization_id == context.organization_id,
            WeeklySummary.week_start == week_start,
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(WeeklySummary | None, await self.db.scalar(statement))

    async def upsert_weekly_summary(
        self,
        context: TenantContext,
        *,
        summary: GeneratedWeeklySummary,
        week_start: date,
        week_end: date,
        source_revision: int,
        provider: str,
        model: str | None,
        prompt_version: str,
        generation_mode: str,
        generated_at: datetime,
    ) -> WeeklySummary:
        await self._lock_organization(context.organization_id)
        row = await self.get_weekly_summary(context, week_start, for_update=True)
        metrics: dict[str, object] = {
            "source_revision": source_revision,
            "prompt_version": prompt_version,
            "generation_mode": generation_mode,
            "headline": summary.headline,
            "highlights": list(summary.highlights),
            "watch_items": list(summary.watch_items),
        }
        if row is None:
            row = WeeklySummary(
                id=uuid.uuid4(),
                organization_id=context.organization_id,
                week_start=week_start,
                week_end=week_end,
                metrics=metrics,
                summary=summary.overview,
                provider=provider,
                model=model,
                generated_by_user_id=context.user_id,
                generated_at=generated_at,
            )
            self.db.add(row)
        else:
            row.week_end = week_end
            row.metrics = metrics
            row.summary = summary.overview
            row.provider = provider
            row.model = model
            row.generated_by_user_id = context.user_id
            row.generated_at = generated_at
        await self.db.flush()
        return row

    async def top_customers(
        self,
        context: TenantContext,
        *,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list[RankedCustomerResult]:
        rows = (
            await self.db.execute(
                select(
                    Customer.name,
                    func.coalesce(func.sum(Order.total), Decimal("0.00")),
                    func.count(Order.id),
                    Customer.id,
                )
                .join(
                    Order,
                    (Order.organization_id == Customer.organization_id)
                    & (Order.customer_id == Customer.id),
                )
                .where(
                    Customer.organization_id == context.organization_id,
                    Order.status.in_(REVENUE_STATUSES),
                    Order.ordered_at >= start,
                    Order.ordered_at < end,
                )
                .group_by(Customer.id, Customer.name)
                .order_by(func.sum(Order.total).desc(), Customer.id.asc())
                .limit(limit)
            )
        ).all()
        return [
            RankedCustomerResult(
                name=str(row[0]),
                revenue_minor=int(Decimal(row[1]) * 100),
                order_count=int(row[2]),
            )
            for row in rows
        ]

    async def save_assistant_query(
        self,
        context: TenantContext,
        *,
        question_redacted: str,
        intent: str,
        parameters: dict[str, object],
        answer: str,
        answer_status: str,
        applied_range: dict[str, object],
        confidence: Decimal | None,
        follow_ups: list[str],
        supporting_metrics: list[dict[str, object]],
        provider: str,
        created_at: datetime,
    ) -> AssistantQuery:
        row = AssistantQuery(
            id=uuid.uuid4(),
            organization_id=context.organization_id,
            user_id=context.user_id,
            question_redacted=question_redacted,
            intent=intent,
            parameters=parameters,
            answer=answer,
            answer_status=answer_status,
            applied_range=applied_range,
            confidence=confidence,
            follow_ups=follow_ups,
            supporting_metrics=supporting_metrics,
            provider=provider,
            created_at=created_at,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def assistant_history(
        self,
        context: TenantContext,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[AssistantQuery]:
        filters = (
            AssistantQuery.organization_id == context.organization_id,
            AssistantQuery.user_id == context.user_id,
        )
        total = int(
            await self.db.scalar(select(func.count(AssistantQuery.id)).where(*filters)) or 0
        )
        items = list(
            (
                await self.db.scalars(
                    select(AssistantQuery)
                    .where(*filters)
                    .order_by(AssistantQuery.created_at.desc(), AssistantQuery.id.asc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return PageResult(items=items, page=page, page_size=page_size, total=total)
