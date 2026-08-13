from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from insightforge.schemas.common import StrictSchema


class PlanLimitsView(StrictSchema):
    members: int
    customers: int
    products: int
    orders: int


class PlanView(StrictSchema):
    id: Literal["free", "pro", "business"]
    name: str
    monthly_price_minor: int
    currency: str
    description: str
    features: list[str]
    limits: PlanLimitsView


class UsageMetricView(StrictSchema):
    used: int
    limit: int


class UsageView(StrictSchema):
    members: UsageMetricView
    customers: UsageMetricView
    products: UsageMetricView
    orders: UsageMetricView


class SubscriptionView(StrictSchema):
    plan: str
    status: str
    provider: str
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    usage: UsageView


class InvoiceView(StrictSchema):
    id: uuid.UUID
    number: str
    issued_at: datetime
    amount_minor: int
    currency: str
    status: Literal["paid"]
    hosted_url: str | None


class UpgradeIntentRequest(StrictSchema):
    plan: Literal["free", "pro", "business"]


class BillingIntentView(StrictSchema):
    id: uuid.UUID
    kind: Literal["upgrade", "portal"]
    status: Literal["completed"]
    mode: Literal["demo"]
    plan: str
    destination: str | None
    message: str
    created_at: datetime
