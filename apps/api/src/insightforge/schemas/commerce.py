from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Self

from pydantic import EmailStr, Field, field_validator, model_validator

from insightforge.core.money import MAX_MONEY_MINOR
from insightforge.models.enums import CustomerStatus, OrderStatus, ProductStatus
from insightforge.schemas.analytics import AnalyticsRangeView
from insightforge.schemas.common import StrictSchema


class CustomerCreateRequest(StrictSchema):
    external_id: str | None = Field(default=None, max_length=120)
    name: str = Field(min_length=1, max_length=160)
    email: EmailStr | None = None
    company: str | None = Field(default=None, max_length=160)
    status: CustomerStatus = CustomerStatus.ACTIVE
    acquired_at: datetime | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Customer name cannot be blank.")
        return normalized

    @field_validator("acquired_at")
    @classmethod
    def require_aware_acquired_at(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("acquired_at must include a UTC offset.")
        return value


class CustomerUpdateRequest(StrictSchema):
    external_id: str | None = Field(default=None, max_length=120)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    email: EmailStr | None = None
    company: str | None = Field(default=None, max_length=160)
    status: CustomerStatus | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Customer name cannot be blank.")
        return normalized

    @model_validator(mode="after")
    def require_field(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Provide at least one customer field to update.")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Customer name cannot be null.")
        if "status" in self.model_fields_set and self.status is None:
            raise ValueError("Customer status cannot be null.")
        return self


class CustomerView(StrictSchema):
    id: uuid.UUID
    external_id: str | None
    name: str
    email: EmailStr | None
    company: str | None
    status: str
    segment: str
    acquired_at: datetime
    last_order_at: datetime | None
    total_spent_minor: int
    order_count: int
    version: int
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class CustomerMetricsView(StrictSchema):
    customer_id: uuid.UUID
    spend_minor: int
    order_count: int
    average_order_value_minor: int | None
    last_order_at: datetime | None
    recency_days: int | None


class ProductCreateRequest(StrictSchema):
    external_id: str | None = Field(default=None, max_length=120)
    sku: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=180)
    category: str = Field(min_length=1, max_length=100)
    unit_price_minor: int = Field(ge=0, le=MAX_MONEY_MINOR)

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Product SKU cannot be blank.")
        return normalized

    @field_validator("name", "category")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Product text fields cannot be blank.")
        return normalized


class ProductUpdateRequest(StrictSchema):
    external_id: str | None = Field(default=None, max_length=120)
    sku: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=180)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    unit_price_minor: int | None = Field(default=None, ge=0, le=MAX_MONEY_MINOR)
    status: ProductStatus | None = None

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Product SKU cannot be blank.")
        return normalized

    @field_validator("name", "category")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Product text fields cannot be blank.")
        return normalized

    @model_validator(mode="after")
    def require_field(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Provide at least one product field to update.")
        required_fields = {"sku", "name", "category", "unit_price_minor", "status"}
        if any(
            field in self.model_fields_set and getattr(self, field) is None
            for field in required_fields
        ):
            raise ValueError("Required product fields cannot be null.")
        return self


class ProductView(StrictSchema):
    id: uuid.UUID
    external_id: str | None
    sku: str
    name: str
    category: str
    unit_price_minor: int
    status: str
    units_sold: int
    revenue_minor: int
    average_price_minor: int | None
    version: int
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class ProductPeriodMetricsView(StrictSchema):
    units_sold: int
    eligible_revenue_minor: int
    average_selling_price_minor: int | None
    order_count: int


class ProductTrendPointView(StrictSchema):
    period_start: date
    units_sold: int
    eligible_revenue_minor: int


class ProductMetricsView(StrictSchema):
    product_id: uuid.UUID
    currency: str
    range: AnalyticsRangeView
    comparison_range: AnalyticsRangeView
    current: ProductPeriodMetricsView
    previous: ProductPeriodMetricsView
    units_change_percent: float | None
    revenue_change_percent: float | None
    trend: list[ProductTrendPointView]


class OrderItemCreateRequest(StrictSchema):
    product_id: uuid.UUID
    quantity: int = Field(ge=1, le=10_000)
    discount_minor: int = Field(default=0, ge=0, le=MAX_MONEY_MINOR)


class OrderCreateRequest(StrictSchema):
    customer_id: uuid.UUID
    external_id: str | None = Field(default=None, max_length=120)
    order_number: str = Field(min_length=1, max_length=80)
    ordered_at: datetime | None = None
    status: OrderStatus = OrderStatus.PENDING
    discount_minor: int = Field(default=0, ge=0, le=MAX_MONEY_MINOR)
    tax_minor: int = Field(default=0, ge=0, le=MAX_MONEY_MINOR)
    items: list[OrderItemCreateRequest] = Field(min_length=1, max_length=100)

    @field_validator("order_number")
    @classmethod
    def normalize_order_number(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Order number cannot be blank.")
        return normalized

    @field_validator("ordered_at")
    @classmethod
    def require_aware_ordered_at(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("ordered_at must include a UTC offset.")
        return value

    @model_validator(mode="after")
    def unique_products(self) -> Self:
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Each product may appear only once in an order.")
        if self.status not in {OrderStatus.PENDING, OrderStatus.PAID}:
            raise ValueError("New orders may start only as pending or paid.")
        return self


class OrderUpdateRequest(StrictSchema):
    status: OrderStatus


class OrderCommandRequest(StrictSchema):
    reason: str = Field(min_length=3, max_length=500)


class OrderItemView(StrictSchema):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    sku: str
    quantity: int
    unit_price_minor: int
    discount_minor: int
    line_total_minor: int


class OrderStatusEventView(StrictSchema):
    id: uuid.UUID
    from_status: str | None
    to_status: str
    reason: str | None
    changed_by_user_id: uuid.UUID | None
    occurred_at: datetime


class CustomerReferenceView(StrictSchema):
    id: uuid.UUID
    name: str
    email: EmailStr | None


class OrderView(StrictSchema):
    id: uuid.UUID
    external_id: str | None
    order_number: str
    status: str
    ordered_at: datetime
    subtotal_minor: int
    discount_minor: int
    tax_minor: int
    total_minor: int
    currency: str
    source: str
    customer: CustomerReferenceView
    item_count: int
    items: list[OrderItemView] | None = None
    status_history: list[OrderStatusEventView] | None = None
    version: int
    created_at: datetime
    updated_at: datetime
