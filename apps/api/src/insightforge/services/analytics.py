from __future__ import annotations

from datetime import time, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from insightforge.analytics.calculations import bucket_dates, comparison
from insightforge.analytics.ranges import EffectiveAnalyticsRange
from insightforge.core.money import decimal_to_minor
from insightforge.core.problems import AppError
from insightforge.core.time import utc_now
from insightforge.repositories.analytics import (
    AcquisitionAggregate,
    AnalyticsRepository,
    PeriodSummary,
    RankedAggregate,
    SeriesAggregate,
)
from insightforge.schemas.analytics import (
    AnalyticsFilterOptionsView,
    AnalyticsRangeView,
    AnalyticsView,
    BreakdownView,
    ComparisonMetricView,
    RecentTransactionView,
    TimeSeriesPointView,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from insightforge.api.dependencies import TenantContext


def _metric(
    current: int | float | None,
    previous: int | float | None,
) -> ComparisonMetricView:
    ratio, status = comparison(current, previous)
    return ComparisonMetricView(
        value=current,
        comparison_value=previous,
        change_ratio=ratio,
        change_status=status,
    )


def _average_minor(summary: PeriodSummary | None) -> int | None:
    if summary is None or summary.order_count == 0:
        return None
    return round(decimal_to_minor(summary.revenue) / summary.order_count)


def _repeat_rate(summary: PeriodSummary | None) -> float | None:
    if summary is None or summary.customers == 0:
        return None
    return summary.repeat_customers / summary.customers


def _range_view(effective_range: EffectiveAnalyticsRange) -> AnalyticsRangeView:
    return AnalyticsRangeView(
        start=effective_range.current.start,
        end=effective_range.current.end,
    )


def _comparison_range_view(
    effective_range: EffectiveAnalyticsRange,
) -> AnalyticsRangeView | None:
    if effective_range.comparison is None:
        return None
    return AnalyticsRangeView(
        start=effective_range.comparison.start,
        end=effective_range.comparison.end,
    )


def _filled_series(
    *,
    effective_range: EffectiveAnalyticsRange,
    revenue: list[SeriesAggregate],
    acquisition: list[AcquisitionAggregate],
) -> list[TimeSeriesPointView]:
    zone = ZoneInfo(effective_range.time_zone)
    local_start = effective_range.current.start.astimezone(zone).date()
    local_end_instant = effective_range.current.end.astimezone(zone)
    local_end = local_end_instant.date()
    if local_end_instant.time() != time.min:
        local_end += timedelta(days=1)
    revenue_map = {row.period_start: row for row in revenue}
    acquisition_map = {row.period_start: row for row in acquisition}
    return [
        TimeSeriesPointView(
            period_start=period,
            revenue_minor=decimal_to_minor(
                revenue_map.get(period, SeriesAggregate(period, Decimal("0.00"), 0)).revenue
            ),
            order_count=revenue_map.get(
                period,
                SeriesAggregate(period, Decimal("0.00"), 0),
            ).order_count,
            new_customers=acquisition_map.get(
                period,
                AcquisitionAggregate(period, 0),
            ).new_customers,
        )
        for period in bucket_dates(local_start, local_end, effective_range.granularity)
    ]


def _breakdowns(
    rows: list[RankedAggregate],
    *,
    total_revenue_minor: int,
    total_count: int = 0,
) -> list[BreakdownView]:
    result: list[BreakdownView] = []
    for row in rows:
        revenue_minor = decimal_to_minor(row.revenue)
        denominator = total_revenue_minor if revenue_minor else total_count
        numerator = revenue_minor if revenue_minor else row.count
        result.append(
            BreakdownView(
                id=row.id,
                label=row.label,
                revenue_minor=revenue_minor,
                units=row.units,
                count=row.count,
                share_ratio=numerator / denominator if denominator else None,
            )
        )
    return result


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.repository = AnalyticsRepository(db)

    async def snapshot(
        self,
        context: TenantContext,
        effective_range: EffectiveAnalyticsRange,
    ) -> AnalyticsView:
        current = effective_range.current
        comparison_range = effective_range.comparison
        currencies = await self.repository.currencies(
            context.organization.id,
            start=current.start,
            end=current.end,
        )
        if comparison_range is not None:
            currencies |= await self.repository.currencies(
                context.organization.id,
                start=comparison_range.start,
                end=comparison_range.end,
            )
        expected_currency = context.organization.reporting_currency
        if currencies - {expected_currency}:
            raise AppError(
                status=422,
                code="mixed_currency_not_supported",
                title="Mixed currencies are not supported",
                detail="This range contains orders outside the reporting currency.",
            )
        current_summary = await self.repository.summary(
            context.organization.id,
            start=current.start,
            end=current.end,
        )
        previous_summary = (
            await self.repository.summary(
                context.organization.id,
                start=comparison_range.start,
                end=comparison_range.end,
            )
            if comparison_range is not None
            else None
        )
        revenue_series = await self.repository.revenue_series(
            context.organization.id,
            start=current.start,
            end=current.end,
            time_zone=effective_range.time_zone,
            granularity=effective_range.granularity,
        )
        acquisition = await self.repository.acquisition_series(
            context.organization.id,
            start=current.start,
            end=current.end,
            time_zone=effective_range.time_zone,
            granularity=effective_range.granularity,
        )
        product_rows = await self.repository.products(
            context.organization.id,
            start=current.start,
            end=current.end,
        )
        category_rows = await self.repository.categories(
            context.organization.id,
            start=current.start,
            end=current.end,
        )
        status_rows = await self.repository.order_statuses(
            context.organization.id,
            start=current.start,
            end=current.end,
        )
        recent_rows = await self.repository.recent_orders(
            context.organization.id,
            start=current.start,
            end=current.end,
        )
        previous_revenue = decimal_to_minor(previous_summary.revenue) if previous_summary else None
        current_revenue = decimal_to_minor(current_summary.revenue)
        series = _filled_series(
            effective_range=effective_range,
            revenue=revenue_series,
            acquisition=acquisition,
        )
        status_total = sum(row.count for row in status_rows)
        previous_orders = previous_summary.order_count if previous_summary else None
        previous_customers = previous_summary.customers if previous_summary else None
        previous_new_customers = previous_summary.new_customers if previous_summary else None
        return AnalyticsView(
            range=_range_view(effective_range),
            comparison_range=_comparison_range_view(effective_range),
            granularity=effective_range.granularity,
            time_zone=effective_range.time_zone,
            currency=expected_currency,
            source_revision=context.organization.data_revision,
            generated_at=utc_now(),
            data_availability="available" if status_total else "empty",
            metrics={
                "revenue_minor": _metric(current_revenue, previous_revenue),
                "order_count": _metric(current_summary.order_count, previous_orders),
                "customers": _metric(current_summary.customers, previous_customers),
                "new_customers": _metric(
                    current_summary.new_customers,
                    previous_new_customers,
                ),
                "average_order_value_minor": _metric(
                    _average_minor(current_summary),
                    _average_minor(previous_summary),
                ),
                "repeat_rate": _metric(
                    _repeat_rate(current_summary),
                    _repeat_rate(previous_summary),
                ),
            },
            revenue_series=series,
            order_series=series,
            customer_acquisition=series,
            products=_breakdowns(product_rows, total_revenue_minor=current_revenue),
            categories=_breakdowns(category_rows, total_revenue_minor=current_revenue),
            order_statuses=_breakdowns(
                status_rows,
                total_revenue_minor=0,
                total_count=status_total,
            ),
            recent_transactions=[
                RecentTransactionView(
                    id=row.order.id,
                    order_number=row.order.order_number,
                    customer_name=row.customer_name,
                    status=row.order.status,
                    total_minor=decimal_to_minor(row.order.total),
                    currency=row.order.currency,
                    ordered_at=row.order.ordered_at,
                )
                for row in recent_rows
            ],
        )

    async def filter_options(
        self,
        context: TenantContext,
        effective_range: EffectiveAnalyticsRange,
    ) -> AnalyticsFilterOptionsView:
        categories, statuses, sources = await self.repository.filter_options(
            context.organization.id
        )
        return AnalyticsFilterOptionsView(
            range=_range_view(effective_range),
            comparison_range=_comparison_range_view(effective_range),
            granularity=effective_range.granularity,
            time_zone=effective_range.time_zone,
            currency=context.organization.reporting_currency,
            source_revision=context.organization.data_revision,
            generated_at=utc_now(),
            categories=categories,
            order_statuses=statuses,
            sources=sources,
        )
