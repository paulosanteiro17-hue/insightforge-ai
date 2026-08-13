from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from insightforge.ai import (
    INSIGHT_PROMPT_VERSION,
    AIProviderError,
    AnalyticsSnapshot,
    CustomerAggregate,
    ProviderErrorCode,
)
from insightforge.schemas.analytics import (
    AnalyticsRangeView,
    AnalyticsView,
    BreakdownView,
    ComparisonMetricView,
    RecentTransactionView,
    TimeSeriesPointView,
)
from insightforge.schemas.reports import ReportFilters
from insightforge.services.intelligence import (
    IntelligenceService,
    build_analytics_snapshot,
    redact_question,
)
from insightforge.services.reports import (
    ReportService,
    build_report_rows,
    formula_safe_csv_cell,
    serialize_report_rows,
)


def _metric(
    value: int | float | None,
    comparison_value: int | float | None = None,
) -> ComparisonMetricView:
    return ComparisonMetricView(
        value=value,
        comparison_value=comparison_value,
        change_ratio=None,
        change_status="not_comparable",
    )


def _analytics(*, product_name: str = "Analytics Pro") -> AnalyticsView:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end = datetime(2026, 8, 1, tzinfo=UTC)
    points = [
        TimeSeriesPointView(
            period_start=start.date() + timedelta(days=index),
            revenue_minor=10_000 + index,
            order_count=2,
            new_customers=1,
        )
        for index in range(60)
    ]
    products = [
        BreakdownView(
            id=uuid.uuid4(),
            label=product_name if index < 2 else f"Product {index + 1}",
            revenue_minor=120_000 - index * 1_000,
            units=20 - index,
            share_ratio=0.1,
        )
        for index in range(12)
    ]
    return AnalyticsView(
        range=AnalyticsRangeView(start=start, end=end),
        comparison_range=AnalyticsRangeView(
            start=start - (end - start),
            end=start,
        ),
        granularity="day",
        time_zone="UTC",
        currency="USD",
        source_revision=42,
        generated_at=end,
        data_availability="available",
        metrics={
            "revenue_minor": _metric(600_000, 500_000),
            "order_count": _metric(10, 9),
            "customers": _metric(8, 7),
            "new_customers": _metric(3, 2),
            "average_order_value_minor": _metric(60_000, 55_556),
            "repeat_rate": _metric(0.25, 0.2),
        },
        revenue_series=points,
        order_series=points,
        customer_acquisition=points,
        products=products,
        categories=[],
        order_statuses=[
            BreakdownView(id=uuid.uuid4(), label="completed", count=10),
            BreakdownView(id=uuid.uuid4(), label="cancelled", count=2),
            BreakdownView(id=uuid.uuid4(), label="pending", count=18),
        ],
        recent_transactions=[
            RecentTransactionView(
                id=uuid.uuid4(),
                order_number="PRIVATE-ORDER-001",
                customer_name="private-person@example.com",
                status="completed",
                total_minor=10_000,
                currency="USD",
                ordered_at=end - timedelta(days=1),
            )
        ],
    )


def test_snapshot_projection_is_bounded_aggregate_only_and_drops_identifiers() -> None:
    analytics = _analytics()
    customer_aggregates = [
        CustomerAggregate(rank=index, revenue_minor=10_000, order_count=1) for index in range(1, 11)
    ]

    snapshot = build_analytics_snapshot(
        analytics,
        top_customers=customer_aggregates,
    )
    serialized = snapshot.model_dump_json()

    assert snapshot.order_count == 10
    assert snapshot.order_statuses.total == 30
    assert len(snapshot.top_products) == 10
    assert len(snapshot.top_customers) == 10
    assert len(snapshot.trend) == 52
    assert snapshot.top_products[0].name == snapshot.top_products[1].name
    assert "PRIVATE-ORDER-001" not in serialized
    assert "private-person@example.com" not in serialized
    assert all(str(item.id) not in serialized for item in analytics.products)


def test_question_history_redaction_removes_common_direct_identifiers() -> None:
    question = (
        "Show customer 123456789 for analyst@example.com with id "
        "c73f30c7-f03d-4e23-8c94-7ce294465566"
    )

    assert redact_question(question) == ("Show customer [number] for [email] with id [identifier]")
    assert redact_question(question, blocked=True) == "[Blocked question]"
    assert redact_question(question, unsupported=True) == "[Unsupported question]"


class _FailingProvider:
    async def generate(self, _snapshot: AnalyticsSnapshot):
        raise AIProviderError(
            ProviderErrorCode.UNAVAILABLE,
            "The AI provider is temporarily unavailable.",
            retryable=True,
        )


@pytest.mark.asyncio
async def test_provider_failure_uses_deterministic_fallback_metadata() -> None:
    service = IntelligenceService(object(), provider=_FailingProvider())  # type: ignore[arg-type]

    generated = await service._generate(build_analytics_snapshot(_analytics()))

    assert generated.mode == "fallback"
    assert generated.provider == "deterministic"
    assert generated.model is None
    assert generated.prompt_version == INSIGHT_PROMPT_VERSION
    assert len(generated.bundle.insights) == 5


def test_ask_capabilities_are_allowlisted_and_document_the_safety_boundary() -> None:
    capabilities = IntelligenceService.capabilities()

    assert {item.intent for item in capabilities.capabilities} == {
        "sales_status",
        "top_product",
        "revenue_decline",
        "top_customers",
        "business_summary",
    }
    assert "Arbitrary database queries" in capabilities.safety_note


def test_report_filters_only_accept_enforced_canonical_dimensions() -> None:
    filters = ReportFilters(
        date_from=datetime(2026, 7, 1, tzinfo=UTC),
        date_to=datetime(2026, 8, 1, tzinfo=UTC),
        granularity="day",
    )

    assert filters.granularity == "day"
    with pytest.raises(ValidationError, match="statuses"):
        ReportFilters.model_validate(
            {
                **filters.model_dump(),
                "statuses": ["completed"],
            }
        )
    with pytest.raises(ValidationError, match="UTC offset"):
        ReportFilters(
            date_from=datetime(2026, 7, 1),
            date_to=datetime(2026, 8, 1),
        )
    with pytest.raises(ValidationError, match="earlier"):
        ReportFilters(
            date_from=datetime(2026, 8, 1, tzinfo=UTC),
            date_to=datetime(2026, 7, 1, tzinfo=UTC),
        )


def test_all_report_templates_build_only_canonical_aggregate_rows() -> None:
    analytics = _analytics()
    templates = ReportService.templates()

    assert {template.report_type for template in templates} == {
        "monthly_performance",
        "sales",
        "customer",
        "product_performance",
    }
    assert len(build_report_rows("monthly_performance", analytics).rows) == 6
    assert len(build_report_rows("sales", analytics).rows) == 60
    assert len(build_report_rows("customer", analytics).rows) == 60
    product_rows = build_report_rows("product_performance", analytics)
    assert len(product_rows.rows) == 12
    assert all("id" not in row for row in product_rows.rows)


def test_report_serializers_create_stable_json_and_formula_safe_csv() -> None:
    analytics = _analytics(product_name=' =HYPERLINK("https://invalid.example")')
    filters = ReportFilters(
        date_from=analytics.range.start,
        date_to=analytics.range.end,
        granularity=analytics.granularity,
    )
    rows = build_report_rows("product_performance", analytics)

    json_payload, json_type = serialize_report_rows(
        report_format="json",
        report_type="product_performance",
        report_name="Product Performance Report",
        filters=filters,
        source_revision=analytics.source_revision,
        report_rows=rows,
    )
    csv_payload, csv_type = serialize_report_rows(
        report_format="csv",
        report_type="product_performance",
        report_name="Product Performance Report",
        filters=filters,
        source_revision=analytics.source_revision,
        report_rows=rows,
    )

    document = json.loads(json_payload)
    parsed_csv = list(csv.reader(io.StringIO(csv_payload.decode("utf-8"))))
    assert json_type == "application/json"
    assert document["source_revision"] == 42
    assert document["rows"][0]["product"].startswith(" =HYPERLINK")
    assert csv_type == "text/csv; charset=utf-8"
    assert parsed_csv[1][1].startswith("' =HYPERLINK")
    assert formula_safe_csv_cell("+SUM(A1:A2)") == "'+SUM(A1:A2)"
    assert formula_safe_csv_cell("Ordinary text") == "Ordinary text"
