from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Literal, cast
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.ai import (
    INSIGHT_PROMPT_VERSION,
    OPENAI_MODEL,
    AIProviderError,
    AnalyticsSnapshot,
    AskIntent,
    AskRoutingError,
    AskRoutingErrorCode,
    CustomerAggregate,
    InsightBundle,
    InsightProvider,
    OpenAICompatibleClient,
    OpenAIProvider,
    OrderStatusAggregate,
    ProductAggregate,
    TrendAggregate,
    generate_deterministic_analysis,
    parse_ask_intent,
)
from insightforge.core.pagination import PageResult
from insightforge.core.problems import AppError
from insightforge.core.time import utc_now
from insightforge.models import AIInsight, AssistantQuery, WeeklySummary
from insightforge.repositories.intelligence import IntelligenceRepository
from insightforge.schemas.analytics import AnalyticsView, ComparisonMetricView
from insightforge.schemas.intelligence import (
    AnswerCitationView,
    AskCapabilitiesView,
    AskCapabilityView,
    AskQuestionRequest,
    AssistantAnswerView,
    InsightView,
    WeeklySummaryView,
)
from insightforge.services.idempotency import (
    IdempotencyService,
    canonical_request_hash,
    validate_uuid_idempotency_key,
)

if TYPE_CHECKING:
    from openai import AsyncOpenAI

    from insightforge.api.dependencies import TenantContext

GenerationMode = Literal["deterministic", "provider", "fallback"]
AnswerStatus = Literal["answered", "unsupported", "insufficient_data", "blocked"]

_EMAIL_PATTERN = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
_UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
)
_LONG_NUMBER_PATTERN = re.compile(r"\b\d{7,}\b")

ASK_CAPABILITIES = AskCapabilitiesView(
    capabilities=[
        AskCapabilityView(
            intent="sales_status",
            label="Sales status",
            example="How many completed orders are there?",
        ),
        AskCapabilityView(
            intent="top_product",
            label="Top product",
            example="Which product generated the most revenue?",
        ),
        AskCapabilityView(
            intent="revenue_decline",
            label="Revenue decline",
            example="Did revenue decline from the previous period?",
        ),
        AskCapabilityView(
            intent="top_customers",
            label="Top customers",
            example="Who are the top 5 customers?",
        ),
        AskCapabilityView(
            intent="business_summary",
            label="Business summary",
            example="Give me a business performance summary.",
        ),
    ]
)


@dataclass(frozen=True, slots=True)
class _GeneratedBundle:
    bundle: InsightBundle
    provider: str
    model: str | None
    prompt_version: str
    mode: GenerationMode


@dataclass(frozen=True, slots=True)
class _GroundedAnswer:
    answer: str
    status: AnswerStatus
    citations: list[AnswerCitationView]
    follow_ups: list[str]
    confidence: Decimal | None


def _integer_metric(metrics: dict[str, ComparisonMetricView], key: str) -> int:
    metric = metrics.get(key)
    if metric is None or metric.value is None:
        return 0
    value = metric.value
    if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value:
        raise ValueError(f"Canonical analytics metric {key} must be a whole number.")
    return int(value)


def _optional_integer_metric(
    metrics: dict[str, ComparisonMetricView], key: str, *, comparison: bool = False
) -> int | None:
    metric = metrics.get(key)
    if metric is None:
        return None
    value = metric.comparison_value if comparison else metric.value
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value:
        raise ValueError(f"Canonical analytics metric {key} must be a whole number.")
    return int(value)


def _optional_ratio_metric(metrics: dict[str, ComparisonMetricView], key: str) -> float | None:
    metric = metrics.get(key)
    if metric is None or metric.value is None:
        return None
    value = float(metric.value)
    return value if 0 <= value <= 1 else None


def _local_period_dates(analytics: AnalyticsView) -> tuple[date, date]:
    zone = ZoneInfo(analytics.time_zone)
    start = analytics.range.start.astimezone(zone).date()
    end = analytics.range.end.astimezone(zone).date()
    if end <= start:
        end = start + timedelta(days=1)
    return start, end


def build_analytics_snapshot(
    analytics: AnalyticsView,
    *,
    top_customers: list[CustomerAggregate] | None = None,
) -> AnalyticsSnapshot:
    """Project canonical analytics into the bounded aggregate-only provider contract."""

    period_start, period_end = _local_period_dates(analytics)
    statuses: dict[str, int] = {
        "pending": 0,
        "paid": 0,
        "processing": 0,
        "completed": 0,
        "cancelled": 0,
        "refunded": 0,
    }
    for item in analytics.order_statuses:
        if item.label in statuses:
            statuses[item.label] += item.count
    products = [
        ProductAggregate(
            rank=index,
            name=item.label,
            revenue_minor=item.revenue_minor,
            units_sold=item.units,
            revenue_share=item.share_ratio,
        )
        for index, item in enumerate(analytics.products[:10], start=1)
    ]
    trend = [
        TrendAggregate(
            period_start=item.period_start,
            revenue_minor=item.revenue_minor,
            order_count=item.order_count,
            new_customers=item.new_customers,
        )
        for item in analytics.revenue_series[-52:]
        if period_start <= item.period_start < period_end
    ]
    return AnalyticsSnapshot(
        period_start=period_start,
        period_end=period_end,
        currency=analytics.currency,
        revenue_minor=_integer_metric(analytics.metrics, "revenue_minor"),
        previous_revenue_minor=_optional_integer_metric(
            analytics.metrics, "revenue_minor", comparison=True
        ),
        order_count=_integer_metric(analytics.metrics, "order_count"),
        previous_order_count=_optional_integer_metric(
            analytics.metrics, "order_count", comparison=True
        ),
        customer_count=_integer_metric(analytics.metrics, "customers"),
        new_customer_count=_integer_metric(analytics.metrics, "new_customers"),
        average_order_value_minor=_optional_integer_metric(
            analytics.metrics, "average_order_value_minor"
        ),
        repeat_customer_rate=_optional_ratio_metric(analytics.metrics, "repeat_rate"),
        order_statuses=OrderStatusAggregate(
            pending=statuses["pending"],
            paid=statuses["paid"],
            processing=statuses["processing"],
            completed=statuses["completed"],
            cancelled=statuses["cancelled"],
            refunded=statuses["refunded"],
        ),
        top_products=products,
        top_customers=(top_customers or [])[:10],
        trend=trend,
    )


def redact_question(question: str, *, blocked: bool = False, unsupported: bool = False) -> str:
    """Retain useful intent history without persisting common direct identifiers."""

    if blocked:
        return "[Blocked question]"
    if unsupported:
        return "[Unsupported question]"
    redacted = _EMAIL_PATTERN.sub("[email]", question)
    redacted = _UUID_PATTERN.sub("[identifier]", redacted)
    redacted = _LONG_NUMBER_PATTERN.sub("[number]", redacted)
    redacted = " ".join(redacted.split())
    return redacted[:500]


def _source_revision(metrics: list[dict[str, object]]) -> int:
    for metric in metrics:
        if metric.get("key") == "_source_revision":
            value = metric.get("value")
            return int(value) if isinstance(value, int) else 0
    return 0


def _insight_view(row: AIInsight) -> InsightView:
    metrics = [
        metric for metric in row.supporting_metrics if metric.get("key") != "_source_revision"
    ]
    return InsightView(
        id=row.id,
        category=cast(
            Literal["growth", "warning", "opportunity", "performance", "anomaly"],
            row.category,
        ),
        severity=cast(Literal["info", "low", "medium", "high"], row.severity),
        title=row.title,
        description=row.description,
        supporting_metrics=metrics,
        provider=row.provider,
        model=row.model,
        prompt_version=row.prompt_version,
        generation_mode=cast(GenerationMode, row.generation_mode),
        status=cast(Literal["active", "superseded", "failed"], row.status),
        source_revision=_source_revision(row.supporting_metrics),
        period_start=row.period_start,
        period_end=row.period_end,
        generated_at=row.generated_at,
        expires_at=row.expires_at,
        superseded_at=row.superseded_at,
    )


def _summary_view(row: WeeklySummary) -> WeeklySummaryView:
    metrics = row.metrics
    highlights = metrics.get("highlights", [])
    watch_items = metrics.get("watch_items", [])
    raw_generation_mode = metrics.get("generation_mode", "deterministic")
    generation_mode: GenerationMode = (
        cast(GenerationMode, raw_generation_mode)
        if raw_generation_mode in {"deterministic", "provider", "fallback"}
        else "deterministic"
    )
    raw_source_revision = metrics.get("source_revision", 0)
    source_revision = (
        raw_source_revision
        if isinstance(raw_source_revision, int) and not isinstance(raw_source_revision, bool)
        else 0
    )
    return WeeklySummaryView(
        id=row.id,
        week_start=row.week_start,
        week_end=row.week_end,
        headline=str(metrics.get("headline", "Weekly business summary")),
        overview=row.summary,
        highlights=[str(value) for value in highlights] if isinstance(highlights, list) else [],
        watch_items=[str(value) for value in watch_items] if isinstance(watch_items, list) else [],
        provider=row.provider,
        model=row.model,
        prompt_version=str(metrics.get("prompt_version", "unknown")),
        generation_mode=generation_mode,
        source_revision=source_revision,
        generated_at=row.generated_at,
    )


def _answer_view(row: AssistantQuery) -> AssistantAnswerView:
    citations = [AnswerCitationView.model_validate(value) for value in row.supporting_metrics]
    return AssistantAnswerView(
        id=row.id,
        question_redacted=row.question_redacted,
        intent=row.intent,
        parameters=row.parameters,
        answer=row.answer,
        answer_status=cast(AnswerStatus, row.answer_status),
        applied_range=row.applied_range,
        confidence=float(row.confidence) if row.confidence is not None else None,
        follow_ups=row.follow_ups,
        citations=citations,
        provider=row.provider,
        created_at=row.created_at,
    )


class IntelligenceService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        provider: InsightProvider | None = None,
        provider_name: str = "openai",
        provider_model: str = OPENAI_MODEL,
        insight_ttl: timedelta = timedelta(days=7),
    ) -> None:
        self.db = db
        self.repository = IntelligenceRepository(db)
        self.provider = provider
        self.provider_name = provider_name
        self.provider_model = provider_model
        self.insight_ttl = insight_ttl
        self.idempotency = IdempotencyService(db)

    @classmethod
    def with_openai(
        cls,
        db: AsyncSession,
        client: AsyncOpenAI | OpenAICompatibleClient,
        *,
        timeout_seconds: float = 20.0,
        model: str = OPENAI_MODEL,
    ) -> IntelligenceService:
        return cls(
            db,
            provider=OpenAIProvider(
                client,
                timeout_seconds=timeout_seconds,
                model=model,
            ),
            provider_model=model,
        )

    async def _snapshot(
        self,
        context: TenantContext,
        analytics: AnalyticsView,
    ) -> AnalyticsSnapshot:
        customers = await self.repository.top_customers(
            context,
            start=analytics.range.start,
            end=analytics.range.end,
            limit=10,
        )
        anonymized = [
            CustomerAggregate(
                rank=index,
                revenue_minor=item.revenue_minor,
                order_count=item.order_count,
            )
            for index, item in enumerate(customers, start=1)
        ]
        return build_analytics_snapshot(analytics, top_customers=anonymized)

    async def _generate(self, snapshot: AnalyticsSnapshot) -> _GeneratedBundle:
        if self.provider is None:
            return _GeneratedBundle(
                bundle=generate_deterministic_analysis(snapshot),
                provider="deterministic",
                model=None,
                prompt_version="deterministic.v1",
                mode="deterministic",
            )
        try:
            bundle = await self.provider.generate(snapshot)
        except AIProviderError:
            return _GeneratedBundle(
                bundle=generate_deterministic_analysis(snapshot),
                provider="deterministic",
                model=None,
                prompt_version=INSIGHT_PROMPT_VERSION,
                mode="fallback",
            )
        return _GeneratedBundle(
            bundle=bundle,
            provider=self.provider_name,
            model=self.provider_model,
            prompt_version=INSIGHT_PROMPT_VERSION,
            mode="provider",
        )

    async def list_insights(
        self,
        context: TenantContext,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[InsightView]:
        result = await self.repository.list_insights(
            context, page=page, page_size=page_size, status="active"
        )
        return PageResult(
            items=[_insight_view(row) for row in result.items],
            page=page,
            page_size=page_size,
            total=result.total,
        )

    async def get_insight(
        self,
        context: TenantContext,
        insight_id: uuid.UUID,
    ) -> InsightView:
        row = await self.repository.get_insight(context, insight_id)
        if row is None:
            raise AppError(
                status=404,
                code="resource_not_found",
                title="Resource not found",
                detail="The requested resource was not found.",
            )
        return _insight_view(row)

    async def regenerate_insights(
        self,
        context: TenantContext,
        analytics: AnalyticsView,
    ) -> list[InsightView]:
        snapshot = await self._snapshot(context, analytics)
        generated = await self._generate(snapshot)
        now = utc_now()
        try:
            rows = await self.repository.replace_insights(
                organization_id=context.organization_id,
                bundle=generated.bundle,
                period_start=snapshot.period_start,
                period_end=snapshot.period_end,
                source_revision=analytics.source_revision,
                provider=generated.provider,
                model=generated.model,
                prompt_version=generated.prompt_version,
                generation_mode=generated.mode,
                generated_at=now,
                expires_at=now + self.insight_ttl,
            )
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        return [_insight_view(row) for row in rows]

    async def get_weekly_summary(
        self,
        context: TenantContext,
        week_start: date,
    ) -> WeeklySummaryView:
        row = await self.repository.get_weekly_summary(context, week_start)
        if row is None:
            raise AppError(
                status=404,
                code="resource_not_found",
                title="Weekly summary not found",
                detail="Generate the weekly business summary for this period.",
            )
        return _summary_view(row)

    async def regenerate_weekly_summary(
        self,
        context: TenantContext,
        analytics: AnalyticsView,
    ) -> WeeklySummaryView:
        snapshot = await self._snapshot(context, analytics)
        if snapshot.period_end - snapshot.period_start != timedelta(days=7):
            raise AppError(
                status=422,
                code="weekly_range_required",
                title="A weekly range is required",
                detail="Choose an exact seven-day analytics range.",
            )
        generated = await self._generate(snapshot)
        try:
            row = await self.repository.upsert_weekly_summary(
                context,
                summary=generated.bundle.weekly_summary,
                week_start=snapshot.period_start,
                week_end=snapshot.period_end,
                source_revision=analytics.source_revision,
                provider=generated.provider,
                model=generated.model,
                prompt_version=generated.prompt_version,
                generation_mode=generated.mode,
                generated_at=utc_now(),
            )
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        return _summary_view(row)

    @staticmethod
    def capabilities() -> AskCapabilitiesView:
        return ASK_CAPABILITIES

    async def ask(
        self,
        context: TenantContext,
        analytics: AnalyticsView,
        request: AskQuestionRequest,
    ) -> AssistantAnswerView:
        try:
            row = await self._create_answer(context, analytics, request)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        return _answer_view(row)

    async def ask_idempotent(
        self,
        context: TenantContext,
        analytics: AnalyticsView,
        request: AskQuestionRequest,
        *,
        idempotency_key: str | None,
    ) -> tuple[AssistantAnswerView, bool]:
        key = validate_uuid_idempotency_key(idempotency_key)
        request_hash = canonical_request_hash(
            {
                "question": request.question,
                "range_start": analytics.range.start.isoformat(),
                "range_end": analytics.range.end.isoformat(),
                "source_revision": analytics.source_revision,
            }
        )
        scope = f"{context.organization_id}:{context.user_id}"
        operation = "create_ask_answer"
        replay_body = await self.idempotency.replay_response_body(
            scope_key=scope,
            operation=operation,
            key=key,
            request_hash=request_hash,
        )
        if replay_body is not None:
            return AssistantAnswerView.model_validate(replay_body), True

        record = self.idempotency.start(
            scope_key=scope,
            actor_user_id=context.user_id,
            operation=operation,
            key=key,
            request_hash=request_hash,
        )
        try:
            row = await self._create_answer(context, analytics, request)
            view = _answer_view(row)
            self.idempotency.complete(
                record,
                status_code=201,
                resource_type="assistant_query",
                resource_id=row.id,
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
            return AssistantAnswerView.model_validate(replay_body), True
        except Exception:
            await self.db.rollback()
            raise
        return view, False

    async def _create_answer(
        self,
        context: TenantContext,
        analytics: AnalyticsView,
        request: AskQuestionRequest,
    ) -> AssistantQuery:
        applied_range: dict[str, object] = {
            "start": analytics.range.start.isoformat(),
            "end": analytics.range.end.isoformat(),
            "time_zone": analytics.time_zone,
            "source_revision": analytics.source_revision,
        }
        try:
            route = parse_ask_intent(request.question)
        except AskRoutingError as error:
            is_blocked = error.code is AskRoutingErrorCode.BLOCKED
            status: AnswerStatus = "blocked" if is_blocked else "unsupported"
            answer = (
                "This question cannot be processed because it contains disallowed instructions."
                if is_blocked
                else "This question is outside the supported analytics capabilities."
            )
            row = await self.repository.save_assistant_query(
                context,
                question_redacted=redact_question(
                    request.question,
                    blocked=is_blocked,
                    unsupported=not is_blocked,
                ),
                intent=error.code.value,
                parameters={},
                answer=answer,
                answer_status=status,
                applied_range=applied_range,
                confidence=None,
                follow_ups=["Choose one of the documented aggregate analytics questions."],
                supporting_metrics=[],
                provider="deterministic",
                created_at=utc_now(),
            )
            return row

        grounded = await self._ground_answer(context, analytics, route.intent, route.parameters)
        row = await self.repository.save_assistant_query(
            context,
            question_redacted=redact_question(request.question),
            intent=route.intent.value,
            parameters=route.parameters.model_dump(mode="json"),
            answer=grounded.answer,
            answer_status=grounded.status,
            applied_range=applied_range,
            confidence=grounded.confidence,
            follow_ups=grounded.follow_ups,
            supporting_metrics=[
                citation.model_dump(mode="json") for citation in grounded.citations
            ],
            provider="deterministic",
            created_at=utc_now(),
        )
        return row

    async def _ground_answer(
        self,
        context: TenantContext,
        analytics: AnalyticsView,
        intent: AskIntent,
        parameters: object,
    ) -> _GroundedAnswer:
        if intent is AskIntent.SALES_STATUS:
            return self._sales_status_answer(analytics, getattr(parameters, "status", None))
        if intent is AskIntent.TOP_PRODUCT:
            return self._top_product_answer(analytics, int(getattr(parameters, "limit", 1)))
        if intent is AskIntent.REVENUE_DECLINE:
            return self._revenue_decline_answer(analytics)
        if intent is AskIntent.TOP_CUSTOMERS:
            return await self._top_customers_answer(
                context, analytics, int(getattr(parameters, "limit", 5))
            )
        snapshot = build_analytics_snapshot(analytics)
        summary = generate_deterministic_analysis(snapshot).weekly_summary
        return _GroundedAnswer(
            answer=summary.overview,
            status="answered" if not snapshot.is_empty else "insufficient_data",
            citations=[
                AnswerCitationView(
                    metric="revenue_minor",
                    label="Revenue",
                    value=snapshot.revenue_minor,
                    unit="minor_currency",
                ),
                AnswerCitationView(
                    metric="order_count",
                    label="Orders",
                    value=snapshot.order_count,
                    unit="count",
                ),
            ],
            follow_ups=list(summary.watch_items),
            confidence=Decimal("1.000"),
        )

    @staticmethod
    def _sales_status_answer(
        analytics: AnalyticsView,
        requested_status: str | None,
    ) -> _GroundedAnswer:
        breakdown = {item.label: item.count for item in analytics.order_statuses}
        if requested_status is not None:
            count = breakdown.get(requested_status, 0)
            return _GroundedAnswer(
                answer=f"There were {count:,} {requested_status} orders in the selected period.",
                status="answered",
                citations=[
                    AnswerCitationView(
                        metric=f"order_status.{requested_status}",
                        label=f"{requested_status.title()} orders",
                        value=count,
                        unit="count",
                    )
                ],
                follow_ups=[],
                confidence=Decimal("1.000"),
            )
        if not breakdown:
            return _GroundedAnswer(
                answer="No order status activity is available for the selected period.",
                status="insufficient_data",
                citations=[],
                follow_ups=["Choose a period with recorded orders."],
                confidence=None,
            )
        ordered = sorted(breakdown.items(), key=lambda item: (-item[1], item[0]))
        answer = (
            "Order status totals: "
            + "; ".join(f"{status.title()} {count:,}" for status, count in ordered)
            + "."
        )
        return _GroundedAnswer(
            answer=answer,
            status="answered",
            citations=[
                AnswerCitationView(
                    metric=f"order_status.{status}",
                    label=f"{status.title()} orders",
                    value=count,
                    unit="count",
                )
                for status, count in ordered
            ],
            follow_ups=[],
            confidence=Decimal("1.000"),
        )

    @staticmethod
    def _top_product_answer(analytics: AnalyticsView, limit: int) -> _GroundedAnswer:
        products = analytics.products[:limit]
        if not products:
            return _GroundedAnswer(
                answer="No product revenue is available for the selected period.",
                status="insufficient_data",
                citations=[],
                follow_ups=["Choose a period with product sales."],
                confidence=None,
            )
        answer = (
            "Top products by revenue: "
            + "; ".join(
                f"{item.label} ({analytics.currency} {item.revenue_minor / 100:,.2f})"
                for item in products
            )
            + "."
        )
        return _GroundedAnswer(
            answer=answer,
            status="answered",
            citations=[
                AnswerCitationView(
                    metric="product_revenue_minor",
                    label=item.label,
                    value=item.revenue_minor,
                    unit="minor_currency",
                )
                for item in products
            ],
            follow_ups=[],
            confidence=Decimal("1.000"),
        )

    @staticmethod
    def _revenue_decline_answer(analytics: AnalyticsView) -> _GroundedAnswer:
        metric = analytics.metrics.get("revenue_minor")
        if metric is None or metric.value is None or metric.comparison_value is None:
            return _GroundedAnswer(
                answer="A previous-period revenue comparison is not available.",
                status="insufficient_data",
                citations=[],
                follow_ups=["Enable a previous-period comparison."],
                confidence=None,
            )
        current = int(metric.value)
        previous = int(metric.comparison_value)
        if current < previous and previous:
            ratio = (previous - current) / previous
            answer = (
                f"Revenue decreased {ratio * 100:.1f}% to {analytics.currency} "
                f"{current / 100:,.2f}. These aggregates establish the change, but not its cause."
            )
        elif current > previous:
            answer = "Revenue did not decline; it increased from the previous period."
        else:
            answer = "Revenue did not decline; it was unchanged from the previous period."
        return _GroundedAnswer(
            answer=answer,
            status="answered",
            citations=[
                AnswerCitationView(
                    metric="revenue_minor",
                    label="Current revenue",
                    value=current,
                    unit="minor_currency",
                ),
                AnswerCitationView(
                    metric="previous_revenue_minor",
                    label="Previous revenue",
                    value=previous,
                    unit="minor_currency",
                ),
            ],
            follow_ups=[],
            confidence=Decimal("1.000"),
        )

    async def _top_customers_answer(
        self,
        context: TenantContext,
        analytics: AnalyticsView,
        limit: int,
    ) -> _GroundedAnswer:
        customers = await self.repository.top_customers(
            context,
            start=analytics.range.start,
            end=analytics.range.end,
            limit=limit,
        )
        if not customers:
            return _GroundedAnswer(
                answer="No customer revenue is available for the selected period.",
                status="insufficient_data",
                citations=[],
                follow_ups=["Choose a period with customer orders."],
                confidence=None,
            )
        answer = (
            "Top customers by revenue: "
            + "; ".join(
                f"{item.name} ({analytics.currency} {item.revenue_minor / 100:,.2f})"
                for item in customers
            )
            + "."
        )
        return _GroundedAnswer(
            answer=answer,
            status="answered",
            citations=[
                AnswerCitationView(
                    metric="customer_revenue_minor",
                    label=item.name,
                    value=item.revenue_minor,
                    unit="minor_currency",
                )
                for item in customers
            ],
            follow_ups=[],
            confidence=Decimal("1.000"),
        )

    async def history(
        self,
        context: TenantContext,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[AssistantAnswerView]:
        result = await self.repository.assistant_history(context, page=page, page_size=page_size)
        return PageResult(
            items=[_answer_view(row) for row in result.items],
            page=page,
            page_size=page_size,
            total=result.total,
        )
