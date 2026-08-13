from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.core.concurrency import ensure_version
from insightforge.core.database_errors import integrity_constraint_name
from insightforge.core.money import decimal_to_minor, minor_to_decimal
from insightforge.core.pagination import PageResult, SortField, parse_sort, validate_time_range
from insightforge.core.problems import AppError
from insightforge.core.revisions import increment_data_revision
from insightforge.core.time import utc_now
from insightforge.models import Customer, Order, OrderItem, OrderStatusEvent
from insightforge.models.enums import OrderStatus, ProductStatus
from insightforge.repositories.commerce import (
    CustomerRepository,
    OrderRepository,
    OrderRow,
    ProductRepository,
)
from insightforge.schemas.commerce import (
    CustomerReferenceView,
    OrderCommandRequest,
    OrderCreateRequest,
    OrderItemView,
    OrderStatusEventView,
    OrderUpdateRequest,
    OrderView,
)
from insightforge.services.commerce_common import _duplicate, _normalize_datetime, _not_found
from insightforge.services.idempotency import (
    IdempotencyService,
    canonical_request_hash,
    validate_idempotency_key,
)

if TYPE_CHECKING:
    from insightforge.api.dependencies import TenantContext

ORDER_UNIQUE_CONSTRAINTS = {
    "uq_orders_external_id",
    "uq_orders_org_number",
}

ORDER_TRANSITIONS: dict[str, frozenset[str]] = {
    OrderStatus.PENDING.value: frozenset({OrderStatus.PAID.value, OrderStatus.CANCELLED.value}),
    OrderStatus.PAID.value: frozenset(
        {OrderStatus.PROCESSING.value, OrderStatus.COMPLETED.value, OrderStatus.REFUNDED.value}
    ),
    OrderStatus.PROCESSING.value: frozenset(
        {OrderStatus.COMPLETED.value, OrderStatus.REFUNDED.value}
    ),
    OrderStatus.COMPLETED.value: frozenset({OrderStatus.REFUNDED.value}),
    OrderStatus.CANCELLED.value: frozenset(),
    OrderStatus.REFUNDED.value: frozenset(),
}


def order_view(
    row: OrderRow,
    *,
    items: list[OrderItem] | None = None,
    events: list[OrderStatusEvent] | None = None,
) -> OrderView:
    return OrderView(
        id=row.order.id,
        external_id=row.order.external_id,
        order_number=row.order.order_number,
        status=row.order.status,
        ordered_at=row.order.ordered_at,
        subtotal_minor=decimal_to_minor(row.order.subtotal),
        discount_minor=decimal_to_minor(row.order.discount),
        tax_minor=decimal_to_minor(row.order.tax),
        total_minor=decimal_to_minor(row.order.total),
        currency=row.order.currency,
        source=row.order.source,
        customer=CustomerReferenceView(
            id=row.customer.id,
            name=row.customer.name,
            email=row.customer.email,
        ),
        item_count=row.item_count,
        items=(
            [
                OrderItemView(
                    id=item.id,
                    product_id=item.product_id,
                    product_name=item.product_name,
                    sku=item.sku,
                    quantity=item.quantity,
                    unit_price_minor=decimal_to_minor(item.unit_price),
                    discount_minor=decimal_to_minor(item.discount),
                    line_total_minor=decimal_to_minor(item.line_total),
                )
                for item in items
            ]
            if items is not None
            else None
        ),
        status_history=(
            [
                OrderStatusEventView(
                    id=event.id,
                    from_status=event.from_status,
                    to_status=event.to_status,
                    reason=event.reason,
                    changed_by_user_id=event.changed_by_user_id,
                    occurred_at=event.occurred_at,
                )
                for event in events
            ]
            if events is not None
            else None
        ),
        version=row.order.version,
        created_at=row.order.created_at,
        updated_at=row.order.updated_at,
    )


class OrderService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = OrderRepository(db)
        self.customers = CustomerRepository(db)
        self.products = ProductRepository(db)
        self.idempotency = IdempotencyService(db)

    async def list(
        self,
        context: TenantContext,
        *,
        page: int,
        page_size: int,
        sort_value: str | None,
        query: str | None,
        statuses: tuple[str, ...],
        customer_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> PageResult[OrderView]:
        validate_time_range(date_from, date_to)
        sort = parse_sort(
            sort_value,
            allowed=frozenset({"ordered_at", "total", "status", "created_at"}),
            default=(SortField("ordered_at", True),),
        )
        result = await self.repository.list(
            context,
            page=page,
            page_size=page_size,
            sort=sort,
            query=query.strip() if query else None,
            statuses=statuses,
            customer_id=customer_id,
            date_from=date_from,
            date_to=date_to,
        )
        return PageResult(
            [order_view(row) for row in result.items],
            page,
            page_size,
            result.total,
        )

    async def detail(self, context: TenantContext, order_id: uuid.UUID) -> OrderView:
        found = await self.repository.get(context, order_id)
        if found is None:
            raise _not_found()
        order, customer = found
        items = await self.repository.items(context, order_id)
        events = await self.repository.events(context, order_id)
        return order_view(
            OrderRow(order, customer, sum(item.quantity for item in items)),
            items=items,
            events=events,
        )

    async def create(
        self,
        context: TenantContext,
        payload: OrderCreateRequest,
        idempotency_key: str | None,
    ) -> tuple[OrderView, bool]:
        key = validate_idempotency_key(idempotency_key)
        request_hash = canonical_request_hash(payload.model_dump(mode="json"))
        scope = f"{context.organization.id}:{context.identity.user.id}"
        operation = "create_order"
        replay_body = await self.idempotency.replay_response_body(
            scope_key=scope,
            operation=operation,
            key=key,
            request_hash=request_hash,
        )
        if replay_body is not None:
            return OrderView.model_validate(replay_body), True
        customer = await self.customers.get(
            context, payload.customer_id, include_archived=False, for_update=True
        )
        if customer is None:
            raise _not_found()
        products = await self.products.get_many_for_update(
            context, {item.product_id for item in payload.items}
        )
        product_map = {product.id: product for product in products}
        if len(product_map) != len(payload.items) or any(
            product.status != ProductStatus.ACTIVE.value or product.deleted_at is not None
            for product in products
        ):
            raise _not_found()

        order_id = uuid.uuid4()
        item_rows: list[OrderItem] = []
        subtotal_minor = 0
        item_discount_minor = 0
        for item in payload.items:
            product = product_map[item.product_id]
            gross_minor = decimal_to_minor(product.unit_price) * item.quantity
            if item.discount_minor > gross_minor:
                raise AppError(
                    status=422,
                    code="validation_error",
                    title="Request validation failed",
                    detail="An item discount cannot exceed its gross line amount.",
                )
            subtotal_minor += gross_minor
            item_discount_minor += item.discount_minor
            item_rows.append(
                OrderItem(
                    id=uuid.uuid4(),
                    organization_id=context.organization.id,
                    order_id=order_id,
                    product_id=product.id,
                    product_name=product.name,
                    sku=product.sku,
                    quantity=item.quantity,
                    unit_price=product.unit_price,
                    discount=minor_to_decimal(item.discount_minor),
                    line_total=minor_to_decimal(gross_minor - item.discount_minor),
                )
            )
        total_discount_minor = item_discount_minor + payload.discount_minor
        total_minor = subtotal_minor - total_discount_minor + payload.tax_minor
        if total_minor < 0:
            raise AppError(
                status=422,
                code="validation_error",
                title="Request validation failed",
                detail="Order discounts cannot make the total negative.",
            )
        order = Order(
            id=order_id,
            organization_id=context.organization.id,
            customer_id=customer.id,
            external_id=payload.external_id,
            order_number=payload.order_number.strip(),
            status=payload.status.value,
            ordered_at=_normalize_datetime(payload.ordered_at),
            subtotal=minor_to_decimal(subtotal_minor),
            discount=minor_to_decimal(total_discount_minor),
            tax=minor_to_decimal(payload.tax_minor),
            total=minor_to_decimal(total_minor),
            currency=context.organization.reporting_currency,
            source="manual",
        )
        record = self.idempotency.start(
            scope_key=scope,
            actor_user_id=context.identity.user.id,
            operation=operation,
            key=key,
            request_hash=request_hash,
        )
        self.db.add(order)
        await self.db.flush()
        event = OrderStatusEvent(
            id=uuid.uuid4(),
            organization_id=context.organization.id,
            order_id=order_id,
            changed_by_user_id=context.identity.user.id,
            from_status=None,
            to_status=order.status,
            reason="Order created.",
            occurred_at=order.ordered_at,
        )
        self.db.add_all([*item_rows, event])
        await self.db.flush()
        await self._refresh_customer(context, customer)
        await increment_data_revision(self.db, context.organization)
        created_view = order_view(
            OrderRow(
                order=order,
                customer=customer,
                item_count=sum(item.quantity for item in item_rows),
            ),
            items=item_rows,
            events=[event],
        )
        self.idempotency.complete(
            record,
            status_code=201,
            resource_type="order",
            resource_id=order_id,
            response_body=created_view.model_dump(mode="json"),
        )
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            competing = await self.idempotency.find(scope_key=scope, operation=operation, key=key)
            if competing is not None:
                replay_body = await self.idempotency.replay_response_body(
                    scope_key=scope,
                    operation=operation,
                    key=key,
                    request_hash=request_hash,
                )
                if replay_body is not None:
                    return OrderView.model_validate(replay_body), True
            if integrity_constraint_name(exc) in ORDER_UNIQUE_CONSTRAINTS:
                raise _duplicate(
                    "An order with this order number or external ID already exists."
                ) from exc
            raise
        return created_view, False

    async def update_status(
        self,
        context: TenantContext,
        order_id: uuid.UUID,
        payload: OrderUpdateRequest,
        expected_version: int,
    ) -> OrderView:
        if payload.status in {OrderStatus.CANCELLED, OrderStatus.REFUNDED}:
            raise AppError(
                status=409,
                code="invalid_state_transition",
                title="Order status transition is invalid",
                detail="Use the dedicated cancel or refund command for this status.",
            )
        await self._transition(
            context,
            order_id,
            target=payload.status.value,
            reason="Order status updated.",
            expected_version=expected_version,
        )
        return await self.detail(context, order_id)

    async def command(
        self,
        context: TenantContext,
        order_id: uuid.UUID,
        payload: OrderCommandRequest,
        *,
        command: str,
        idempotency_key: str | None,
    ) -> tuple[OrderView, bool]:
        key = validate_idempotency_key(idempotency_key)
        target = "cancelled" if command == "cancel" else "refunded"
        request_hash = canonical_request_hash(
            {"order_id": str(order_id), "reason": payload.reason, "target": target}
        )
        scope = f"{context.organization.id}:{context.identity.user.id}"
        operation = f"{command}_order:{order_id}"
        replay_body = await self.idempotency.replay_response_body(
            scope_key=scope,
            operation=operation,
            key=key,
            request_hash=request_hash,
        )
        if replay_body is not None:
            return OrderView.model_validate(replay_body), True
        record = self.idempotency.start(
            scope_key=scope,
            actor_user_id=context.identity.user.id,
            operation=operation,
            key=key,
            request_hash=request_hash,
        )
        await self._transition(
            context,
            order_id,
            target=target,
            reason=payload.reason,
            commit=False,
        )
        command_view = await self.detail(context, order_id)
        self.idempotency.complete(
            record,
            status_code=200,
            resource_type="order",
            resource_id=order_id,
            response_body=command_view.model_dump(mode="json"),
        )
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            competing = await self.idempotency.find(scope_key=scope, operation=operation, key=key)
            if competing is None:
                raise
            replay_body = await self.idempotency.replay_response_body(
                scope_key=scope,
                operation=operation,
                key=key,
                request_hash=request_hash,
            )
            if replay_body is None:
                raise
            return OrderView.model_validate(replay_body), True
        return command_view, False

    async def _transition(
        self,
        context: TenantContext,
        order_id: uuid.UUID,
        *,
        target: str,
        reason: str,
        expected_version: int | None = None,
        commit: bool = True,
    ) -> None:
        found = await self.repository.get(context, order_id, for_update=True)
        if found is None:
            raise _not_found()
        order, _ = found
        if expected_version is not None:
            ensure_version(order.version, expected_version)
        if target == order.status:
            return
        if target not in ORDER_TRANSITIONS.get(order.status, frozenset()):
            raise AppError(
                status=409,
                code="invalid_state_transition",
                title="Order status transition is invalid",
                detail=f"An order cannot move from {order.status} to {target}.",
            )
        previous = order.status
        order.status = target
        order.version += 1
        self.db.add(
            OrderStatusEvent(
                id=uuid.uuid4(),
                organization_id=context.organization.id,
                order_id=order.id,
                changed_by_user_id=context.identity.user.id,
                from_status=previous,
                to_status=target,
                reason=reason,
                occurred_at=utc_now(),
            )
        )
        await self.db.flush()
        customer = await self.customers.get(
            context, order.customer_id, include_archived=True, for_update=True
        )
        if customer is not None:
            await self._refresh_customer(context, customer)
        await increment_data_revision(self.db, context.organization)
        if commit:
            await self.db.commit()

    async def _refresh_customer(self, context: TenantContext, customer: Customer) -> None:
        metrics = await self.customers.metrics(context, customer.id)
        customer.lifetime_value = metrics.spend
        customer.last_order_at = metrics.last_order_at
        if metrics.order_count == 0:
            customer.segment = "new"
            return
        recency = (
            (utc_now().date() - metrics.last_order_at.date()).days if metrics.last_order_at else 999
        )
        if recency > 180:
            customer.segment = "inactive"
        elif recency > 90:
            customer.segment = "at_risk"
        elif metrics.spend >= Decimal("5000.00") or metrics.order_count >= 10:
            customer.segment = "high_value"
        elif metrics.order_count >= 5:
            customer.segment = "loyal"
        elif metrics.order_count >= 2:
            customer.segment = "repeat"
        else:
            customer.segment = "new"
