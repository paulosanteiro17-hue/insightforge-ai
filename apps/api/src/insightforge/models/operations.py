from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from insightforge.core.time import utc_now
from insightforge.db.base import Base
from insightforge.models._types import TimestampMixin, UUIDPrimaryKeyMixin
from insightforge.models.enums import (
    BillingEventStatus,
    BillingProvider,
    ImportStatus,
    JobStatus,
    Plan,
    ReportStatus,
    SubscriptionStatus,
)


class DataImport(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "data_imports"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_data_imports_tenant_id"),
        CheckConstraint("kind IN ('customers', 'products', 'orders')", name="kind_allowed"),
        CheckConstraint(
            "status IN ('uploaded', 'validating', 'ready', 'importing', 'completed', "
            "'validation_failed', 'import_failed', 'cancelled', 'expired')",
            name="status_allowed",
        ),
        CheckConstraint("size_bytes >= 0", name="size_non_negative"),
        CheckConstraint(
            "total_rows >= 0 AND valid_rows >= 0 AND invalid_rows >= 0 AND imported_rows >= 0",
            name="row_counts_non_negative",
        ),
        Index("ix_data_imports_org_created", "organization_id", "created_at"),
        Index("ix_data_imports_org_status", "organization_id", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), default=ImportStatus.UPLOADED.value, server_default="uploaded"
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str | None] = mapped_column(Text)
    content_sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    template_version: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    mapping: Mapped[dict[str, object]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    total_rows: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    valid_rows: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    imported_rows: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    validation_summary: Mapped[dict[str, object]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=text("CURRENT_TIMESTAMP")
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DataImportError(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "data_import_errors"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_data_import_errors_tenant_id"),
        ForeignKeyConstraint(
            ["organization_id", "import_id"],
            ["data_imports.organization_id", "data_imports.id"],
            name="fk_data_import_errors_tenant_import",
            ondelete="CASCADE",
        ),
        CheckConstraint("row_number > 0", name="row_number_positive"),
        Index("ix_data_import_errors_import", "organization_id", "import_id", "row_number"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    import_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    column_name: Mapped[str | None] = mapped_column(String(120))
    error_code: Mapped[str] = mapped_column(String(80), nullable=False)
    safe_message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_value_excerpt: Mapped[str | None] = mapped_column(String(240))


class Report(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_reports_tenant_id"),
        CheckConstraint(
            "report_type IN ('monthly_performance', 'sales', 'customer', 'product_performance')",
            name="type_allowed",
        ),
        CheckConstraint(
            "status IN ('queued', 'generating', 'ready', 'failed', 'expired')",
            name="status_allowed",
        ),
        CheckConstraint("format IN ('json', 'csv')", name="format_allowed"),
        CheckConstraint("source_revision >= 0", name="source_revision_non_negative"),
        Index("ix_reports_org_created", "organization_id", "created_at"),
        Index("ix_reports_org_status", "organization_id", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    filters: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=ReportStatus.QUEUED.value, server_default="queued"
    )
    format: Mapped[str] = mapped_column(String(12), nullable=False)
    source_revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    result_summary: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    storage_key: Mapped[str | None] = mapped_column(Text)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_subscriptions_tenant_id"),
        UniqueConstraint("organization_id", name="uq_subscriptions_organization"),
        UniqueConstraint("provider_customer_id", name="uq_subscriptions_provider_customer"),
        UniqueConstraint("provider_subscription_id", name="uq_subscriptions_provider_subscription"),
        CheckConstraint("plan IN ('free', 'pro', 'business')", name="plan_allowed"),
        CheckConstraint(
            "status IN ('active', 'trialing', 'past_due', 'cancelled')", name="status_allowed"
        ),
        CheckConstraint("provider IN ('demo', 'stripe')", name="provider_allowed"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    plan: Mapped[str] = mapped_column(String(20), default=Plan.FREE.value, server_default="free")
    status: Mapped[str] = mapped_column(
        String(20), default=SubscriptionStatus.ACTIVE.value, server_default="active"
    )
    provider: Mapped[str] = mapped_column(
        String(20), default=BillingProvider.DEMO.value, server_default="demo"
    )
    provider_customer_id: Mapped[str | None] = mapped_column(Text)
    provider_subscription_id: Mapped[str | None] = mapped_column(Text)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )


class BillingEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "billing_events"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_billing_events_tenant_id"),
        UniqueConstraint("provider_event_id", name="uq_billing_events_provider_event"),
        ForeignKeyConstraint(
            ["organization_id", "subscription_id"],
            ["subscriptions.organization_id", "subscriptions.id"],
            name="fk_billing_events_tenant_subscription",
        ),
        CheckConstraint("status IN ('received', 'processed', 'failed')", name="status_allowed"),
        Index("ix_billing_events_org_received", "organization_id", "received_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    provider_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True))
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    payload_digest: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=BillingEventStatus.RECEIVED.value, server_default="received"
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=text("CURRENT_TIMESTAMP")
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint("actor_type IN ('user', 'system', 'demo')", name="actor_type_allowed"),
        Index("ix_audit_logs_org_occurred", "organization_id", "occurred_at"),
        Index("ix_audit_logs_actor_occurred", "actor_user_id", "occurred_at"),
        Index("ix_audit_logs_resource", "organization_id", "resource_type", "resource_id"),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL")
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(80))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True))
    request_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    safe_metadata: Mapped[dict[str, object]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=text("CURRENT_TIMESTAMP")
    )


class BackgroundJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "background_jobs"
    __table_args__ = (
        CheckConstraint("actor_type IN ('user', 'system', 'demo')", name="actor_type_allowed"),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="status_allowed",
        ),
        CheckConstraint("priority >= -100 AND priority <= 100", name="priority_bounded"),
        CheckConstraint(
            "attempt_count >= 0 AND max_attempts > 0 AND attempt_count <= max_attempts",
            name="attempts_bounded",
        ),
        CheckConstraint(
            "(locked_by IS NULL) = (locked_until IS NULL)", name="lease_fields_consistent"
        ),
        Index(
            "ix_background_jobs_claim",
            "status",
            "run_after",
            "priority",
            postgresql_where=text("status IN ('queued', 'running')"),
        ),
        Index("ix_background_jobs_org_created", "organization_id", "created_at"),
        Index("ix_background_jobs_idempotency", "idempotency_record_id"),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE")
    )
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    job_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    progress: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        default=lambda: {"current": 0, "total": None, "unit": "items"},
        server_default=text("jsonb_build_object('current', 0, 'total', NULL, 'unit', 'items')"),
    )
    status: Mapped[str] = mapped_column(
        String(24), default=JobStatus.QUEUED.value, server_default="queued"
    )
    priority: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    run_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=text("CURRENT_TIMESTAMP")
    )
    attempt_count: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(SmallInteger, default=5, server_default="5")
    locked_by: Mapped[str | None] = mapped_column(String(120))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_record_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("idempotency_records.id", ondelete="SET NULL")
    )
    trace_id: Mapped[str | None] = mapped_column(String(80))
    last_error_code: Mapped[str | None] = mapped_column(String(80))
    last_error_message: Mapped[str | None] = mapped_column(String(500))
    last_error_request_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
