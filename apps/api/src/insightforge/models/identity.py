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
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from insightforge.core.time import utc_now
from insightforge.db.base import Base
from insightforge.models._types import TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin
from insightforge.models.enums import (
    AccountActionKind,
    IdempotencyState,
    OnboardingState,
    OrganizationRole,
    OrganizationStatus,
    UserStatus,
)


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'invited', 'disabled')", name="status_allowed"),
    )

    email: Mapped[str] = mapped_column(CITEXT(), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), default=UserStatus.ACTIVE.value, server_default=UserStatus.ACTIVE.value
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locale: Mapped[str] = mapped_column(String(16), default="en-US", server_default="en-US")
    time_zone: Mapped[str] = mapped_column(String(64), default="UTC", server_default="UTC")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    weekly_summary_email: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )
    insight_alert_email: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )
    product_updates_email: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    compact_tables: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class UserSession(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "user_sessions"
    __table_args__ = (
        CheckConstraint("idle_expires_at <= absolute_expires_at", name="expiry_order"),
        Index("ix_user_sessions_user_expiry", "user_id", "absolute_expires_at"),
        Index(
            "ix_user_sessions_active_expiry",
            "idle_expires_at",
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(CHAR(64), unique=True, nullable=False)
    csrf_token_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    idle_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_prefix_hash: Mapped[str | None] = mapped_column(CHAR(64))
    user_agent_hash: Mapped[str | None] = mapped_column(CHAR(64))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=text("CURRENT_TIMESTAMP")
    )


class AccountActionToken(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "account_action_tokens"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('password_reset', 'email_verification', 'email_change')",
            name="purpose_allowed",
        ),
        CheckConstraint("attempts >= 0 AND attempts <= 10", name="attempts_bounded"),
        CheckConstraint(
            "(purpose = 'email_change' AND pending_email IS NOT NULL) OR "
            "(purpose <> 'email_change' AND pending_email IS NULL)",
            name="pending_email_consistent",
        ),
        Index("ix_account_action_tokens_user_expiry", "user_id", "purpose", "expires_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    token_hash: Mapped[str] = mapped_column(CHAR(64), unique=True, nullable=False)
    pending_email: Mapped[str | None] = mapped_column(CITEXT())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=text("CURRENT_TIMESTAMP")
    )

    @property
    def is_password_reset(self) -> bool:
        return self.purpose == AccountActionKind.PASSWORD_RESET.value


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'suspended', 'pending_deletion')", name="status_allowed"
        ),
        CheckConstraint(
            "onboarding_state IN ('organization', 'data', 'complete')",
            name="onboarding_state_allowed",
        ),
        CheckConstraint(
            "demo_status IS NULL OR demo_status IN ('preparing', 'ready', 'resetting', 'expired')",
            name="demo_status_allowed",
        ),
        CheckConstraint("data_revision >= 0", name="data_revision_non_negative"),
        CheckConstraint("demo_generation >= 0", name="demo_generation_non_negative"),
        CheckConstraint("slug = lower(slug)", name="slug_lowercase"),
        CheckConstraint("reporting_currency ~ '^[A-Z]{3}$'", name="reporting_currency_format"),
        CheckConstraint(
            "(is_demo = true AND demo_expires_at IS NOT NULL AND demo_status IS NOT NULL) OR "
            "(is_demo = false AND demo_expires_at IS NULL AND demo_status IS NULL)",
            name="demo_fields_consistent",
        ),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    reporting_currency: Mapped[str] = mapped_column(CHAR(3), default="USD", server_default="USD")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", server_default="UTC")
    industry: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(
        String(24), default=OrganizationStatus.ACTIVE.value, server_default="active"
    )
    onboarding_state: Mapped[str] = mapped_column(
        String(24), default=OnboardingState.ORGANIZATION.value, server_default="organization"
    )
    data_revision: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    demo_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    demo_generation: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    demo_status: Mapped[str | None] = mapped_column(String(24))


class OrganizationMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_organization_members_tenant_id"),
        UniqueConstraint("organization_id", "user_id", name="uq_organization_members_org_user"),
        CheckConstraint("role IN ('owner', 'admin', 'member')", name="role_allowed"),
        Index("ix_organization_members_user_active", "user_id", "removed_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(16), default=OrganizationRole.MEMBER.value, nullable=False
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=text("CURRENT_TIMESTAMP")
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OrganizationInvitation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "organization_invitations"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_organization_invitations_tenant_id"),
        CheckConstraint("role IN ('admin', 'member')", name="role_allowed"),
        Index(
            "uq_organization_invitations_active_email",
            "organization_id",
            "email",
            unique=True,
            postgresql_where=text("accepted_at IS NULL AND revoked_at IS NULL"),
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(CITEXT(), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    token_hash: Mapped[str] = mapped_column(CHAR(64), unique=True, nullable=False)
    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=text("CURRENT_TIMESTAMP")
    )


class IdempotencyRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "scope_key",
            "operation",
            "idempotency_key",
            name="uq_idempotency_records_scope_operation_key",
        ),
        CheckConstraint("state IN ('processing', 'completed', 'failed')", name="state_allowed"),
        CheckConstraint(
            "response_status IS NULL OR (response_status >= 100 AND response_status <= 599)",
            name="response_status_valid",
        ),
        CheckConstraint("expires_at >= created_at + interval '24 hours'", name="retention_minimum"),
        Index("ix_idempotency_records_expiry", "expires_at"),
        Index("ix_idempotency_records_actor_created", "actor_user_id", "created_at"),
    )

    scope_key: Mapped[str] = mapped_column(String(120), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    operation: Mapped[str] = mapped_column(String(120), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    state: Mapped[str] = mapped_column(
        String(24), default=IdempotencyState.PROCESSING.value, server_default="processing"
    )
    response_status: Mapped[int | None] = mapped_column(SmallInteger)
    response_body: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    resource_type: Mapped[str | None] = mapped_column(String(80))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
