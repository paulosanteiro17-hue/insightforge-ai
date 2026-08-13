from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response, status

from insightforge.api.dependencies import (
    TenantContext,
    TenantContextDependency,
    get_customer_service,
    get_order_service,
    require_csrf,
    require_permission,
)
from insightforge.core.concurrency import require_if_match, version_etag
from insightforge.core.policies import Permission
from insightforge.models.enums import CustomerStatus, OrderStatus
from insightforge.schemas.commerce import (
    CustomerCreateRequest,
    CustomerMetricsView,
    CustomerUpdateRequest,
    CustomerView,
    OrderView,
)
from insightforge.schemas.common import (
    CollectionEnvelope,
    CollectionMeta,
    DataEnvelope,
    PaginationView,
)
from insightforge.services.commerce import CustomerService, OrderService

router = APIRouter(prefix="/customers", tags=["Customers"])
CustomerServiceDependency = Annotated[CustomerService, Depends(get_customer_service)]
OrderServiceDependency = Annotated[OrderService, Depends(get_order_service)]
WriteContext = Annotated[
    TenantContext,
    require_permission(Permission.MANAGE_BUSINESS_DATA),
]


@router.get("", response_model=CollectionEnvelope[CustomerView])
async def list_customers(
    context: TenantContextDependency,
    service: CustomerServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    sort: str | None = None,
    query: Annotated[str | None, Query(alias="q", max_length=160)] = None,
    customer_status: Annotated[list[CustomerStatus] | None, Query(alias="status")] = None,
    segment: Annotated[list[str] | None, Query()] = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    include_archived: bool = False,
) -> CollectionEnvelope[CustomerView]:
    result = await service.list(
        context,
        page=page,
        page_size=page_size,
        sort_value=sort,
        query=query,
        statuses=tuple(value.value for value in customer_status or []),
        segments=tuple(segment or []),
        created_from=created_from,
        created_to=created_to,
        include_archived=include_archived,
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
                "status": [value.value for value in customer_status or []],
                "segment": segment or [],
                "include_archived": include_archived,
            },
        ),
    )


@router.post(
    "",
    response_model=DataEnvelope[CustomerView],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_customer(
    payload: CustomerCreateRequest,
    response: Response,
    context: WriteContext,
    service: CustomerServiceDependency,
) -> DataEnvelope[CustomerView]:
    customer = await service.create(context, payload)
    response.headers["Location"] = f"/api/v1/customers/{customer.id}"
    response.headers["ETag"] = version_etag(customer.version)
    return DataEnvelope(data=customer)


@router.get("/{customer_id}", response_model=DataEnvelope[CustomerView])
async def get_customer(
    customer_id: uuid.UUID,
    response: Response,
    context: TenantContextDependency,
    service: CustomerServiceDependency,
) -> DataEnvelope[CustomerView]:
    customer = await service.get(context, customer_id)
    response.headers["ETag"] = version_etag(customer.version)
    return DataEnvelope(data=customer)


@router.get("/{customer_id}/metrics", response_model=DataEnvelope[CustomerMetricsView])
async def get_customer_metrics(
    customer_id: uuid.UUID,
    context: TenantContextDependency,
    service: CustomerServiceDependency,
) -> DataEnvelope[CustomerMetricsView]:
    return DataEnvelope(data=await service.metrics(context, customer_id))


@router.get("/{customer_id}/orders", response_model=CollectionEnvelope[OrderView])
async def list_customer_orders(
    customer_id: uuid.UUID,
    context: TenantContextDependency,
    customer_service: CustomerServiceDependency,
    order_service: OrderServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    sort: str | None = None,
    query: Annotated[str | None, Query(alias="q", max_length=180)] = None,
    order_status: Annotated[list[OrderStatus] | None, Query(alias="status")] = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> CollectionEnvelope[OrderView]:
    await customer_service.get(context, customer_id)
    result = await order_service.list(
        context,
        page=page,
        page_size=page_size,
        sort_value=sort,
        query=query,
        statuses=tuple(value.value for value in order_status or []),
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
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
                "status": [value.value for value in order_status or []],
                "customer_id": str(customer_id),
            },
        ),
    )


@router.patch(
    "/{customer_id}",
    response_model=DataEnvelope[CustomerView],
    dependencies=[Depends(require_csrf)],
)
async def update_customer(
    customer_id: uuid.UUID,
    payload: CustomerUpdateRequest,
    response: Response,
    context: WriteContext,
    service: CustomerServiceDependency,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> DataEnvelope[CustomerView]:
    customer = await service.update(
        context,
        customer_id,
        payload,
        require_if_match(if_match),
    )
    response.headers["ETag"] = version_etag(customer.version)
    return DataEnvelope(data=customer)


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def archive_customer(
    customer_id: uuid.UUID,
    context: WriteContext,
    service: CustomerServiceDependency,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> Response:
    await service.archive(context, customer_id, require_if_match(if_match))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
