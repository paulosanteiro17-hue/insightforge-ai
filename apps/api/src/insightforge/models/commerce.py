from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from insightforge.core.time import utc_now
from insightforge.db.base import Base
from insightforge.models._types import TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin
from insightforge.models.enums import CustomerSegment, CustomerStatus, OrderStatus, ProductStatus


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_customers_tenant_id"),
        CheckConstraint("status IN ('active', 'at_risk', 'inactive')", name="status_allowed"),
        CheckConstraint(
            "segment IN ('new', 'repeat', 'loyal', 'high_value', 'at_risk', 'inactive')",
            name="segment_allowed",
        ),
        CheckConstraint("lifetime_value >= 0", name="lifetime_value_non_negative"),
        Index(
            "uq_customers_active_external_id",
            "organization_id",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL AND deleted_at IS NULL"),
        ),
        Index(
            "uq_customers_active_email",
            "organization_id",
            "email",
            unique=True,
            postgresql_where=text("email IS NOT NULL AND deleted_at IS NULL"),
        ),
        Index("ix_customers_org_status", "organization_id", "status"),
        Index("ix_customers_org_segment", "organization_id", "segment"),
        Index("ix_customers_org_acquired", "organization_id", "acquired_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str | None] = mapped_column(CITEXT())
    company: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(
        String(24), default=CustomerStatus.ACTIVE.value, server_default="active"
    )
    segment: Mapped[str] = mapped_column(
        String(24), default=CustomerSegment.NEW.value, server_default="new"
    )
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_order_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lifetime_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00"), server_default="0.00"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Product(UUIDPrimaryKeyMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_products_tenant_id"),
        UniqueConstraint("organization_id", "sku", name="uq_products_org_sku"),
        CheckConstraint("status IN ('active', 'archived')", name="status_allowed"),
        CheckConstraint("unit_price >= 0", name="unit_price_non_negative"),
        Index(
            "uq_products_active_external_id",
            "organization_id",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL AND deleted_at IS NULL"),
        ),
        Index("ix_products_org_category", "organization_id", "category"),
        Index("ix_products_org_status", "organization_id", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String(120))
    sku: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), default=ProductStatus.ACTIVE.value, server_default="active"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Order(UUIDPrimaryKeyMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_orders_tenant_id"),
        UniqueConstraint("organization_id", "order_number", name="uq_orders_org_number"),
        ForeignKeyConstraint(
            ["organization_id", "customer_id"],
            ["customers.organization_id", "customers.id"],
            name="fk_orders_tenant_customer",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('pending', 'paid', 'processing', 'completed', 'cancelled', 'refunded')",
            name="status_allowed",
        ),
        CheckConstraint(
            "subtotal >= 0 AND discount >= 0 AND tax >= 0 AND total >= 0",
            name="money_non_negative",
        ),
        CheckConstraint("total = subtotal - discount + tax", name="total_consistent"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_format"),
        Index(
            "uq_orders_external_id",
            "organization_id",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
        Index("ix_orders_org_ordered", "organization_id", "ordered_at"),
        Index("ix_orders_org_status_ordered", "organization_id", "status", "ordered_at"),
        Index("ix_orders_org_customer_ordered", "organization_id", "customer_id", "ordered_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(120))
    order_number: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), default=OrderStatus.PENDING.value, server_default="pending"
    )
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00"), server_default="0.00"
    )
    tax: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00"), server_default="0.00"
    )
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    source: Mapped[str] = mapped_column(String(60), default="manual", server_default="manual")


class OrderItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "order_items"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_order_items_tenant_id"),
        ForeignKeyConstraint(
            ["organization_id", "order_id"],
            ["orders.organization_id", "orders.id"],
            name="fk_order_items_tenant_order",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "product_id"],
            ["products.organization_id", "products.id"],
            name="fk_order_items_tenant_product",
            ondelete="RESTRICT",
        ),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint(
            "unit_price >= 0 AND discount >= 0 AND line_total >= 0", name="money_non_negative"
        ),
        CheckConstraint(
            "line_total = (unit_price * quantity) - discount", name="line_total_consistent"
        ),
        Index("ix_order_items_org_order", "organization_id", "order_id"),
        Index("ix_order_items_org_product", "organization_id", "product_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    order_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    product_name: Mapped[str] = mapped_column(String(180), nullable=False)
    sku: Mapped[str] = mapped_column(String(80), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00"), server_default="0.00"
    )
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=text("CURRENT_TIMESTAMP")
    )


class OrderStatusEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "order_status_events"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_order_status_events_tenant_id"),
        ForeignKeyConstraint(
            ["organization_id", "order_id"],
            ["orders.organization_id", "orders.id"],
            name="fk_order_status_events_tenant_order",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "from_status IS NULL OR from_status IN "
            "('pending', 'paid', 'processing', 'completed', 'cancelled', 'refunded')",
            name="from_status_allowed",
        ),
        CheckConstraint(
            "to_status IN ('pending', 'paid', 'processing', 'completed', 'cancelled', 'refunded')",
            name="to_status_allowed",
        ),
        Index("ix_order_status_events_order", "organization_id", "order_id", "occurred_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    order_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    from_status: Mapped[str | None] = mapped_column(String(24))
    to_status: Mapped[str] = mapped_column(String(24), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=text("CURRENT_TIMESTAMP")
    )
