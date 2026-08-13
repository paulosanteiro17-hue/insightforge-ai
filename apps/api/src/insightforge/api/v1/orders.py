from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response, status

from insightforge.api.dependencies import (
    TenantContext,
    TenantContextDependency,
    get_order_service,
    require_csrf,
    require_permission,
)
from insightforge.core.concurrency import require_if_match, version_etag
from insightforge.core.policies import Permission
from insightforge.models.enums import OrderStatus
from insightforge.schemas.commerce import (
    OrderCommandRequest,
    OrderCreateRequest,
    OrderUpdateRequest,
    OrderView,
)
from insightforge.schemas.common import (
    CollectionEnvelope,
    CollectionMeta,
    DataEnvelope,
    PaginationView,
)
from insightforge.services.commerce import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])
OrderServiceDependency = Annotated[OrderService, Depends(get_order_service)]
WriteContext = Annotated[
    TenantContext,
    require_permission(Permission.MANAGE_BUSINESS_DATA),
]


@router.get("", response_model=CollectionEnvelope[OrderView])
async def list_orders(
    context: TenantContextDependency,
    service: OrderServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    sort: str | None = None,
    query: Annotated[str | None, Query(alias="q", max_length=180)] = None,
    order_status: Annotated[list[OrderStatus] | None, Query(alias="status")] = None,
    customer_id: uuid.UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> CollectionEnvelope[OrderView]:
    result = await service.list(
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
                "customer_id": str(customer_id) if customer_id else None,
            },
        ),
    )


@router.post(
    "",
    response_model=DataEnvelope[OrderView],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_order(
    payload: OrderCreateRequest,
    response: Response,
    context: WriteContext,
    service: OrderServiceDependency,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> DataEnvelope[OrderView]:
    order, replayed = await service.create(context, payload, idempotency_key)
    response.headers["Location"] = f"/api/v1/orders/{order.id}"
    response.headers["ETag"] = version_etag(order.version)
    response.headers["Idempotency-Replayed"] = "true" if replayed else "false"
    return DataEnvelope(data=order)


@router.get("/{order_id}", response_model=DataEnvelope[OrderView])
async def get_order(
    order_id: uuid.UUID,
    response: Response,
    context: TenantContextDependency,
    service: OrderServiceDependency,
) -> DataEnvelope[OrderView]:
    order = await service.detail(context, order_id)
    response.headers["ETag"] = version_etag(order.version)
    return DataEnvelope(data=order)


@router.patch(
    "/{order_id}",
    response_model=DataEnvelope[OrderView],
    dependencies=[Depends(require_csrf)],
)
async def update_order(
    order_id: uuid.UUID,
    payload: OrderUpdateRequest,
    response: Response,
    context: WriteContext,
    service: OrderServiceDependency,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> DataEnvelope[OrderView]:
    order = await service.update_status(
        context,
        order_id,
        payload,
        require_if_match(if_match),
    )
    response.headers["ETag"] = version_etag(order.version)
    return DataEnvelope(data=order)


async def _run_command(
    *,
    order_id: uuid.UUID,
    payload: OrderCommandRequest,
    response: Response,
    context: TenantContext,
    service: OrderService,
    command: str,
    idempotency_key: str | None,
) -> DataEnvelope[OrderView]:
    order, replayed = await service.command(
        context,
        order_id,
        payload,
        command=command,
        idempotency_key=idempotency_key,
    )
    response.headers["ETag"] = version_etag(order.version)
    response.headers["Idempotency-Replayed"] = "true" if replayed else "false"
    return DataEnvelope(data=order)


@router.post(
    "/{order_id}/cancel",
    response_model=DataEnvelope[OrderView],
    dependencies=[Depends(require_csrf)],
)
async def cancel_order(
    order_id: uuid.UUID,
    payload: OrderCommandRequest,
    response: Response,
    context: WriteContext,
    service: OrderServiceDependency,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> DataEnvelope[OrderView]:
    return await _run_command(
        order_id=order_id,
        payload=payload,
        response=response,
        context=context,
        service=service,
        command="cancel",
        idempotency_key=idempotency_key,
    )


@router.post(
    "/{order_id}/refund",
    response_model=DataEnvelope[OrderView],
    dependencies=[Depends(require_csrf)],
)
async def refund_order(
    order_id: uuid.UUID,
    payload: OrderCommandRequest,
    response: Response,
    context: WriteContext,
    service: OrderServiceDependency,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> DataEnvelope[OrderView]:
    return await _run_command(
        order_id=order_id,
        payload=payload,
        response=response,
        context=context,
        service=service,
        command="refund",
        idempotency_key=idempotency_key,
    )
