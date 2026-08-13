from __future__ import annotations

import random
import uuid
from collections import Counter
from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from insightforge.analytics.calculations import comparison
from insightforge.analytics.ranges import resolve_analytics_range
from insightforge.core.concurrency import ensure_version, require_if_match, version_etag
from insightforge.core.money import decimal_to_minor, minor_to_decimal
from insightforge.core.problems import AppError
from insightforge.schemas.commerce import (
    CustomerCreateRequest,
    OrderCreateRequest,
    ProductCreateRequest,
)
from insightforge.services.auth import validate_demo_idempotency_key
from insightforge.services.commerce import ORDER_TRANSITIONS
from insightforge.services.seed import DemoSeedService


def test_money_boundary_round_trips_minor_units_exactly() -> None:
    assert decimal_to_minor(minor_to_decimal(123_456)) == 123_456


def test_etag_preconditions_are_strong_and_versioned() -> None:
    assert version_etag(7) == '"7"'
    assert require_if_match('"7"') == 7
    with pytest.raises(AppError) as missing:
        require_if_match(None)
    with pytest.raises(AppError) as stale:
        ensure_version(8, 7)
    assert missing.value.status == 428
    assert stale.value.status == 412


def test_required_commerce_strings_reject_whitespace_only_values() -> None:
    with pytest.raises(ValidationError):
        CustomerCreateRequest(name=" ")
    with pytest.raises(ValidationError):
        ProductCreateRequest(sku=" ", name="Product", category="Software", unit_price_minor=1)
    with pytest.raises(ValidationError):
        OrderCreateRequest(customer_id=uuid.uuid4(), order_number=" ", items=[])


def test_order_transition_matrix_blocks_arbitrary_jumps() -> None:
    assert "completed" not in ORDER_TRANSITIONS["pending"]
    assert "cancelled" in ORDER_TRANSITIONS["pending"]
    assert ORDER_TRANSITIONS["refunded"] == frozenset()


def test_comparison_zero_denominator_has_explicit_status() -> None:
    assert comparison(10, 0) == (None, "new")
    assert comparison(0, 0) == (None, "unchanged")
    assert comparison(None, 0) == (None, "not_comparable")


def test_custom_range_uses_half_open_tenant_boundaries_and_prior_period() -> None:
    effective = resolve_analytics_range(
        preset="custom",
        compare="previous_period",
        requested_granularity="day",
        date_from=date(2026, 3, 8),
        date_to=date(2026, 3, 10),
        time_zone="America/New_York",
        now=datetime(2026, 3, 10, tzinfo=UTC),
    )

    assert effective.current.start == datetime(2026, 3, 8, 5, tzinfo=UTC)
    assert effective.current.end == datetime(2026, 3, 10, 4, tzinfo=UTC)
    assert effective.comparison is not None
    assert effective.comparison.end == effective.current.start


def test_demo_idempotency_requires_uuid_v4_entropy() -> None:
    key = str(uuid.uuid4())
    assert validate_demo_idempotency_key(key) == key
    with pytest.raises(AppError):
        validate_demo_idempotency_key("predictable-key-123")
    with pytest.raises(AppError):
        validate_demo_idempotency_key(str(uuid.uuid1()))


def _seed_shape(organization_id: uuid.UUID):
    service = object.__new__(DemoSeedService)
    anchor = datetime(2026, 8, 10, 12, tzinfo=UTC)
    customers = service._customers(organization_id, anchor)
    products = service._products(organization_id, anchor)
    orders, _items, _events = service._orders(
        organization_id=organization_id,
        actor_user_id=uuid.uuid4(),
        anchor=anchor,
        customers=customers,
        products=products,
        rng=random.Random("insightforge-demo:v1"),  # noqa: S311
        currency="USD",
    )
    service._project_customer_metrics(customers, orders)
    return customers, orders


def test_demo_seed_is_reproducible_and_contains_business_signals() -> None:
    first_customers, first_orders = _seed_shape(uuid.uuid4())
    _second_customers, second_orders = _seed_shape(uuid.uuid4())

    assert len(first_customers) == 60
    assert len(first_orders) == len(second_orders)
    assert [order.total for order in first_orders] == [order.total for order in second_orders]
    months = Counter(order.ordered_at.month for order in first_orders)
    assert months[12] > months[5]
    assert months[11] > months[6]
    assert any(customer.segment in {"inactive", "at_risk"} for customer in first_customers)
