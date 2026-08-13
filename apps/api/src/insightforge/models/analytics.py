from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
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
from insightforge.models._types import UUIDPrimaryKeyMixin
from insightforge.models.enums import MetricGrain


class MetricObservation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "metric_observations"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_metric_observations_tenant_id"),
        UniqueConstraint(
            "organization_id",
            "metric_key",
            "observed_on",
            "dimensions_hash",
            name="uq_metric_observations_identity",
        ),
        ForeignKeyConstraint(
            ["organization_id", "source_import_id"],
            ["data_imports.organization_id", "data_imports.id"],
            name="fk_metric_observations_tenant_import",
        ),
        Index("ix_metric_observations_org_date", "organization_id", "observed_on"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    metric_key: Mapped[str] = mapped_column(String(80), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    value_numeric: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    dimensions: Mapped[dict[str, object]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    dimensions_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    source_import_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=text("CURRENT_TIMESTAMP")
    )


class MetricSnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "metric_snapshots"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_metric_snapshots_tenant_id"),
        UniqueConstraint(
            "organization_id",
            "cache_key",
            "source_revision",
            name="uq_metric_snapshots_cache_revision",
        ),
        CheckConstraint("grain IN ('day', 'week', 'month')", name="grain_allowed"),
        CheckConstraint("period_start < period_end", name="period_valid"),
        CheckConstraint("source_revision >= 0", name="source_revision_non_negative"),
        Index("ix_metric_snapshots_org_metric", "organization_id", "metric_key", "period_start"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    cache_key: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(80), nullable=False)
    grain: Mapped[str] = mapped_column(String(16), default=MetricGrain.DAY.value)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    source_revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=text("CURRENT_TIMESTAMP")
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AIInsight(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ai_insights"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_ai_insights_tenant_id"),
        CheckConstraint(
            "category IN ('growth', 'warning', 'opportunity', 'performance', 'anomaly')",
            name="category_allowed",
        ),
        CheckConstraint("severity IN ('info', 'low', 'medium', 'high')", name="severity_allowed"),
        CheckConstraint("status IN ('active', 'superseded', 'failed')", name="status_allowed"),
        CheckConstraint(
            "generation_mode IN ('deterministic', 'provider', 'fallback')",
            name="generation_mode_allowed",
        ),
        CheckConstraint("period_start < period_end", name="period_valid"),
        Index("ix_ai_insights_org_generated", "organization_id", "generated_at"),
        Index("ix_ai_insights_org_status", "organization_id", "status", "severity"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    supporting_metrics: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str | None] = mapped_column(String(80))
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    generation_mode: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="active", server_default="active")
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=text("CURRENT_TIMESTAMP")
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AssistantQuery(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assistant_queries"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_assistant_queries_tenant_id"),
        CheckConstraint(
            "answer_status IN ('answered', 'unsupported', 'insufficient_data', 'blocked')",
            name="answer_status_allowed",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="confidence_range",
        ),
        Index("ix_assistant_queries_org_user", "organization_id", "user_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    question_redacted: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str] = mapped_column(String(80), nullable=False)
    parameters: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    answer_status: Mapped[str] = mapped_column(String(24), nullable=False)
    applied_range: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    follow_ups: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    supporting_metrics: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=text("CURRENT_TIMESTAMP")
    )


class WeeklySummary(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "weekly_summaries"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_weekly_summaries_tenant_id"),
        UniqueConstraint("organization_id", "week_start", name="uq_weekly_summaries_week"),
        CheckConstraint("week_start < week_end", name="week_valid"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    metrics: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str | None] = mapped_column(String(80))
    generated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=text("CURRENT_TIMESTAMP")
    )
