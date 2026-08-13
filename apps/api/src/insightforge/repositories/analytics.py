from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import and_, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.models import Customer, Order, OrderItem, Product
from insightforge.repositories.commerce import REVENUE_STATUSES


@dataclass(frozen=True, slots=True)
class PeriodSummary:
    revenue: Decimal
    order_count: int
    customers: int
    new_customers: int
    repeat_customers: int


@dataclass(frozen=True, slots=True)
class SeriesAggregate:
    period_start: date
    revenue: Decimal
    order_count: int


@dataclass(frozen=True, slots=True)
class AcquisitionAggregate:
    period_start: date
    new_customers: int


@dataclass(frozen=True, slots=True)
class RankedAggregate:
    id: uuid.UUID | None
    label: str
    revenue: Decimal
    units: int
    count: int


@dataclass(frozen=True, slots=True)
class RecentOrder:
    order: Order
    customer_name: str


class AnalyticsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def currencies(
        self,
        organization_id: uuid.UUID,
        *,
        start: datetime,
        end: datetime,
    ) -> set[str]:
        values = await self.db.scalars(
            select(distinct(Order.currency)).where(
                Order.organization_id == organization_id,
                Order.status.in_(REVENUE_STATUSES),
                Order.ordered_at >= start,
                Order.ordered_at < end,
            )
        )
        return set(values.all())

    async def summary(
        self,
        organization_id: uuid.UUID,
        *,
        start: datetime,
        end: datetime,
    ) -> PeriodSummary:
        revenue_row = (
            await self.db.execute(
                select(
                    func.coalesce(func.sum(Order.total), Decimal("0.00")),
                    func.count(Order.id),
                ).where(
                    Order.organization_id == organization_id,
                    Order.status.in_(REVENUE_STATUSES),
                    Order.ordered_at >= start,
                    Order.ordered_at < end,
                )
            )
        ).one()
        history = (
            select(
                Order.customer_id.label("customer_id"),
                func.min(Order.ordered_at).label("first_order_at"),
                func.count(Order.id).label("order_count"),
            )
            .where(
                Order.organization_id == organization_id,
                Order.status.in_(REVENUE_STATUSES),
                Order.ordered_at < end,
            )
            .group_by(Order.customer_id)
            .subquery()
        )
        customer_row = (
            await self.db.execute(
                select(
                    func.count(history.c.customer_id),
                    func.count(history.c.customer_id).filter(
                        history.c.first_order_at >= start,
                        history.c.first_order_at < end,
                    ),
                    func.count(history.c.customer_id).filter(history.c.order_count >= 2),
                )
            )
        ).one()
        return PeriodSummary(
            revenue=Decimal(revenue_row[0]),
            order_count=int(revenue_row[1]),
            customers=int(customer_row[0]),
            new_customers=int(customer_row[1]),
            repeat_customers=int(customer_row[2]),
        )

    async def revenue_series(
        self,
        organization_id: uuid.UUID,
        *,
        start: datetime,
        end: datetime,
        time_zone: str,
        granularity: str,
    ) -> list[SeriesAggregate]:
        bucket = func.date_trunc(
            granularity,
            func.timezone(time_zone, Order.ordered_at),
        ).label("period_start")
        rows = (
            await self.db.execute(
                select(
                    bucket,
                    func.coalesce(func.sum(Order.total), Decimal("0.00")),
                    func.count(Order.id),
                )
                .where(
                    Order.organization_id == organization_id,
                    Order.status.in_(REVENUE_STATUSES),
                    Order.ordered_at >= start,
                    Order.ordered_at < end,
                )
                .group_by(bucket)
                .order_by(bucket)
            )
        ).all()
        return [
            SeriesAggregate(
                period_start=row[0].date(),
                revenue=Decimal(row[1]),
                order_count=int(row[2]),
            )
            for row in rows
        ]

    async def acquisition_series(
        self,
        organization_id: uuid.UUID,
        *,
        start: datetime,
        end: datetime,
        time_zone: str,
        granularity: str,
    ) -> list[AcquisitionAggregate]:
        first_orders = (
            select(
                Order.customer_id.label("customer_id"),
                func.min(Order.ordered_at).label("first_order_at"),
            )
            .where(
                Order.organization_id == organization_id,
                Order.status.in_(REVENUE_STATUSES),
                Order.ordered_at < end,
            )
            .group_by(Order.customer_id)
            .subquery()
        )
        bucket = func.date_trunc(
            granularity,
            func.timezone(time_zone, first_orders.c.first_order_at),
        ).label("period_start")
        rows = (
            await self.db.execute(
                select(bucket, func.count(first_orders.c.customer_id))
                .where(
                    first_orders.c.first_order_at >= start,
                    first_orders.c.first_order_at < end,
                )
                .group_by(bucket)
                .order_by(bucket)
            )
        ).all()
        return [
            AcquisitionAggregate(period_start=row[0].date(), new_customers=int(row[1]))
            for row in rows
        ]

    async def products(
        self,
        organization_id: uuid.UUID,
        *,
        start: datetime,
        end: datetime,
        limit: int = 10,
    ) -> list[RankedAggregate]:
        rows = (
            await self.db.execute(
                select(
                    Product.id,
                    Product.name,
                    func.coalesce(func.sum(OrderItem.line_total), Decimal("0.00")),
                    func.coalesce(func.sum(OrderItem.quantity), 0),
                    func.count(distinct(Order.id)),
                )
                .join(
                    OrderItem,
                    and_(
                        OrderItem.organization_id == Product.organization_id,
                        OrderItem.product_id == Product.id,
                    ),
                )
                .join(
                    Order,
                    and_(
                        Order.organization_id == OrderItem.organization_id,
                        Order.id == OrderItem.order_id,
                    ),
                )
                .where(
                    Product.organization_id == organization_id,
                    Order.status.in_(REVENUE_STATUSES),
                    Order.ordered_at >= start,
                    Order.ordered_at < end,
                )
                .group_by(Product.id, Product.name)
                .order_by(func.sum(OrderItem.line_total).desc(), Product.id.asc())
                .limit(limit)
            )
        ).all()
        return [
            RankedAggregate(
                id=row[0],
                label=row[1],
                revenue=Decimal(row[2]),
                units=int(row[3]),
                count=int(row[4]),
            )
            for row in rows
        ]

    async def categories(
        self,
        organization_id: uuid.UUID,
        *,
        start: datetime,
        end: datetime,
    ) -> list[RankedAggregate]:
        rows = (
            await self.db.execute(
                select(
                    Product.category,
                    func.coalesce(func.sum(OrderItem.line_total), Decimal("0.00")),
                    func.coalesce(func.sum(OrderItem.quantity), 0),
                    func.count(distinct(Order.id)),
                )
                .join(
                    OrderItem,
                    and_(
                        OrderItem.organization_id == Product.organization_id,
                        OrderItem.product_id == Product.id,
                    ),
                )
                .join(
                    Order,
                    and_(
                        Order.organization_id == OrderItem.organization_id,
                        Order.id == OrderItem.order_id,
                    ),
                )
                .where(
                    Product.organization_id == organization_id,
                    Order.status.in_(REVENUE_STATUSES),
                    Order.ordered_at >= start,
                    Order.ordered_at < end,
                )
                .group_by(Product.category)
                .order_by(func.sum(OrderItem.line_total).desc(), Product.category.asc())
            )
        ).all()
        return [
            RankedAggregate(
                id=None,
                label=row[0],
                revenue=Decimal(row[1]),
                units=int(row[2]),
                count=int(row[3]),
            )
            for row in rows
        ]

    async def order_statuses(
        self,
        organization_id: uuid.UUID,
        *,
        start: datetime,
        end: datetime,
    ) -> list[RankedAggregate]:
        rows = (
            await self.db.execute(
                select(Order.status, func.count(Order.id))
                .where(
                    Order.organization_id == organization_id,
                    Order.ordered_at >= start,
                    Order.ordered_at < end,
                )
                .group_by(Order.status)
                .order_by(func.count(Order.id).desc(), Order.status.asc())
            )
        ).all()
        return [
            RankedAggregate(
                id=None,
                label=row[0],
                revenue=Decimal("0.00"),
                units=0,
                count=int(row[1]),
            )
            for row in rows
        ]

    async def recent_orders(
        self,
        organization_id: uuid.UUID,
        *,
        start: datetime,
        end: datetime,
        limit: int = 10,
    ) -> list[RecentOrder]:
        rows = (
            await self.db.execute(
                select(Order, Customer.name)
                .join(
                    Customer,
                    and_(
                        Customer.organization_id == Order.organization_id,
                        Customer.id == Order.customer_id,
                    ),
                )
                .where(
                    Order.organization_id == organization_id,
                    Order.ordered_at >= start,
                    Order.ordered_at < end,
                )
                .order_by(Order.ordered_at.desc(), Order.id.asc())
                .limit(limit)
            )
        ).all()
        return [RecentOrder(order=row[0], customer_name=row[1]) for row in rows]

    async def filter_options(
        self,
        organization_id: uuid.UUID,
    ) -> tuple[list[str], list[str], list[str]]:
        categories = list(
            (
                await self.db.scalars(
                    select(distinct(Product.category))
                    .where(Product.organization_id == organization_id)
                    .order_by(Product.category)
                )
            ).all()
        )
        statuses = list(
            (
                await self.db.scalars(
                    select(distinct(Order.status))
                    .where(Order.organization_id == organization_id)
                    .order_by(Order.status)
                )
            ).all()
        )
        sources = list(
            (
                await self.db.scalars(
                    select(distinct(Order.source))
                    .where(Order.organization_id == organization_id)
                    .order_by(Order.source)
                )
            ).all()
        )
        return categories, statuses, sources
