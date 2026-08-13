from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.core.pagination import PageResult
from insightforge.core.problems import AppError
from insightforge.core.time import utc_now
from insightforge.models import (
    BillingEvent,
    Customer,
    Order,
    Organization,
    OrganizationMember,
    Product,
    Subscription,
)
from insightforge.models.enums import OrganizationRole
from insightforge.schemas.billing import (
    BillingIntentView,
    InvoiceView,
    PlanLimitsView,
    PlanView,
    SubscriptionView,
    UsageMetricView,
    UsageView,
)
from insightforge.services.auditing import add_audit_event
from insightforge.services.idempotency import (
    IdempotencyService,
    canonical_request_hash,
    validate_idempotency_key,
)

PlanId = Literal["free", "pro", "business"]

PLAN_LIMITS: dict[PlanId, dict[str, int]] = {
    "free": {"members": 3, "customers": 1_000, "products": 100, "orders": 5_000},
    "pro": {"members": 15, "customers": 25_000, "products": 2_000, "orders": 100_000},
    "business": {
        "members": 100,
        "customers": 250_000,
        "products": 20_000,
        "orders": 1_000_000,
    },
}
PLAN_PRICES: dict[PlanId, int] = {
    "free": 0,
    "pro": 4_900,
    "business": 14_900,
}


def public_plans() -> list[PlanView]:
    definitions: tuple[tuple[PlanId, str, str, list[str]], ...] = (
        (
            "free",
            "Free",
            "Essential analytics for a small workspace.",
            ["Core dashboards", "CSV imports", "Weekly business summary"],
        ),
        (
            "pro",
            "Pro",
            "Advanced analytics and AI workflows for growing teams.",
            ["Everything in Free", "AI insights", "Advanced reports", "Priority exports"],
        ),
        (
            "business",
            "Business",
            "Higher limits and administration controls for established teams.",
            ["Everything in Pro", "Expanded team limits", "Audit exports", "Priority support"],
        ),
    )
    return [
        PlanView(
            id=plan_id,
            name=name,
            monthly_price_minor=PLAN_PRICES[plan_id],
            currency="USD",
            description=description,
            features=features,
            limits=PlanLimitsView(**PLAN_LIMITS[plan_id]),
        )
        for plan_id, name, description, features in definitions
    ]


class BillingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.idempotency = IdempotencyService(db)

    async def subscription_view(self, organization_id: uuid.UUID) -> SubscriptionView:
        subscription = await self._subscription(organization_id)
        if subscription is None:
            raise self._not_found()
        return SubscriptionView(
            plan=subscription.plan,
            status=subscription.status,
            provider=subscription.provider,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
            usage=await self.usage(organization_id, subscription.plan),
        )

    async def usage(self, organization_id: uuid.UUID, plan: str | None = None) -> UsageView:
        if plan is None:
            subscription = await self._subscription(organization_id)
            if subscription is None:
                raise self._not_found()
            plan = subscription.plan
        limits = PLAN_LIMITS[cast(PlanId, plan)]
        members, customers, products, orders = await self._usage_counts(organization_id)
        return UsageView(
            members=UsageMetricView(used=members, limit=limits["members"]),
            customers=UsageMetricView(used=customers, limit=limits["customers"]),
            products=UsageMetricView(used=products, limit=limits["products"]),
            orders=UsageMetricView(used=orders, limit=limits["orders"]),
        )

    async def invoices(
        self,
        organization_id: uuid.UUID,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[InvoiceView]:
        subscription = await self._subscription(organization_id)
        if subscription is None:
            raise self._not_found()
        total = 0 if subscription.plan == "free" else 6
        reference = utc_now().astimezone(UTC)
        invoices: list[InvoiceView] = []
        for index in range(total):
            issued_at = self._month_start(reference, -index)
            invoice_id = uuid.uuid5(
                organization_id,
                f"demo-invoice:{subscription.plan}:{issued_at.year}-{issued_at.month:02d}",
            )
            invoices.append(
                InvoiceView(
                    id=invoice_id,
                    number=f"IF-{issued_at.year}{issued_at.month:02d}-{invoice_id.hex[:6].upper()}",
                    issued_at=issued_at,
                    amount_minor=PLAN_PRICES[cast(PlanId, subscription.plan)],
                    currency="USD",
                    status="paid",
                    hosted_url=None,
                )
            )
        start = (page - 1) * page_size
        return PageResult(
            items=invoices[start : start + page_size],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def upgrade_intent(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_is_demo: bool,
        plan: str,
        request_id: uuid.UUID,
        idempotency_key: str | None,
    ) -> tuple[BillingIntentView, bool]:
        _organization, _owner = await self._lock_owner(organization_id, actor_user_id)
        key = validate_idempotency_key(idempotency_key)
        request_hash = canonical_request_hash({"plan": plan})
        replay = await self.idempotency.replay_response_body(
            scope_key=f"organization:{organization_id}",
            operation="create_billing_upgrade_intent",
            key=key,
            request_hash=request_hash,
        )
        if replay is not None:
            return BillingIntentView.model_validate(replay), True
        subscription = await self.db.scalar(
            select(Subscription)
            .where(Subscription.organization_id == organization_id)
            .with_for_update()
        )
        if subscription is None:
            raise self._not_found()
        if subscription.provider != "demo":
            raise AppError(
                status=503,
                code="billing_provider_unavailable",
                title="Billing provider is unavailable",
                detail="Try again after billing service is restored.",
            )
        now = utc_now()
        intent_id = uuid.uuid4()
        view = BillingIntentView(
            id=intent_id,
            kind="upgrade",
            status="completed",
            mode="demo",
            plan=plan,
            destination=None,
            message="The simulated plan change was applied. No payment was collected.",
            created_at=now,
        )
        record = self.idempotency.start(
            scope_key=f"organization:{organization_id}",
            actor_user_id=actor_user_id,
            operation="create_billing_upgrade_intent",
            key=key,
            request_hash=request_hash,
        )
        subscription.plan = plan
        subscription.status = "active"
        subscription.current_period_start = now
        subscription.current_period_end = now + timedelta(days=30)
        subscription.cancel_at_period_end = False
        self.db.add(
            BillingEvent(
                id=intent_id,
                organization_id=organization_id,
                provider_event_id=f"demo-upgrade:{organization_id}:{intent_id}",
                subscription_id=subscription.id,
                event_type="demo.subscription.updated",
                payload_digest=canonical_request_hash(
                    {"organization_id": organization_id, "plan": plan, "intent_id": intent_id}
                ),
                status="processed",
                received_at=now,
                processed_at=now,
            )
        )
        response_body = cast(dict[str, object], view.model_dump(mode="json"))
        self.idempotency.complete(
            record,
            status_code=201,
            resource_type="billing_intent",
            resource_id=intent_id,
            response_body=response_body,
        )
        add_audit_event(
            self.db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            actor_is_demo=actor_is_demo,
            action="billing.subscription.updated",
            request_id=request_id,
            resource_type="subscription",
            resource_id=subscription.id,
            metadata={"plan": plan, "provider": "demo", "payment_collected": False},
        )
        await self.db.commit()
        return view, False

    async def portal_intent(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_is_demo: bool,
        request_id: uuid.UUID,
        idempotency_key: str | None,
    ) -> tuple[BillingIntentView, bool]:
        _organization, _owner = await self._lock_owner(organization_id, actor_user_id)
        key = validate_idempotency_key(idempotency_key)
        request_hash = canonical_request_hash({})
        replay = await self.idempotency.replay_response_body(
            scope_key=f"organization:{organization_id}",
            operation="create_billing_portal_intent",
            key=key,
            request_hash=request_hash,
        )
        if replay is not None:
            return BillingIntentView.model_validate(replay), True
        subscription = await self._subscription(organization_id, for_update=True)
        if subscription is None:
            raise self._not_found()
        if subscription.provider != "demo":
            raise AppError(
                status=503,
                code="billing_provider_unavailable",
                title="Billing provider is unavailable",
                detail="Try again after billing service is restored.",
            )
        now = utc_now()
        intent_id = uuid.uuid4()
        view = BillingIntentView(
            id=intent_id,
            kind="portal",
            status="completed",
            mode="demo",
            plan=subscription.plan,
            destination="/settings/billing",
            message="Billing is managed in the application while the demo adapter is active.",
            created_at=now,
        )
        record = self.idempotency.start(
            scope_key=f"organization:{organization_id}",
            actor_user_id=actor_user_id,
            operation="create_billing_portal_intent",
            key=key,
            request_hash=request_hash,
        )
        self.db.add(
            BillingEvent(
                id=intent_id,
                organization_id=organization_id,
                provider_event_id=f"demo-portal:{organization_id}:{intent_id}",
                subscription_id=subscription.id,
                event_type="demo.portal.opened",
                payload_digest=request_hash,
                status="processed",
                received_at=now,
                processed_at=now,
            )
        )
        response_body = cast(dict[str, object], view.model_dump(mode="json"))
        self.idempotency.complete(
            record,
            status_code=201,
            resource_type="billing_intent",
            resource_id=intent_id,
            response_body=response_body,
        )
        add_audit_event(
            self.db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            actor_is_demo=actor_is_demo,
            action="billing.portal.requested",
            request_id=request_id,
            resource_type="subscription",
            resource_id=subscription.id,
            metadata={"provider": "demo"},
        )
        await self.db.commit()
        return view, False

    async def _lock_owner(
        self, organization_id: uuid.UUID, actor_user_id: uuid.UUID
    ) -> tuple[Organization, OrganizationMember]:
        organization = await self.db.scalar(
            select(Organization).where(Organization.id == organization_id).with_for_update()
        )
        owner = await self.db.scalar(
            select(OrganizationMember)
            .where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == actor_user_id,
                OrganizationMember.removed_at.is_(None),
            )
            .with_for_update()
        )
        if organization is None or owner is None:
            raise self._not_found()
        if owner.role != OrganizationRole.OWNER.value:
            raise AppError(
                status=403,
                code="permission_denied",
                title="Permission denied",
                detail="Only an organization owner can manage billing.",
            )
        return organization, owner

    async def _subscription(
        self, organization_id: uuid.UUID, *, for_update: bool = False
    ) -> Subscription | None:
        statement = select(Subscription).where(Subscription.organization_id == organization_id)
        if for_update:
            statement = statement.with_for_update()
        return cast(Subscription | None, await self.db.scalar(statement))

    async def _usage_counts(self, organization_id: uuid.UUID) -> tuple[int, int, int, int]:
        members = int(
            await self.db.scalar(
                select(func.count())
                .select_from(OrganizationMember)
                .where(
                    OrganizationMember.organization_id == organization_id,
                    OrganizationMember.removed_at.is_(None),
                )
            )
            or 0
        )
        customers = int(
            await self.db.scalar(
                select(func.count())
                .select_from(Customer)
                .where(Customer.organization_id == organization_id, Customer.deleted_at.is_(None))
            )
            or 0
        )
        products = int(
            await self.db.scalar(
                select(func.count())
                .select_from(Product)
                .where(Product.organization_id == organization_id, Product.deleted_at.is_(None))
            )
            or 0
        )
        orders = int(
            await self.db.scalar(
                select(func.count())
                .select_from(Order)
                .where(Order.organization_id == organization_id)
            )
            or 0
        )
        return members, customers, products, orders

    @staticmethod
    def _month_start(reference: datetime, offset: int) -> datetime:
        ordinal = reference.year * 12 + reference.month - 1 + offset
        year, month = divmod(ordinal, 12)
        return datetime(year, month + 1, 1, tzinfo=UTC)

    @staticmethod
    def _not_found() -> AppError:
        return AppError(
            status=404,
            code="resource_not_found",
            title="Resource not found",
            detail="The requested resource was not found.",
        )
