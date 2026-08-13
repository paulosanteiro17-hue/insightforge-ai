from __future__ import annotations

import builtins
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal, cast

from sqlalchemy import Select, and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.core.pagination import PageResult, SortField
from insightforge.models import Customer, Order, OrderItem, OrderStatusEvent, Product

if TYPE_CHECKING:
    from insightforge.api.dependencies import TenantContext

REVENUE_STATUSES = ("paid", "processing", "completed")


@dataclass(frozen=True, slots=True)
class CustomerRow:
    customer: Customer
    order_count: int


@dataclass(frozen=True, slots=True)
class ProductRow:
    product: Product
    units_sold: int
    revenue: Decimal


@dataclass(frozen=True, slots=True)
class ProductPeriodMetrics:
    units_sold: int
    revenue: Decimal
    order_count: int


@dataclass(frozen=True, slots=True)
class ProductTrendPoint:
    period_start: datetime
    units_sold: int
    revenue: Decimal


@dataclass(frozen=True, slots=True)
class ProductPerformance:
    current: ProductPeriodMetrics
    previous: ProductPeriodMetrics
    trend: list[ProductTrendPoint]


@dataclass(frozen=True, slots=True)
class OrderRow:
    order: Order
    customer: Customer
    item_count: int


@dataclass(frozen=True, slots=True)
class CustomerMetrics:
    spend: Decimal
    order_count: int
    last_order_at: datetime | None


class CustomerRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        context: TenantContext,
        *,
        page: int,
        page_size: int,
        sort: tuple[SortField, ...],
        query: str | None,
        statuses: tuple[str, ...],
        segments: tuple[str, ...],
        created_from: datetime | None,
        created_to: datetime | None,
        include_archived: bool,
    ) -> PageResult[CustomerRow]:
        order_count = (
            select(func.count(Order.id))
            .where(
                Order.organization_id == Customer.organization_id,
                Order.customer_id == Customer.id,
                Order.status.in_(REVENUE_STATUSES),
            )
            .correlate(Customer)
            .scalar_subquery()
        )
        filters = [Customer.organization_id == context.organization.id]
        if not include_archived:
            filters.append(Customer.deleted_at.is_(None))
        if query:
            pattern = f"%{query}%"
            filters.append(
                or_(
                    Customer.name.ilike(pattern),
                    Customer.email.ilike(pattern),
                    Customer.company.ilike(pattern),
                )
            )
        if statuses:
            filters.append(Customer.status.in_(statuses))
        if segments:
            filters.append(Customer.segment.in_(segments))
        if created_from:
            filters.append(Customer.created_at >= created_from)
        if created_to:
            filters.append(Customer.created_at < created_to)

        statement = select(Customer, order_count.label("order_count")).where(*filters)
        order_map: dict[str, Any] = {
            "name": func.lower(Customer.name),
            "total_spent": Customer.lifetime_value,
            "last_order_at": Customer.last_order_at,
            "created_at": Customer.created_at,
        }
        statement = self._apply_order(statement, sort, order_map, Customer.id)
        total = int(await self.db.scalar(select(func.count(Customer.id)).where(*filters)) or 0)
        rows = (
            await self.db.execute(statement.offset((page - 1) * page_size).limit(page_size))
        ).all()
        return PageResult(
            items=[CustomerRow(customer=row[0], order_count=int(row[1] or 0)) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def get(
        self,
        context: TenantContext,
        customer_id: uuid.UUID,
        *,
        include_archived: bool = False,
        for_update: bool = False,
    ) -> Customer | None:
        statement = select(Customer).where(
            Customer.organization_id == context.organization.id,
            Customer.id == customer_id,
        )
        if not include_archived:
            statement = statement.where(Customer.deleted_at.is_(None))
        if for_update:
            statement = statement.with_for_update()
        return cast(Customer | None, await self.db.scalar(statement))

    async def metrics(
        self,
        context: TenantContext,
        customer_id: uuid.UUID,
    ) -> CustomerMetrics:
        row = (
            await self.db.execute(
                select(
                    func.coalesce(func.sum(Order.total), Decimal("0.00")),
                    func.count(Order.id),
                    func.max(Order.ordered_at),
                ).where(
                    Order.organization_id == context.organization.id,
                    Order.customer_id == customer_id,
                    Order.status.in_(REVENUE_STATUSES),
                )
            )
        ).one()
        return CustomerMetrics(
            spend=Decimal(row[0]),
            order_count=int(row[1]),
            last_order_at=row[2],
        )

    @staticmethod
    def _apply_order(
        statement: Select[tuple[Customer, int]],
        sort: tuple[SortField, ...],
        mapping: Mapping[str, Any],
        tie_breaker: Any,
    ) -> Select[tuple[Customer, int]]:
        expressions: builtins.list[Any] = []
        for field in sort:
            expression = mapping[field.name]
            expressions.append(expression.desc() if field.descending else expression.asc())
        expressions.append(tie_breaker.asc())
        return statement.order_by(*expressions)


class ProductRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _aggregate_statement(
        self, organization_id: uuid.UUID
    ) -> Select[tuple[Product, int, Decimal]]:
        eligible_quantity = case(
            (Order.id.is_not(None), OrderItem.quantity),
            else_=0,
        )
        eligible_revenue = case(
            (Order.id.is_not(None), OrderItem.line_total),
            else_=Decimal("0.00"),
        )
        return (
            select(
                Product,
                func.coalesce(func.sum(eligible_quantity), 0).label("units_sold"),
                func.coalesce(func.sum(eligible_revenue), Decimal("0.00")).label("revenue"),
            )
            .outerjoin(
                OrderItem,
                and_(
                    OrderItem.organization_id == Product.organization_id,
                    OrderItem.product_id == Product.id,
                ),
            )
            .outerjoin(
                Order,
                and_(
                    Order.organization_id == OrderItem.organization_id,
                    Order.id == OrderItem.order_id,
                    Order.status.in_(REVENUE_STATUSES),
                ),
            )
            .where(Product.organization_id == organization_id)
            .group_by(Product.id)
        )

    async def list(
        self,
        context: TenantContext,
        *,
        page: int,
        page_size: int,
        sort: tuple[SortField, ...],
        query: str | None,
        statuses: tuple[str, ...],
        categories: tuple[str, ...],
    ) -> PageResult[ProductRow]:
        statement = self._aggregate_statement(context.organization.id)
        filters = []
        if query:
            pattern = f"%{query}%"
            filters.append(or_(Product.name.ilike(pattern), Product.sku.ilike(pattern)))
        if statuses:
            filters.append(Product.status.in_(statuses))
        if categories:
            filters.append(Product.category.in_(categories))
        if filters:
            statement = statement.where(*filters)
        units_sold = statement.selected_columns.units_sold
        revenue = statement.selected_columns.revenue
        average_price = case((units_sold > 0, revenue / units_sold), else_=None)
        order_map: dict[str, Any] = {
            "name": func.lower(Product.name),
            "units_sold": units_sold,
            "revenue": revenue,
            "average_price": average_price,
            "created_at": Product.created_at,
        }
        expressions: builtins.list[Any] = []
        for field in sort:
            expression = order_map[field.name]
            expressions.append(expression.desc() if field.descending else expression.asc())
        statement = statement.order_by(*expressions, Product.id.asc())
        count_filters = [Product.organization_id == context.organization.id, *filters]
        total = int(await self.db.scalar(select(func.count(Product.id)).where(*count_filters)) or 0)
        rows = (
            await self.db.execute(statement.offset((page - 1) * page_size).limit(page_size))
        ).all()
        return PageResult(
            items=[
                ProductRow(product=row[0], units_sold=int(row[1]), revenue=Decimal(row[2]))
                for row in rows
            ],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def get(
        self,
        context: TenantContext,
        product_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> Product | None:
        statement = select(Product).where(
            Product.organization_id == context.organization.id,
            Product.id == product_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(Product | None, await self.db.scalar(statement))

    async def get_many_for_update(
        self,
        context: TenantContext,
        product_ids: set[uuid.UUID],
    ) -> builtins.list[Product]:
        return [
            product
            for product in (
                await self.db.scalars(
                    select(Product)
                    .where(
                        Product.organization_id == context.organization.id,
                        Product.id.in_(product_ids),
                    )
                    .with_for_update()
                )
            ).all()
        ]

    async def metrics(
        self,
        context: TenantContext,
        product_id: uuid.UUID,
    ) -> ProductRow | None:
        row = (
            await self.db.execute(
                self._aggregate_statement(context.organization.id).where(Product.id == product_id)
            )
        ).one_or_none()
        if row is None:
            return None
        return ProductRow(product=row[0], units_sold=int(row[1]), revenue=Decimal(row[2]))

    async def performance(
        self,
        context: TenantContext,
        product_id: uuid.UUID,
        *,
        current_start: datetime,
        current_end: datetime,
        comparison_start: datetime,
        comparison_end: datetime,
        granularity: Literal["day", "week", "month"],
    ) -> ProductPerformance | None:
        product_exists = await self.db.scalar(
            select(Product.id).where(
                Product.organization_id == context.organization.id,
                Product.id == product_id,
            )
        )
        if product_exists is None:
            return None
        current = await self._period_performance(
            context.organization.id,
            product_id,
            start=current_start,
            end=current_end,
        )
        previous = await self._period_performance(
            context.organization.id,
            product_id,
            start=comparison_start,
            end=comparison_end,
        )
        local_bucket = func.date_trunc(
            granularity,
            func.timezone(context.organization.timezone, Order.ordered_at),
        )
        rows = (
            await self.db.execute(
                select(
                    local_bucket.label("period_start"),
                    func.coalesce(func.sum(OrderItem.quantity), 0),
                    func.coalesce(func.sum(OrderItem.line_total), Decimal("0.00")),
                )
                .select_from(OrderItem)
                .join(
                    Order,
                    and_(
                        Order.organization_id == OrderItem.organization_id,
                        Order.id == OrderItem.order_id,
                    ),
                )
                .where(
                    OrderItem.organization_id == context.organization.id,
                    OrderItem.product_id == product_id,
                    Order.status.in_(REVENUE_STATUSES),
                    Order.ordered_at >= current_start,
                    Order.ordered_at < current_end,
                )
                .group_by(local_bucket)
                .order_by(local_bucket.asc())
            )
        ).all()
        return ProductPerformance(
            current=current,
            previous=previous,
            trend=[
                ProductTrendPoint(
                    period_start=row[0],
                    units_sold=int(row[1]),
                    revenue=Decimal(row[2]),
                )
                for row in rows
            ],
        )

    async def _period_performance(
        self,
        organization_id: uuid.UUID,
        product_id: uuid.UUID,
        *,
        start: datetime,
        end: datetime,
    ) -> ProductPeriodMetrics:
        row = (
            await self.db.execute(
                select(
                    func.coalesce(func.sum(OrderItem.quantity), 0),
                    func.coalesce(func.sum(OrderItem.line_total), Decimal("0.00")),
                    func.count(func.distinct(Order.id)),
                )
                .select_from(OrderItem)
                .join(
                    Order,
                    and_(
                        Order.organization_id == OrderItem.organization_id,
                        Order.id == OrderItem.order_id,
                    ),
                )
                .where(
                    OrderItem.organization_id == organization_id,
                    OrderItem.product_id == product_id,
                    Order.status.in_(REVENUE_STATUSES),
                    Order.ordered_at >= start,
                    Order.ordered_at < end,
                )
            )
        ).one()
        return ProductPeriodMetrics(
            units_sold=int(row[0]),
            revenue=Decimal(row[1]),
            order_count=int(row[2]),
        )


class OrderRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        context: TenantContext,
        *,
        page: int,
        page_size: int,
        sort: tuple[SortField, ...],
        query: str | None,
        statuses: tuple[str, ...],
        customer_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> PageResult[OrderRow]:
        item_count = (
            select(func.coalesce(func.sum(OrderItem.quantity), 0))
            .where(
                OrderItem.organization_id == Order.organization_id,
                OrderItem.order_id == Order.id,
            )
            .correlate(Order)
            .scalar_subquery()
        )
        filters = [Order.organization_id == context.organization.id]
        if query:
            pattern = f"%{query}%"
            filters.append(or_(Order.order_number.ilike(pattern), Customer.name.ilike(pattern)))
        if statuses:
            filters.append(Order.status.in_(statuses))
        if customer_id:
            filters.append(Order.customer_id == customer_id)
        if date_from:
            filters.append(Order.ordered_at >= date_from)
        if date_to:
            filters.append(Order.ordered_at < date_to)
        statement = (
            select(Order, Customer, item_count.label("item_count"))
            .join(
                Customer,
                and_(
                    Customer.organization_id == Order.organization_id,
                    Customer.id == Order.customer_id,
                ),
            )
            .where(*filters)
        )
        order_map: dict[str, Any] = {
            "ordered_at": Order.ordered_at,
            "total": Order.total,
            "status": Order.status,
            "created_at": Order.created_at,
        }
        expressions: builtins.list[Any] = []
        for field in sort:
            expression = order_map[field.name]
            expressions.append(expression.desc() if field.descending else expression.asc())
        statement = statement.order_by(*expressions, Order.id.asc())
        total_statement = (
            select(func.count(Order.id))
            .select_from(Order)
            .join(
                Customer,
                and_(
                    Customer.organization_id == Order.organization_id,
                    Customer.id == Order.customer_id,
                ),
            )
            .where(*filters)
        )
        total = int(await self.db.scalar(total_statement) or 0)
        rows = (
            await self.db.execute(statement.offset((page - 1) * page_size).limit(page_size))
        ).all()
        return PageResult(
            items=[OrderRow(order=row[0], customer=row[1], item_count=int(row[2])) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def get(
        self,
        context: TenantContext,
        order_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> tuple[Order, Customer] | None:
        statement = (
            select(Order, Customer)
            .join(
                Customer,
                and_(
                    Customer.organization_id == Order.organization_id,
                    Customer.id == Order.customer_id,
                ),
            )
            .where(
                Order.organization_id == context.organization.id,
                Order.id == order_id,
            )
        )
        if for_update:
            statement = statement.with_for_update(of=Order)
        row = (await self.db.execute(statement)).one_or_none()
        return None if row is None else (row[0], row[1])

    async def items(self, context: TenantContext, order_id: uuid.UUID) -> builtins.list[OrderItem]:
        return [
            item
            for item in (
                await self.db.scalars(
                    select(OrderItem)
                    .where(
                        OrderItem.organization_id == context.organization.id,
                        OrderItem.order_id == order_id,
                    )
                    .order_by(OrderItem.created_at.asc(), OrderItem.id.asc())
                )
            ).all()
        ]

    async def events(
        self, context: TenantContext, order_id: uuid.UUID
    ) -> builtins.list[OrderStatusEvent]:
        return [
            event
            for event in (
                await self.db.scalars(
                    select(OrderStatusEvent)
                    .where(
                        OrderStatusEvent.organization_id == context.organization.id,
                        OrderStatusEvent.order_id == order_id,
                    )
                    .order_by(
                        OrderStatusEvent.occurred_at.asc(),
                        OrderStatusEvent.id.asc(),
                    )
                )
            ).all()
        ]
