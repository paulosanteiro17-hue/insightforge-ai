from __future__ import annotations

from statistics import fmean

from insightforge.ai.schemas import (
    AnalyticsSnapshot,
    Insight,
    InsightBundle,
    InsightCategory,
    InsightSeverity,
    MetricKey,
    SupportingMetric,
    WeeklySummary,
)


def _change_ratio(current: int, previous: int | None) -> float | None:
    if previous is None:
        return None
    if previous == 0:
        return 0.0 if current == 0 else None
    return (current - previous) / previous


def _percent(value: float) -> str:
    return f"{abs(value) * 100:.1f}%"


def _money(value_minor: int, currency: str) -> str:
    return f"{currency} {value_minor / 100:,.2f}"


def _growth(snapshot: AnalyticsSnapshot, revenue_change: float | None) -> Insight:
    evidence = SupportingMetric(
        key=MetricKey.REVENUE,
        value=snapshot.revenue_minor,
        comparison_value=snapshot.previous_revenue_minor,
        unit="minor_currency",
    )
    if snapshot.is_empty:
        return Insight(
            category=InsightCategory.GROWTH,
            severity=InsightSeverity.INFO,
            title="Growth baseline is unavailable for this period",
            description=(
                "No recognized revenue or orders were recorded in this period. "
                "Import or create sales activity before evaluating growth."
            ),
            supporting_metrics=[evidence],
        )
    if revenue_change is None:
        title = "Revenue established a new comparison baseline"
        description = (
            f"Revenue reached {_money(snapshot.revenue_minor, snapshot.currency)}, but the prior "
            "period does not provide a non-zero baseline for a percentage comparison."
        )
        severity = InsightSeverity.INFO
    elif revenue_change >= 0.05:
        title = "Revenue growth is moving in the right direction"
        description = (
            f"Revenue increased {_percent(revenue_change)} to "
            f"{_money(snapshot.revenue_minor, snapshot.currency)} versus the prior period."
        )
        severity = InsightSeverity.LOW
    elif revenue_change <= -0.05:
        title = "Revenue growth is under pressure"
        description = (
            f"Revenue decreased {_percent(revenue_change)} to "
            f"{_money(snapshot.revenue_minor, snapshot.currency)} versus the prior period."
        )
        severity = InsightSeverity.MEDIUM
    else:
        title = "Revenue remained broadly stable"
        description = (
            f"Revenue changed {_percent(revenue_change)} and closed at "
            f"{_money(snapshot.revenue_minor, snapshot.currency)}."
        )
        severity = InsightSeverity.INFO
    return Insight(
        category=InsightCategory.GROWTH,
        severity=severity,
        title=title,
        description=description,
        supporting_metrics=[evidence],
    )


def _warning(snapshot: AnalyticsSnapshot, revenue_change: float | None) -> Insight:
    status_total = snapshot.order_statuses.total
    cancellation_rate = snapshot.order_statuses.cancelled / status_total if status_total else 0.0
    evidence = SupportingMetric(
        key=MetricKey.CANCELLATION_RATE,
        value=cancellation_rate,
        unit="ratio",
    )
    if revenue_change is not None and revenue_change <= -0.15:
        return Insight(
            category=InsightCategory.WARNING,
            severity=InsightSeverity.HIGH,
            title="The revenue decline needs attention",
            description=(
                f"Revenue fell {_percent(revenue_change)} from the prior period. "
                "Review the product mix and order pipeline before the decline persists."
            ),
            supporting_metrics=[
                SupportingMetric(
                    key=MetricKey.REVENUE,
                    value=snapshot.revenue_minor,
                    comparison_value=snapshot.previous_revenue_minor,
                    unit="minor_currency",
                )
            ],
        )
    if cancellation_rate >= 0.10:
        return Insight(
            category=InsightCategory.WARNING,
            severity=InsightSeverity.MEDIUM,
            title="Cancelled orders are elevated",
            description=(
                f"Cancelled orders represent {_percent(cancellation_rate)} of recorded orders. "
                "Review cancellation reasons and fulfillment friction."
            ),
            supporting_metrics=[evidence],
        )
    return Insight(
        category=InsightCategory.WARNING,
        severity=InsightSeverity.INFO,
        title="No material warning threshold was crossed",
        description=(
            f"The cancellation rate is {_percent(cancellation_rate)} and no severe aggregate "
            "revenue warning was detected for this period."
        ),
        supporting_metrics=[evidence],
    )


def _opportunity(snapshot: AnalyticsSnapshot) -> Insight:
    if not snapshot.top_products:
        return Insight(
            category=InsightCategory.OPPORTUNITY,
            severity=InsightSeverity.INFO,
            title="Build a product performance baseline",
            description=(
                "There is not enough ranked product revenue to identify a product-led opportunity."
            ),
            supporting_metrics=[
                SupportingMetric(key=MetricKey.ORDERS, value=snapshot.order_count, unit="count")
            ],
        )
    product = min(snapshot.top_products, key=lambda item: item.rank)
    share = product.revenue_share or 0.0
    if share >= 0.50:
        title = "Reduce dependence on the leading product"
        description = (
            f"{product.name} contributes {_percent(share)} of revenue. Use its demand signal while "
            "testing complementary offers that reduce concentration risk."
        )
        severity = InsightSeverity.MEDIUM
    else:
        title = "Expand the strongest product motion"
        product_revenue = _money(product.revenue_minor, snapshot.currency)
        description = (
            f"{product.name} is the leading product with {product_revenue} in revenue. "
            "Test targeted upsell and retention campaigns around this demand."
        )
        severity = InsightSeverity.LOW
    return Insight(
        category=InsightCategory.OPPORTUNITY,
        severity=severity,
        title=title,
        description=description,
        supporting_metrics=[
            SupportingMetric(
                key=MetricKey.TOP_PRODUCT_SHARE,
                value=share,
                unit="ratio",
            )
        ],
    )


def _performance(snapshot: AnalyticsSnapshot) -> Insight:
    average = snapshot.average_order_value_minor
    if snapshot.order_count == 0 or average is None:
        title = "Sales performance is awaiting activity"
        description = "No completed sales baseline is available for order-value analysis."
        value = 0
    else:
        title = "Average order value anchors current performance"
        description = (
            f"The business recorded {snapshot.order_count:,} orders with an average order value of "
            f"{_money(average, snapshot.currency)}."
        )
        value = average
    return Insight(
        category=InsightCategory.PERFORMANCE,
        severity=InsightSeverity.INFO,
        title=title,
        description=description,
        supporting_metrics=[
            SupportingMetric(
                key=MetricKey.AVERAGE_ORDER_VALUE,
                value=value,
                unit="minor_currency",
            ),
            SupportingMetric(key=MetricKey.ORDERS, value=snapshot.order_count, unit="count"),
        ],
    )


def _anomaly(snapshot: AnalyticsSnapshot) -> Insight:
    if len(snapshot.trend) < 3:
        deviation = 0.0
        title = "More trend history is needed"
        description = "At least three aggregate periods are needed for a stable anomaly baseline."
        severity = InsightSeverity.INFO
    else:
        baseline = fmean(point.revenue_minor for point in snapshot.trend[:-1])
        latest = snapshot.trend[-1].revenue_minor
        deviation = (
            0.0
            if baseline == 0 and latest == 0
            else (1.0 if baseline == 0 else (latest - baseline) / baseline)
        )
        if abs(deviation) >= 0.50:
            title = "Latest revenue is outside its recent pattern"
            description = (
                f"The latest aggregate revenue is {_percent(deviation)} "
                f"{'above' if deviation > 0 else 'below'} the preceding-period average."
            )
            severity = InsightSeverity.HIGH
        else:
            title = "Latest revenue remains within its recent pattern"
            description = (
                f"The latest aggregate revenue is {_percent(deviation)} from the "
                "preceding-period average, below the anomaly threshold."
            )
            severity = InsightSeverity.INFO
    return Insight(
        category=InsightCategory.ANOMALY,
        severity=severity,
        title=title,
        description=description,
        supporting_metrics=[
            SupportingMetric(
                key=MetricKey.LATEST_REVENUE_DEVIATION,
                value=deviation,
                unit="ratio",
            )
        ],
    )


def _weekly_summary(snapshot: AnalyticsSnapshot, revenue_change: float | None) -> WeeklySummary:
    if snapshot.is_empty:
        return WeeklySummary(
            headline="No sales activity was recorded",
            overview=(
                "This period has no recognized revenue or orders, so performance comparisons are "
                "not yet meaningful."
            ),
            highlights=["Revenue: no activity", "Orders: no activity"],
            watch_items=["Confirm that current sales data has been imported."],
        )
    if revenue_change is None:
        direction = "Revenue has no comparable prior baseline."
    elif revenue_change >= 0:
        direction = f"Revenue increased {_percent(revenue_change)} from the prior period."
    else:
        direction = f"Revenue decreased {_percent(revenue_change)} from the prior period."
    watch_items: list[str] = []
    if revenue_change is not None and revenue_change <= -0.10:
        watch_items.append("Investigate the drivers of the revenue decline.")
    status_total = snapshot.order_statuses.total
    if status_total and snapshot.order_statuses.cancelled / status_total >= 0.10:
        watch_items.append("Review the elevated cancellation rate.")
    return WeeklySummary(
        headline="Business performance at a glance",
        overview=(
            f"{direction} The period produced {_money(snapshot.revenue_minor, snapshot.currency)} "
            f"across {snapshot.order_count:,} orders."
        ),
        highlights=[
            f"Revenue: {_money(snapshot.revenue_minor, snapshot.currency)}",
            f"Orders: {snapshot.order_count:,}",
            f"New customers: {snapshot.new_customer_count:,}",
        ],
        watch_items=watch_items,
    )


def generate_deterministic_analysis(snapshot: AnalyticsSnapshot) -> InsightBundle:
    """Generate a stable five-category analysis using only supplied aggregates."""

    revenue_change = _change_ratio(snapshot.revenue_minor, snapshot.previous_revenue_minor)
    return InsightBundle(
        insights=[
            _growth(snapshot, revenue_change),
            _warning(snapshot, revenue_change),
            _opportunity(snapshot),
            _performance(snapshot),
            _anomaly(snapshot),
        ],
        weekly_summary=_weekly_summary(snapshot, revenue_change),
    )
