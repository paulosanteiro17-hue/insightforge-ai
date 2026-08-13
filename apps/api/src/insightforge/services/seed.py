from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.models import Customer, Order, OrderItem, OrderStatusEvent, Product

ELIGIBLE_REVENUE_STATUSES = frozenset({"paid", "processing", "completed"})

FIRST_NAMES = (
    "Avery",
    "Jordan",
    "Morgan",
    "Taylor",
    "Riley",
    "Cameron",
    "Parker",
    "Casey",
    "Quinn",
    "Reese",
)
LAST_NAMES = ("Morgan", "Brooks", "Patel", "Chen", "Rivera", "Foster")
COMPANY_PREFIXES = (
    "Blue Oak",
    "Northline",
    "Bright Harbor",
    "Cedar & Co.",
    "Atlas Ridge",
    "Juniper",
)
COMPANY_SUFFIXES = ("Studio", "Labs", "Partners", "Collective", "Works")
PRODUCT_CATALOG = (
    ("NS-CRM-ANNUAL", "CRM Annual Plan", "Software", 154_000),
    ("NS-CRM-MONTHLY", "CRM Monthly Plan", "Software", 14_900),
    ("NS-ANALYTICS", "Analytics Add-on", "Software", 49_900),
    ("NS-AUTOMATION", "Workflow Automation", "Software", 39_900),
    ("NS-ONBOARD", "Guided Onboarding", "Services", 85_000),
    ("NS-TRAINING", "Team Training", "Services", 45_000),
    ("NS-SUPPORT", "Priority Support", "Support", 24_900),
    ("NS-AUDIT", "Data Quality Audit", "Services", 67_500),
    ("NS-SEATS-10", "Ten-seat Expansion", "Licenses", 29_900),
    ("NS-SEATS-25", "Twenty-five-seat Expansion", "Licenses", 64_900),
    ("NS-CONNECT", "Integration Bundle", "Integrations", 32_500),
    ("NS-EXPORT", "Advanced Export Pack", "Software", 12_500),
)
PRODUCT_WEIGHTS = (35.0, 22.0, 12.0, 8.0, 7.0, 5.0, 4.0, 3.0, 2.0, 1.5, 1.0, 0.5)
STATUS_POPULATION = (
    "completed",
    "completed",
    "completed",
    "completed",
    "completed",
    "completed",
    "completed",
    "processing",
    "paid",
    "pending",
    "cancelled",
    "refunded",
)


@dataclass(frozen=True, slots=True)
class SeedSummary:
    customers: int
    products: int
    orders: int


def _money(minor: int) -> Decimal:
    return (Decimal(minor) / Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _stable_id(namespace: uuid.UUID, kind: str, index: int) -> uuid.UUID:
    return uuid.uuid5(namespace, f"insightforge-demo:{kind}:{index}")


def _month_start(value: datetime, offset: int) -> datetime:
    ordinal = value.year * 12 + value.month - 1 + offset
    year, zero_based_month = divmod(ordinal, 12)
    return datetime(year, zero_based_month + 1, 1, tzinfo=UTC)


def _random_instant(rng: random.Random, start: datetime, end: datetime) -> datetime:
    seconds = max(1, int((end - start).total_seconds()))
    return start + timedelta(seconds=rng.randrange(seconds))


class DemoSeedService:
    """Build a repeatable demo commerce history without touching global random state."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def seed(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        anchor: datetime,
        currency: str = "USD",
    ) -> SeedSummary:
        existing = await self.db.scalar(
            select(Customer.id).where(
                Customer.organization_id == organization_id,
                Customer.external_id == "DEMO-CUSTOMER-001",
            )
        )
        if existing is not None:
            return SeedSummary(customers=0, products=0, orders=0)

        # V1 keeps totals and distributions identical across demo workspaces while
        # shifting the visible history to the current UTC day.
        normalized_anchor = anchor.astimezone(UTC).replace(
            hour=12,
            minute=0,
            second=0,
            microsecond=0,
        )
        rng = random.Random("insightforge-demo:v1")  # noqa: S311
        customers = self._customers(organization_id, normalized_anchor)
        products = self._products(organization_id, normalized_anchor)
        self.db.add_all([*customers, *products])
        await self.db.flush()

        orders, items, events = self._orders(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            anchor=normalized_anchor,
            customers=customers,
            products=products,
            rng=rng,
            currency=currency,
        )
        self.db.add_all(orders)
        await self.db.flush()
        self.db.add_all([*items, *events])
        await self.db.flush()
        self._project_customer_metrics(customers, orders)
        return SeedSummary(
            customers=len(customers),
            products=len(products),
            orders=len(orders),
        )

    @staticmethod
    def _customers(organization_id: uuid.UUID, anchor: datetime) -> list[Customer]:
        customers: list[Customer] = []
        for index in range(60):
            first_name = FIRST_NAMES[index % len(FIRST_NAMES)]
            last_name = LAST_NAMES[(index // len(FIRST_NAMES)) % len(LAST_NAMES)]
            acquired_at = anchor - timedelta(days=420 - index * 6)
            company = (
                f"{COMPANY_PREFIXES[index % len(COMPANY_PREFIXES)]} "
                f"{COMPANY_SUFFIXES[(index // 3) % len(COMPANY_SUFFIXES)]}"
            )
            customers.append(
                Customer(
                    id=_stable_id(organization_id, "customer", index),
                    organization_id=organization_id,
                    external_id=f"DEMO-CUSTOMER-{index + 1:03d}",
                    name=f"{first_name} {last_name}",
                    email=f"{first_name}.{last_name}.{index + 1}@example.com".lower(),
                    company=company,
                    status="active",
                    segment="new",
                    acquired_at=acquired_at,
                    lifetime_value=Decimal("0.00"),
                    created_at=acquired_at,
                    updated_at=acquired_at,
                )
            )
        return customers

    @staticmethod
    def _products(organization_id: uuid.UUID, anchor: datetime) -> list[Product]:
        created_at = anchor - timedelta(days=430)
        return [
            Product(
                id=_stable_id(organization_id, "product", index),
                organization_id=organization_id,
                external_id=f"DEMO-PRODUCT-{index + 1:03d}",
                sku=sku,
                name=name,
                category=category,
                unit_price=_money(price_minor),
                status="active",
                created_at=created_at,
                updated_at=created_at,
            )
            for index, (sku, name, category, price_minor) in enumerate(PRODUCT_CATALOG)
        ]

    def _orders(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        anchor: datetime,
        customers: list[Customer],
        products: list[Product],
        rng: random.Random,
        currency: str,
    ) -> tuple[list[Order], list[OrderItem], list[OrderStatusEvent]]:
        orders: list[Order] = []
        items: list[OrderItem] = []
        events: list[OrderStatusEvent] = []
        oldest_month = _month_start(anchor, -11)
        order_index = 0
        for month_index in range(12):
            period_start = _month_start(oldest_month, month_index)
            period_end = min(_month_start(oldest_month, month_index + 1), anchor)
            if period_start >= period_end:
                continue
            growth_count = 16 + month_index * 2
            seasonal_factor = {5: 0.62, 6: 0.68, 11: 1.55, 12: 1.8}.get(
                period_start.month,
                1.0,
            )
            count = max(8, round(growth_count * seasonal_factor))
            for _ in range(count):
                ordered_at = _random_instant(rng, period_start, period_end)
                eligible_customers = [
                    customer for customer in customers if customer.acquired_at <= ordered_at
                ]
                customer_weights = [
                    self._customer_weight(index, ordered_at, anchor)
                    for index, _customer in enumerate(eligible_customers)
                ]
                customer = rng.choices(eligible_customers, weights=customer_weights, k=1)[0]
                status = rng.choice(STATUS_POPULATION)
                order_id = _stable_id(organization_id, "order", order_index)
                selected_products = self._select_products(rng, products)
                order_items: list[OrderItem] = []
                subtotal_minor = 0
                discount_minor = 0
                for item_index, product in enumerate(selected_products):
                    quantity = 2 if rng.random() < 0.13 else 1
                    gross_minor = int(product.unit_price * 100) * quantity
                    line_discount_minor = round(gross_minor * 0.05) if rng.random() < 0.12 else 0
                    subtotal_minor += gross_minor
                    discount_minor += line_discount_minor
                    order_items.append(
                        OrderItem(
                            id=_stable_id(
                                organization_id,
                                f"order-item-{order_index}",
                                item_index,
                            ),
                            organization_id=organization_id,
                            order_id=order_id,
                            product_id=product.id,
                            product_name=product.name,
                            sku=product.sku,
                            quantity=quantity,
                            unit_price=product.unit_price,
                            discount=_money(line_discount_minor),
                            line_total=_money(gross_minor - line_discount_minor),
                            created_at=ordered_at,
                        )
                    )
                taxable_minor = subtotal_minor - discount_minor
                tax_minor = round(taxable_minor * 0.08) if rng.random() < 0.42 else 0
                total_minor = taxable_minor + tax_minor
                order = Order(
                    id=order_id,
                    organization_id=organization_id,
                    customer_id=customer.id,
                    external_id=f"DEMO-ORDER-{order_index + 1:04d}",
                    order_number=f"ORD-{10_001 + order_index}",
                    status=status,
                    ordered_at=ordered_at,
                    subtotal=_money(subtotal_minor),
                    discount=_money(discount_minor),
                    tax=_money(tax_minor),
                    total=_money(total_minor),
                    currency=currency,
                    source="demo_seed",
                    created_at=ordered_at,
                    updated_at=ordered_at,
                )
                orders.append(order)
                items.extend(order_items)
                events.extend(
                    self._status_events(
                        organization_id=organization_id,
                        actor_user_id=actor_user_id,
                        order=order,
                        index=order_index,
                    )
                )
                order_index += 1
        return orders, items, events

    @staticmethod
    def _customer_weight(index: int, ordered_at: datetime, anchor: datetime) -> float:
        weight = 4.5 if index < 5 else 2.0 if index < 18 else 1.0
        if 5 <= index < 13 and ordered_at > anchor - timedelta(days=170):
            return 0.03
        return weight

    @staticmethod
    def _select_products(rng: random.Random, products: list[Product]) -> list[Product]:
        requested = 1 if rng.random() < 0.68 else 2 if rng.random() < 0.82 else 3
        available = list(products)
        weights = list(PRODUCT_WEIGHTS)
        selected: list[Product] = []
        for _ in range(requested):
            product = rng.choices(available, weights=weights, k=1)[0]
            position = available.index(product)
            selected.append(product)
            available.pop(position)
            weights.pop(position)
        return selected

    @staticmethod
    def _status_events(
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        order: Order,
        index: int,
    ) -> list[OrderStatusEvent]:
        initial_time = order.ordered_at - timedelta(minutes=20)
        events = [
            OrderStatusEvent(
                id=_stable_id(organization_id, f"order-event-{index}", 0),
                organization_id=organization_id,
                order_id=order.id,
                changed_by_user_id=actor_user_id,
                from_status=None,
                to_status="pending",
                reason="Created by the deterministic demo seed.",
                occurred_at=initial_time,
            )
        ]
        if order.status != "pending":
            events.append(
                OrderStatusEvent(
                    id=_stable_id(organization_id, f"order-event-{index}", 1),
                    organization_id=organization_id,
                    order_id=order.id,
                    changed_by_user_id=actor_user_id,
                    from_status="pending",
                    to_status=order.status,
                    reason="Advanced by the deterministic demo seed.",
                    occurred_at=order.ordered_at,
                )
            )
        return events

    @staticmethod
    def _project_customer_metrics(customers: list[Customer], orders: list[Order]) -> None:
        eligible_orders: dict[uuid.UUID, list[Order]] = {}
        for order in orders:
            if order.status in ELIGIBLE_REVENUE_STATUSES:
                eligible_orders.setdefault(order.customer_id, []).append(order)
        for customer in customers:
            history = eligible_orders.get(customer.id, [])
            customer.lifetime_value = sum(
                (order.total for order in history),
                start=Decimal("0.00"),
            )
            last_order_at = max(
                (order.ordered_at for order in history),
                default=None,
            )
            customer.last_order_at = last_order_at
            if not history:
                customer.segment = "new"
                continue
            if last_order_at is None:
                continue
            recency = (max(order.ordered_at for order in orders) - last_order_at).days
            if recency > 180:
                customer.status = "inactive"
                customer.segment = "inactive"
            elif recency > 90:
                customer.status = "at_risk"
                customer.segment = "at_risk"
            elif customer.lifetime_value >= Decimal("5000.00") or len(history) >= 10:
                customer.segment = "high_value"
            elif len(history) >= 5:
                customer.segment = "loyal"
            elif len(history) >= 2:
                customer.segment = "repeat"
