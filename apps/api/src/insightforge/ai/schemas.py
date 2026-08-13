from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from insightforge.core.money import MAX_MONEY_MINOR

MoneyMinor = Annotated[int, Field(ge=0, le=MAX_MONEY_MINOR)]
Count = Annotated[int, Field(ge=0, le=2_147_483_647)]
Ratio = Annotated[float, Field(ge=0, le=1)]
ShortText = Annotated[str, Field(min_length=1, max_length=160)]
NarrativeText = Annotated[str, Field(min_length=1, max_length=600)]


class StrictAIModel(BaseModel):
    """Strict, immutable contracts used at the AI trust boundary."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )


class OrderStatusAggregate(StrictAIModel):
    pending: Count = 0
    paid: Count = 0
    processing: Count = 0
    completed: Count = 0
    cancelled: Count = 0
    refunded: Count = 0

    @property
    def total(self) -> int:
        return (
            self.pending
            + self.paid
            + self.processing
            + self.completed
            + self.cancelled
            + self.refunded
        )


class ProductAggregate(StrictAIModel):
    """A ranked product aggregate without database identifiers."""

    rank: Annotated[int, Field(ge=1, le=10)]
    name: ShortText
    revenue_minor: MoneyMinor
    units_sold: Count
    revenue_share: Ratio | None = None


class CustomerAggregate(StrictAIModel):
    """An anonymized customer rank; names, emails, and IDs are intentionally absent."""

    rank: Annotated[int, Field(ge=1, le=10)]
    revenue_minor: MoneyMinor
    order_count: Count


class TrendAggregate(StrictAIModel):
    period_start: date
    revenue_minor: MoneyMinor
    order_count: Count
    new_customers: Count


class AnalyticsSnapshot(StrictAIModel):
    """Bounded aggregate-only input safe to pass across an AI provider boundary."""

    schema_version: Literal["analytics_snapshot.v1"] = "analytics_snapshot.v1"
    period_start: date
    period_end: date
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    revenue_minor: MoneyMinor
    previous_revenue_minor: MoneyMinor | None = None
    order_count: Count
    previous_order_count: Count | None = None
    customer_count: Count
    new_customer_count: Count
    average_order_value_minor: MoneyMinor | None = None
    repeat_customer_rate: Ratio | None = None
    order_statuses: OrderStatusAggregate = Field(default_factory=OrderStatusAggregate)
    top_products: Annotated[list[ProductAggregate], Field(max_length=10)] = Field(
        default_factory=list
    )
    top_customers: Annotated[list[CustomerAggregate], Field(max_length=10)] = Field(
        default_factory=list
    )
    trend: Annotated[list[TrendAggregate], Field(max_length=52)] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_aggregate_shape(self) -> Self:
        if self.period_start >= self.period_end:
            raise ValueError("period_start must be earlier than period_end.")
        product_ranks = [item.rank for item in self.top_products]
        if len(product_ranks) != len(set(product_ranks)):
            raise ValueError("Product aggregate ranks must be unique.")
        customer_ranks = [item.rank for item in self.top_customers]
        if len(customer_ranks) != len(set(customer_ranks)):
            raise ValueError("Customer aggregate ranks must be unique.")
        trend_dates = [item.period_start for item in self.trend]
        if trend_dates != sorted(trend_dates) or len(trend_dates) != len(set(trend_dates)):
            raise ValueError("Trend periods must be unique and sorted in ascending order.")
        if any(period < self.period_start or period >= self.period_end for period in trend_dates):
            raise ValueError("Trend periods must fall within the snapshot range.")
        return self

    @property
    def is_empty(self) -> bool:
        return self.order_count == 0 and self.revenue_minor == 0


class InsightCategory(StrEnum):
    GROWTH = "growth"
    WARNING = "warning"
    OPPORTUNITY = "opportunity"
    PERFORMANCE = "performance"
    ANOMALY = "anomaly"


class InsightSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MetricKey(StrEnum):
    REVENUE = "revenue_minor"
    ORDERS = "order_count"
    NEW_CUSTOMERS = "new_customer_count"
    AVERAGE_ORDER_VALUE = "average_order_value_minor"
    REPEAT_CUSTOMER_RATE = "repeat_customer_rate"
    CANCELLATION_RATE = "cancellation_rate"
    TOP_PRODUCT_SHARE = "top_product_revenue_share"
    LATEST_REVENUE_DEVIATION = "latest_revenue_deviation"


class SupportingMetric(StrictAIModel):
    key: MetricKey
    value: int | float
    comparison_value: int | float | None = None
    unit: Literal["minor_currency", "count", "ratio"]


class Insight(StrictAIModel):
    category: InsightCategory
    severity: InsightSeverity
    title: ShortText
    description: NarrativeText
    supporting_metrics: Annotated[list[SupportingMetric], Field(min_length=1, max_length=4)]


class WeeklySummary(StrictAIModel):
    headline: ShortText
    overview: NarrativeText
    highlights: Annotated[list[ShortText], Field(min_length=1, max_length=5)]
    watch_items: Annotated[list[ShortText], Field(max_length=3)] = Field(default_factory=list)


class InsightBundle(StrictAIModel):
    insights: Annotated[list[Insight], Field(min_length=5, max_length=5)]
    weekly_summary: WeeklySummary

    @model_validator(mode="after")
    def require_each_category_once(self) -> Self:
        categories = [insight.category for insight in self.insights]
        if len(categories) != len(set(categories)) or set(categories) != set(InsightCategory):
            raise ValueError("The bundle must contain every insight category exactly once.")
        return self
