from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.core.concurrency import ensure_version
from insightforge.core.database_errors import integrity_constraint_name
from insightforge.core.money import decimal_to_minor
from insightforge.core.pagination import PageResult, SortField, parse_sort, validate_time_range
from insightforge.core.revisions import increment_data_revision
from insightforge.core.time import utc_now
from insightforge.models import Customer
from insightforge.repositories.commerce import CustomerMetrics, CustomerRepository
from insightforge.schemas.commerce import (
    CustomerCreateRequest,
    CustomerMetricsView,
    CustomerUpdateRequest,
    CustomerView,
)
from insightforge.services.commerce_common import (
    _average_minor,
    _duplicate,
    _normalize_datetime,
    _not_found,
)

if TYPE_CHECKING:
    from insightforge.api.dependencies import TenantContext

CUSTOMER_UNIQUE_CONSTRAINTS = {
    "uq_customers_active_external_id",
    "uq_customers_active_email",
}


def customer_view(customer: Customer, metrics: CustomerMetrics) -> CustomerView:
    return CustomerView(
        id=customer.id,
        external_id=customer.external_id,
        name=customer.name,
        email=customer.email,
        company=customer.company,
        status=customer.status,
        segment=customer.segment,
        acquired_at=customer.acquired_at,
        last_order_at=metrics.last_order_at,
        total_spent_minor=decimal_to_minor(metrics.spend),
        order_count=metrics.order_count,
        version=customer.version,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
        archived_at=customer.deleted_at,
    )


class CustomerService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = CustomerRepository(db)

    async def list(
        self,
        context: TenantContext,
        *,
        page: int,
        page_size: int,
        sort_value: str | None,
        query: str | None,
        statuses: tuple[str, ...],
        segments: tuple[str, ...],
        created_from: datetime | None,
        created_to: datetime | None,
        include_archived: bool,
    ) -> PageResult[CustomerView]:
        validate_time_range(created_from, created_to)
        sort = parse_sort(
            sort_value,
            allowed=frozenset({"name", "total_spent", "last_order_at", "created_at"}),
            default=(SortField("created_at", True),),
        )
        page_result = await self.repository.list(
            context,
            page=page,
            page_size=page_size,
            sort=sort,
            query=query.strip() if query else None,
            statuses=statuses,
            segments=segments,
            created_from=created_from,
            created_to=created_to,
            include_archived=include_archived,
        )
        views = []
        for row in page_result.items:
            views.append(
                customer_view(
                    row.customer,
                    CustomerMetrics(
                        spend=row.customer.lifetime_value,
                        order_count=row.order_count,
                        last_order_at=row.customer.last_order_at,
                    ),
                )
            )
        return PageResult(views, page, page_size, page_result.total)

    async def get(self, context: TenantContext, customer_id: uuid.UUID) -> CustomerView:
        customer = await self.repository.get(context, customer_id)
        if customer is None:
            raise _not_found()
        metrics = await self.repository.metrics(context, customer_id)
        return customer_view(customer, metrics)

    async def metrics(self, context: TenantContext, customer_id: uuid.UUID) -> CustomerMetricsView:
        customer = await self.repository.get(context, customer_id)
        if customer is None:
            raise _not_found()
        metrics = await self.repository.metrics(context, customer_id)
        spend_minor = decimal_to_minor(metrics.spend)
        recency = (
            max(0, (utc_now().date() - metrics.last_order_at.date()).days)
            if metrics.last_order_at
            else None
        )
        return CustomerMetricsView(
            customer_id=customer_id,
            spend_minor=spend_minor,
            order_count=metrics.order_count,
            average_order_value_minor=_average_minor(spend_minor, metrics.order_count),
            last_order_at=metrics.last_order_at,
            recency_days=recency,
        )

    async def create(self, context: TenantContext, payload: CustomerCreateRequest) -> CustomerView:
        customer = Customer(
            id=uuid.uuid4(),
            organization_id=context.organization.id,
            external_id=payload.external_id,
            name=payload.name,
            email=str(payload.email) if payload.email else None,
            company=payload.company,
            status=payload.status.value,
            segment="new",
            acquired_at=_normalize_datetime(payload.acquired_at),
        )
        self.db.add(customer)
        await increment_data_revision(self.db, context.organization)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            if integrity_constraint_name(exc) in CUSTOMER_UNIQUE_CONSTRAINTS:
                raise _duplicate(
                    "A customer with this email or external ID already exists."
                ) from exc
            raise
        return customer_view(customer, CustomerMetrics(Decimal("0.00"), 0, None))

    async def update(
        self,
        context: TenantContext,
        customer_id: uuid.UUID,
        payload: CustomerUpdateRequest,
        expected_version: int,
    ) -> CustomerView:
        customer = await self.repository.get(
            context, customer_id, include_archived=True, for_update=True
        )
        if customer is None:
            raise _not_found()
        ensure_version(customer.version, expected_version)
        fields = payload.model_fields_set
        if "external_id" in fields:
            customer.external_id = payload.external_id
        if "name" in fields and payload.name is not None:
            customer.name = " ".join(payload.name.split())
        if "email" in fields:
            customer.email = str(payload.email) if payload.email else None
        if "company" in fields:
            customer.company = payload.company
        if "status" in fields and payload.status is not None:
            customer.status = payload.status.value
        customer.version += 1
        await increment_data_revision(self.db, context.organization)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            if integrity_constraint_name(exc) in CUSTOMER_UNIQUE_CONSTRAINTS:
                raise _duplicate(
                    "A customer with this email or external ID already exists."
                ) from exc
            raise
        metrics = await self.repository.metrics(context, customer_id)
        return customer_view(customer, metrics)

    async def archive(
        self, context: TenantContext, customer_id: uuid.UUID, expected_version: int
    ) -> None:
        customer = await self.repository.get(
            context, customer_id, include_archived=True, for_update=True
        )
        if customer is None:
            raise _not_found()
        if customer.deleted_at is not None:
            return
        ensure_version(customer.version, expected_version)
        customer.deleted_at = utc_now()
        customer.status = "inactive"
        customer.version += 1
        await increment_data_revision(self.db, context.organization)
        await self.db.commit()
