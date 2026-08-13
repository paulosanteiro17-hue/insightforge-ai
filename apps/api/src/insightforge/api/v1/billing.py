from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response, status

from insightforge.api.dependencies import (
    RequestIdDependency,
    TenantContext,
    get_billing_service,
    require_csrf,
    require_permission,
)
from insightforge.core.policies import Permission
from insightforge.schemas.billing import (
    BillingIntentView,
    InvoiceView,
    PlanView,
    SubscriptionView,
    UpgradeIntentRequest,
)
from insightforge.schemas.common import (
    CollectionEnvelope,
    CollectionMeta,
    DataEnvelope,
    PaginationView,
)
from insightforge.services.billing import BillingService, public_plans

router = APIRouter(prefix="/billing", tags=["Billing"])
BillingServiceDependency = Annotated[BillingService, Depends(get_billing_service)]
BillingContext = Annotated[TenantContext, require_permission(Permission.MANAGE_BILLING)]


@router.get("/plans", response_model=DataEnvelope[list[PlanView]])
async def list_plans(response: Response) -> DataEnvelope[list[PlanView]]:
    response.headers["Cache-Control"] = "public, max-age=3600"
    return DataEnvelope(data=public_plans())


@router.get("/subscription", response_model=DataEnvelope[SubscriptionView])
async def get_subscription(
    context: BillingContext,
    service: BillingServiceDependency,
) -> DataEnvelope[SubscriptionView]:
    return DataEnvelope(data=await service.subscription_view(context.organization.id))


@router.get("/invoices", response_model=CollectionEnvelope[InvoiceView])
async def list_invoices(
    context: BillingContext,
    service: BillingServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> CollectionEnvelope[InvoiceView]:
    result = await service.invoices(
        context.organization.id,
        page=page,
        page_size=page_size,
    )
    return CollectionEnvelope(
        data=result.items,
        meta=CollectionMeta(
            pagination=PaginationView.from_values(
                page=result.page,
                page_size=result.page_size,
                total=result.total,
            ),
            filters={},
        ),
    )


@router.post(
    "/upgrade-intents",
    response_model=DataEnvelope[BillingIntentView],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_upgrade_intent(
    payload: UpgradeIntentRequest,
    response: Response,
    context: BillingContext,
    service: BillingServiceDependency,
    request_id: RequestIdDependency,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> DataEnvelope[BillingIntentView]:
    intent, replayed = await service.upgrade_intent(
        organization_id=context.organization.id,
        actor_user_id=context.identity.user.id,
        actor_is_demo=context.identity.session.is_demo,
        plan=payload.plan,
        request_id=request_id,
        idempotency_key=idempotency_key,
    )
    response.headers["Idempotency-Replayed"] = "true" if replayed else "false"
    response.headers["Location"] = "/api/v1/billing/subscription"
    return DataEnvelope(data=intent)


@router.post(
    "/portal-intents",
    response_model=DataEnvelope[BillingIntentView],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_portal_intent(
    response: Response,
    context: BillingContext,
    service: BillingServiceDependency,
    request_id: RequestIdDependency,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> DataEnvelope[BillingIntentView]:
    intent, replayed = await service.portal_intent(
        organization_id=context.organization.id,
        actor_user_id=context.identity.user.id,
        actor_is_demo=context.identity.session.is_demo,
        request_id=request_id,
        idempotency_key=idempotency_key,
    )
    response.headers["Idempotency-Replayed"] = "true" if replayed else "false"
    response.headers["Location"] = "/api/v1/billing/subscription"
    return DataEnvelope(data=intent)
