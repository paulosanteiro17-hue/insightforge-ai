from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.analytics.ranges import EffectiveAnalyticsRange
from insightforge.core.concurrency import ensure_version
from insightforge.core.database_errors import integrity_constraint_name
from insightforge.core.money import decimal_to_minor, minor_to_decimal
from insightforge.core.pagination import PageResult, SortField, parse_sort
from insightforge.core.problems import AppError
from insightforge.core.revisions import increment_data_revision
from insightforge.core.time import utc_now
from insightforge.models import Product
from insightforge.models.enums import ProductStatus
from insightforge.repositories.commerce import ProductPeriodMetrics, ProductRepository, ProductRow
from insightforge.schemas.analytics import AnalyticsRangeView
from insightforge.schemas.commerce import (
    ProductCreateRequest,
    ProductMetricsView,
    ProductPeriodMetricsView,
    ProductTrendPointView,
    ProductUpdateRequest,
    ProductView,
)
from insightforge.services.commerce_common import _average_minor, _duplicate, _not_found

if TYPE_CHECKING:
    from insightforge.api.dependencies import TenantContext

PRODUCT_UNIQUE_CONSTRAINTS = {
    "uq_products_active_external_id",
    "uq_products_org_sku",
}


def product_view(row: ProductRow) -> ProductView:
    revenue_minor = decimal_to_minor(row.revenue)
    return ProductView(
        id=row.product.id,
        external_id=row.product.external_id,
        sku=row.product.sku,
        name=row.product.name,
        category=row.product.category,
        unit_price_minor=decimal_to_minor(row.product.unit_price),
        status=row.product.status,
        units_sold=row.units_sold,
        revenue_minor=revenue_minor,
        average_price_minor=_average_minor(revenue_minor, row.units_sold),
        version=row.product.version,
        created_at=row.product.created_at,
        updated_at=row.product.updated_at,
        archived_at=row.product.deleted_at,
    )


def _product_period_view(metrics: ProductPeriodMetrics) -> ProductPeriodMetricsView:
    revenue_minor = decimal_to_minor(metrics.revenue)
    return ProductPeriodMetricsView(
        units_sold=metrics.units_sold,
        eligible_revenue_minor=revenue_minor,
        average_selling_price_minor=_average_minor(revenue_minor, metrics.units_sold),
        order_count=metrics.order_count,
    )


def _percent_change(current: int, previous: int) -> float | None:
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 2)


class ProductService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = ProductRepository(db)

    async def list(
        self,
        context: TenantContext,
        *,
        page: int,
        page_size: int,
        sort_value: str | None,
        query: str | None,
        statuses: tuple[str, ...],
        categories: tuple[str, ...],
    ) -> PageResult[ProductView]:
        sort = parse_sort(
            sort_value,
            allowed=frozenset({"name", "units_sold", "revenue", "average_price", "created_at"}),
            default=(SortField("created_at", True),),
        )
        page_result = await self.repository.list(
            context,
            page=page,
            page_size=page_size,
            sort=sort,
            query=query.strip() if query else None,
            statuses=statuses,
            categories=categories,
        )
        return PageResult(
            [product_view(row) for row in page_result.items],
            page,
            page_size,
            page_result.total,
        )

    async def get(self, context: TenantContext, product_id: uuid.UUID) -> ProductView:
        row = await self.repository.metrics(context, product_id)
        if row is None:
            raise _not_found()
        return product_view(row)

    async def performance_metrics(
        self,
        context: TenantContext,
        product_id: uuid.UUID,
        effective_range: EffectiveAnalyticsRange,
    ) -> ProductMetricsView:
        comparison = effective_range.comparison
        if comparison is None:
            raise AppError(
                status=422,
                code="validation_error",
                title="Request validation failed",
                detail="Product metrics require a previous-period comparison.",
            )
        performance = await self.repository.performance(
            context,
            product_id,
            current_start=effective_range.current.start,
            current_end=effective_range.current.end,
            comparison_start=comparison.start,
            comparison_end=comparison.end,
            granularity=effective_range.granularity,
        )
        if performance is None:
            raise _not_found()
        current = _product_period_view(performance.current)
        previous = _product_period_view(performance.previous)
        return ProductMetricsView(
            product_id=product_id,
            currency=context.organization.reporting_currency,
            range=AnalyticsRangeView(
                start=effective_range.current.start,
                end=effective_range.current.end,
            ),
            comparison_range=AnalyticsRangeView(
                start=comparison.start,
                end=comparison.end,
            ),
            current=current,
            previous=previous,
            units_change_percent=_percent_change(current.units_sold, previous.units_sold),
            revenue_change_percent=_percent_change(
                current.eligible_revenue_minor,
                previous.eligible_revenue_minor,
            ),
            trend=[
                ProductTrendPointView(
                    period_start=point.period_start.date(),
                    units_sold=point.units_sold,
                    eligible_revenue_minor=decimal_to_minor(point.revenue),
                )
                for point in performance.trend
            ],
        )

    async def create(self, context: TenantContext, payload: ProductCreateRequest) -> ProductView:
        product = Product(
            id=uuid.uuid4(),
            organization_id=context.organization.id,
            external_id=payload.external_id,
            sku=payload.sku,
            name=payload.name,
            category=payload.category,
            unit_price=minor_to_decimal(payload.unit_price_minor),
            status="active",
        )
        self.db.add(product)
        await increment_data_revision(self.db, context.organization)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            if integrity_constraint_name(exc) in PRODUCT_UNIQUE_CONSTRAINTS:
                raise _duplicate("A product with this SKU or external ID already exists.") from exc
            raise
        return product_view(ProductRow(product, 0, Decimal("0.00")))

    async def update(
        self,
        context: TenantContext,
        product_id: uuid.UUID,
        payload: ProductUpdateRequest,
        expected_version: int,
    ) -> ProductView:
        product = await self.repository.get(context, product_id, for_update=True)
        if product is None:
            raise _not_found()
        ensure_version(product.version, expected_version)
        fields = payload.model_fields_set
        if "external_id" in fields:
            product.external_id = payload.external_id
        if "sku" in fields and payload.sku is not None:
            product.sku = payload.sku
        if "name" in fields and payload.name is not None:
            product.name = " ".join(payload.name.split())
        if "category" in fields and payload.category is not None:
            product.category = " ".join(payload.category.split())
        if "unit_price_minor" in fields and payload.unit_price_minor is not None:
            product.unit_price = minor_to_decimal(payload.unit_price_minor)
        if "status" in fields and payload.status is not None:
            product.status = payload.status.value
            product.deleted_at = utc_now() if payload.status == ProductStatus.ARCHIVED else None
        product.version += 1
        await increment_data_revision(self.db, context.organization)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            if integrity_constraint_name(exc) in PRODUCT_UNIQUE_CONSTRAINTS:
                raise _duplicate("A product with this SKU or external ID already exists.") from exc
            raise
        row = await self.repository.metrics(context, product_id)
        if row is None:
            raise _not_found()
        return product_view(row)

    async def archive(
        self, context: TenantContext, product_id: uuid.UUID, expected_version: int
    ) -> None:
        product = await self.repository.get(context, product_id, for_update=True)
        if product is None:
            raise _not_found()
        if product.status == ProductStatus.ARCHIVED.value:
            return
        ensure_version(product.version, expected_version)
        product.status = ProductStatus.ARCHIVED.value
        product.deleted_at = utc_now()
        product.version += 1
        await increment_data_revision(self.db, context.organization)
        await self.db.commit()
