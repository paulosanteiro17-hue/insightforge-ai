from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Query, Response, status

from insightforge.analytics.ranges import EffectiveAnalyticsRange, resolve_analytics_range
from insightforge.api.dependencies import (
    TenantContext,
    TenantContextDependency,
    get_product_service,
    require_csrf,
    require_permission,
)
from insightforge.core.concurrency import require_if_match, version_etag
from insightforge.core.policies import Permission
from insightforge.core.time import utc_now
from insightforge.models.enums import ProductStatus
from insightforge.schemas.commerce import (
    ProductCreateRequest,
    ProductMetricsView,
    ProductUpdateRequest,
    ProductView,
)
from insightforge.schemas.common import (
    CollectionEnvelope,
    CollectionMeta,
    DataEnvelope,
    PaginationView,
)
from insightforge.services.commerce import ProductService

router = APIRouter(prefix="/products", tags=["Products"])
ProductServiceDependency = Annotated[ProductService, Depends(get_product_service)]
WriteContext = Annotated[
    TenantContext,
    require_permission(Permission.MANAGE_BUSINESS_DATA),
]


def product_metrics_range(
    context: TenantContextDependency,
    range_value: Annotated[
        Literal["7d", "30d", "90d", "year_to_date"],
        Query(alias="range"),
    ] = "30d",
) -> EffectiveAnalyticsRange:
    return resolve_analytics_range(
        preset=range_value,
        compare="previous_period",
        requested_granularity=None,
        date_from=None,
        date_to=None,
        time_zone=context.organization.timezone,
        now=utc_now(),
    )


ProductMetricsRangeDependency = Annotated[
    EffectiveAnalyticsRange,
    Depends(product_metrics_range),
]


@router.get("", response_model=CollectionEnvelope[ProductView])
async def list_products(
    context: TenantContextDependency,
    service: ProductServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    sort: str | None = None,
    query: Annotated[str | None, Query(alias="q", max_length=180)] = None,
    product_status: Annotated[list[ProductStatus] | None, Query(alias="status")] = None,
    category: Annotated[list[str] | None, Query()] = None,
) -> CollectionEnvelope[ProductView]:
    result = await service.list(
        context,
        page=page,
        page_size=page_size,
        sort_value=sort,
        query=query,
        statuses=tuple(value.value for value in product_status or []),
        categories=tuple(category or []),
    )
    return CollectionEnvelope(
        data=result.items,
        meta=CollectionMeta(
            pagination=PaginationView.from_values(
                page=result.page,
                page_size=result.page_size,
                total=result.total,
            ),
            filters={
                "q": query,
                "status": [value.value for value in product_status or []],
                "category": category or [],
            },
        ),
    )


@router.post(
    "",
    response_model=DataEnvelope[ProductView],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_product(
    payload: ProductCreateRequest,
    response: Response,
    context: WriteContext,
    service: ProductServiceDependency,
) -> DataEnvelope[ProductView]:
    product = await service.create(context, payload)
    response.headers["Location"] = f"/api/v1/products/{product.id}"
    response.headers["ETag"] = version_etag(product.version)
    return DataEnvelope(data=product)


@router.get("/{product_id}", response_model=DataEnvelope[ProductView])
async def get_product(
    product_id: uuid.UUID,
    response: Response,
    context: TenantContextDependency,
    service: ProductServiceDependency,
) -> DataEnvelope[ProductView]:
    product = await service.get(context, product_id)
    response.headers["ETag"] = version_etag(product.version)
    return DataEnvelope(data=product)


@router.get("/{product_id}/metrics", response_model=DataEnvelope[ProductMetricsView])
async def get_product_metrics(
    product_id: uuid.UUID,
    context: TenantContextDependency,
    service: ProductServiceDependency,
    effective_range: ProductMetricsRangeDependency,
) -> DataEnvelope[ProductMetricsView]:
    return DataEnvelope(
        data=await service.performance_metrics(context, product_id, effective_range)
    )


@router.patch(
    "/{product_id}",
    response_model=DataEnvelope[ProductView],
    dependencies=[Depends(require_csrf)],
)
async def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdateRequest,
    response: Response,
    context: WriteContext,
    service: ProductServiceDependency,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> DataEnvelope[ProductView]:
    product = await service.update(
        context,
        product_id,
        payload,
        require_if_match(if_match),
    )
    response.headers["ETag"] = version_etag(product.version)
    return DataEnvelope(data=product)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def archive_product(
    product_id: uuid.UUID,
    context: WriteContext,
    service: ProductServiceDependency,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> Response:
    await service.archive(context, product_id, require_if_match(if_match))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
