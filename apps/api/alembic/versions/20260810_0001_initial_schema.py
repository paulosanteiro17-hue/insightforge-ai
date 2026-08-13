"""Create the initial InsightForge AI schema.

Revision ID: 20260810_0001
Revises: None
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# This revision is intentionally kept as a compact, frozen schema snapshot.
# fmt: off

revision: str = "20260810_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def uuid_column(name: str = "id", *, nullable: bool = False) -> sa.Column:
    return sa.Column(name, postgresql.UUID(as_uuid=True), nullable=nullable)


def created_at() -> sa.Column:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
    )


def updated_at() -> sa.Column:
    return sa.Column(
        "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
    )


def tenant_unique(table: str) -> sa.UniqueConstraint:
    return sa.UniqueConstraint("organization_id", "id", name=f"uq_{table}_tenant_id")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    op.create_table(
        "users",
        uuid_column(),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("status", sa.String(24), server_default="active", nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True)),
        sa.Column("locale", sa.String(16), server_default="en-US", nullable=False),
        sa.Column("time_zone", sa.String(64), server_default="UTC", nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        created_at(),
        updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint("status IN ('active', 'invited', 'disabled')", name="ck_users_status_allowed"),
    )
    op.create_table(
        "user_preferences",
        uuid_column("user_id"),
        sa.Column("weekly_summary_email", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("insight_alert_email", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("product_updates_email", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("compact_tables", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        updated_at(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_user_preferences_user_id_users"),
        sa.PrimaryKeyConstraint("user_id", name="pk_user_preferences"),
    )
    op.create_table(
        "user_sessions",
        uuid_column(),
        uuid_column("user_id"),
        sa.Column("token_hash", sa.CHAR(64), nullable=False),
        sa.Column("csrf_token_hash", sa.CHAR(64), nullable=False),
        sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("ip_prefix_hash", sa.CHAR(64)),
        sa.Column("user_agent_hash", sa.CHAR(64)),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        created_at(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_user_sessions_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_user_sessions"),
        sa.UniqueConstraint("token_hash", name="uq_user_sessions_token_hash"),
        sa.CheckConstraint("idle_expires_at <= absolute_expires_at", name="ck_user_sessions_expiry_order"),
    )
    op.create_index("ix_user_sessions_user_expiry", "user_sessions", ["user_id", "absolute_expires_at"])
    op.create_index(
        "ix_user_sessions_active_expiry",
        "user_sessions",
        ["idle_expires_at"],
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.create_table(
        "account_action_tokens",
        uuid_column(),
        uuid_column("user_id"),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("token_hash", sa.CHAR(64), nullable=False),
        sa.Column("pending_email", postgresql.CITEXT()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("attempts", sa.SmallInteger(), server_default="0", nullable=False),
        created_at(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_account_action_tokens_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_account_action_tokens"),
        sa.UniqueConstraint("token_hash", name="uq_account_action_tokens_token_hash"),
        sa.CheckConstraint(
            "purpose IN ('password_reset', 'email_verification', 'email_change')",
            name="ck_account_action_tokens_purpose_allowed",
        ),
        sa.CheckConstraint("attempts >= 0 AND attempts <= 10", name="ck_account_action_tokens_attempts_bounded"),
        sa.CheckConstraint("(purpose = 'email_change' AND pending_email IS NOT NULL) OR (purpose <> 'email_change' AND pending_email IS NULL)", name="ck_account_action_tokens_pending_email_consistent"),
    )
    op.create_index("ix_account_action_tokens_user_expiry", "account_action_tokens", ["user_id", "purpose", "expires_at"])
    op.create_table(
        "organizations",
        uuid_column(),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("reporting_currency", sa.CHAR(3), server_default="USD", nullable=False),
        sa.Column("timezone", sa.String(64), server_default="UTC", nullable=False),
        sa.Column("industry", sa.String(80)),
        sa.Column("status", sa.String(24), server_default="active", nullable=False),
        sa.Column("onboarding_state", sa.String(24), server_default="organization", nullable=False),
        sa.Column("data_revision", sa.BigInteger(), server_default="0", nullable=False),
        uuid_column("created_by_user_id"),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("demo_expires_at", sa.DateTime(timezone=True)),
        sa.Column("demo_generation", sa.Integer(), server_default="0", nullable=False),
        sa.Column("demo_status", sa.String(24)),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        created_at(),
        updated_at(),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT", name="fk_organizations_created_by_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
        sa.CheckConstraint("status IN ('active', 'suspended', 'pending_deletion')", name="ck_organizations_status_allowed"),
        sa.CheckConstraint("onboarding_state IN ('organization', 'data', 'complete')", name="ck_organizations_onboarding_state_allowed"),
        sa.CheckConstraint("demo_status IS NULL OR demo_status IN ('preparing', 'ready', 'resetting', 'expired')", name="ck_organizations_demo_status_allowed"),
        sa.CheckConstraint("data_revision >= 0", name="ck_organizations_data_revision_non_negative"),
        sa.CheckConstraint("demo_generation >= 0", name="ck_organizations_demo_generation_non_negative"),
        sa.CheckConstraint("slug = lower(slug)", name="ck_organizations_slug_lowercase"),
        sa.CheckConstraint("reporting_currency ~ '^[A-Z]{3}$'", name="ck_organizations_reporting_currency_format"),
        sa.CheckConstraint("(is_demo = true AND demo_expires_at IS NOT NULL AND demo_status IS NOT NULL) OR (is_demo = false AND demo_expires_at IS NULL AND demo_status IS NULL)", name="ck_organizations_demo_fields_consistent"),
    )
    op.create_table(
        "organization_members",
        uuid_column(),
        uuid_column("organization_id"),
        uuid_column("user_id"),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("removed_at", sa.DateTime(timezone=True)),
        created_at(),
        updated_at(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", name="fk_organization_members_organization_id_organizations"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_organization_members_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_organization_members"),
        tenant_unique("organization_members"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_organization_members_org_user"),
        sa.CheckConstraint("role IN ('owner', 'admin', 'member')", name="ck_organization_members_role_allowed"),
    )
    op.create_index("ix_organization_members_user_active", "organization_members", ["user_id", "removed_at"])
    op.create_table(
        "organization_invitations",
        uuid_column(),
        uuid_column("organization_id"),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("token_hash", sa.CHAR(64), nullable=False),
        uuid_column("invited_by_user_id"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        created_at(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", name="fk_organization_invitations_organization_id_organizations"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="RESTRICT", name="fk_organization_invitations_invited_by_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_organization_invitations"),
        tenant_unique("organization_invitations"),
        sa.UniqueConstraint("token_hash", name="uq_organization_invitations_token_hash"),
        sa.CheckConstraint("role IN ('admin', 'member')", name="ck_organization_invitations_role_allowed"),
    )
    op.create_index(
        "uq_organization_invitations_active_email",
        "organization_invitations",
        ["organization_id", "email"],
        unique=True,
        postgresql_where=sa.text("accepted_at IS NULL AND revoked_at IS NULL"),
    )
    op.create_table(
        "idempotency_records",
        uuid_column(),
        sa.Column("scope_key", sa.String(120), nullable=False),
        uuid_column("actor_user_id", nullable=True),
        sa.Column("operation", sa.String(120), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("request_hash", sa.CHAR(64), nullable=False),
        sa.Column("state", sa.String(24), server_default="processing", nullable=False),
        sa.Column("response_status", sa.SmallInteger()),
        sa.Column("response_body", postgresql.JSONB()),
        sa.Column("resource_type", sa.String(80)),
        uuid_column("resource_id", nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        created_at(),
        updated_at(),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL", name="fk_idempotency_records_actor_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_idempotency_records"),
        sa.UniqueConstraint("scope_key", "operation", "idempotency_key", name="uq_idempotency_records_scope_operation_key"),
        sa.CheckConstraint("state IN ('processing', 'completed', 'failed')", name="ck_idempotency_records_state_allowed"),
        sa.CheckConstraint("response_status IS NULL OR (response_status >= 100 AND response_status <= 599)", name="ck_idempotency_records_response_status_valid"),
        sa.CheckConstraint("expires_at >= created_at + interval '24 hours'", name="ck_idempotency_records_retention_minimum"),
    )
    op.create_index("ix_idempotency_records_expiry", "idempotency_records", ["expires_at"])
    op.create_index("ix_idempotency_records_actor_created", "idempotency_records", ["actor_user_id", "created_at"])

    op.create_table(
        "customers",
        uuid_column(),
        uuid_column("organization_id"),
        sa.Column("external_id", sa.String(120)),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("email", postgresql.CITEXT()),
        sa.Column("company", sa.String(160)),
        sa.Column("status", sa.String(24), server_default="active", nullable=False),
        sa.Column("segment", sa.String(24), server_default="new", nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_order_at", sa.DateTime(timezone=True)),
        sa.Column("lifetime_value", sa.Numeric(14, 2), server_default="0.00", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        created_at(),
        updated_at(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", name="fk_customers_organization_id_organizations"),
        sa.PrimaryKeyConstraint("id", name="pk_customers"),
        tenant_unique("customers"),
        sa.CheckConstraint("status IN ('active', 'at_risk', 'inactive')", name="ck_customers_status_allowed"),
        sa.CheckConstraint("segment IN ('new', 'repeat', 'loyal', 'high_value', 'at_risk', 'inactive')", name="ck_customers_segment_allowed"),
        sa.CheckConstraint("lifetime_value >= 0", name="ck_customers_lifetime_value_non_negative"),
    )
    op.create_index("uq_customers_active_external_id", "customers", ["organization_id", "external_id"], unique=True, postgresql_where=sa.text("external_id IS NOT NULL AND deleted_at IS NULL"))
    op.create_index("uq_customers_active_email", "customers", ["organization_id", "email"], unique=True, postgresql_where=sa.text("email IS NOT NULL AND deleted_at IS NULL"))
    op.create_index("ix_customers_org_status", "customers", ["organization_id", "status"])
    op.create_index("ix_customers_org_segment", "customers", ["organization_id", "segment"])
    op.create_index("ix_customers_org_acquired", "customers", ["organization_id", "acquired_at"])
    op.create_table(
        "products",
        uuid_column(),
        uuid_column("organization_id"),
        sa.Column("external_id", sa.String(120)),
        sa.Column("sku", sa.String(80), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", sa.String(24), server_default="active", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        created_at(),
        updated_at(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", name="fk_products_organization_id_organizations"),
        sa.PrimaryKeyConstraint("id", name="pk_products"),
        tenant_unique("products"),
        sa.UniqueConstraint("organization_id", "sku", name="uq_products_org_sku"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_products_status_allowed"),
        sa.CheckConstraint("unit_price >= 0", name="ck_products_unit_price_non_negative"),
    )
    op.create_index("uq_products_active_external_id", "products", ["organization_id", "external_id"], unique=True, postgresql_where=sa.text("external_id IS NOT NULL AND deleted_at IS NULL"))
    op.create_index("ix_products_org_category", "products", ["organization_id", "category"])
    op.create_index("ix_products_org_status", "products", ["organization_id", "status"])
    op.create_table(
        "orders",
        uuid_column(),
        uuid_column("organization_id"),
        uuid_column("customer_id"),
        sa.Column("external_id", sa.String(120)),
        sa.Column("order_number", sa.String(80), nullable=False),
        sa.Column("status", sa.String(24), server_default="pending", nullable=False),
        sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=False),
        sa.Column("discount", sa.Numeric(14, 2), server_default="0.00", nullable=False),
        sa.Column("tax", sa.Numeric(14, 2), server_default="0.00", nullable=False),
        sa.Column("total", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False),
        sa.Column("source", sa.String(60), server_default="manual", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        created_at(),
        updated_at(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", name="fk_orders_organization_id_organizations"),
        sa.ForeignKeyConstraint(["organization_id", "customer_id"], ["customers.organization_id", "customers.id"], ondelete="RESTRICT", name="fk_orders_tenant_customer"),
        sa.PrimaryKeyConstraint("id", name="pk_orders"),
        tenant_unique("orders"),
        sa.UniqueConstraint("organization_id", "order_number", name="uq_orders_org_number"),
        sa.CheckConstraint("status IN ('pending', 'paid', 'processing', 'completed', 'cancelled', 'refunded')", name="ck_orders_status_allowed"),
        sa.CheckConstraint("subtotal >= 0 AND discount >= 0 AND tax >= 0 AND total >= 0", name="ck_orders_money_non_negative"),
        sa.CheckConstraint("total = subtotal - discount + tax", name="ck_orders_total_consistent"),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name="ck_orders_currency_format"),
    )
    op.create_index("uq_orders_external_id", "orders", ["organization_id", "external_id"], unique=True, postgresql_where=sa.text("external_id IS NOT NULL"))
    op.create_index("ix_orders_org_ordered", "orders", ["organization_id", "ordered_at"])
    op.create_index("ix_orders_org_status_ordered", "orders", ["organization_id", "status", "ordered_at"])
    op.create_index("ix_orders_org_customer_ordered", "orders", ["organization_id", "customer_id", "ordered_at"])
    op.create_table(
        "order_items",
        uuid_column(),
        uuid_column("organization_id"),
        uuid_column("order_id"),
        uuid_column("product_id"),
        sa.Column("product_name", sa.String(180), nullable=False),
        sa.Column("sku", sa.String(80), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("discount", sa.Numeric(14, 2), server_default="0.00", nullable=False),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
        created_at(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", name="fk_order_items_organization_id_organizations"),
        sa.ForeignKeyConstraint(["organization_id", "order_id"], ["orders.organization_id", "orders.id"], ondelete="CASCADE", name="fk_order_items_tenant_order"),
        sa.ForeignKeyConstraint(["organization_id", "product_id"], ["products.organization_id", "products.id"], ondelete="RESTRICT", name="fk_order_items_tenant_product"),
        sa.PrimaryKeyConstraint("id", name="pk_order_items"),
        tenant_unique("order_items"),
        sa.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0 AND discount >= 0 AND line_total >= 0", name="ck_order_items_money_non_negative"),
        sa.CheckConstraint("line_total = (unit_price * quantity) - discount", name="ck_order_items_line_total_consistent"),
    )
    op.create_index("ix_order_items_org_order", "order_items", ["organization_id", "order_id"])
    op.create_index("ix_order_items_org_product", "order_items", ["organization_id", "product_id"])
    op.create_table(
        "order_status_events",
        uuid_column(),
        uuid_column("organization_id"),
        uuid_column("order_id"),
        uuid_column("changed_by_user_id", nullable=True),
        sa.Column("from_status", sa.String(24)),
        sa.Column("to_status", sa.String(24), nullable=False),
        sa.Column("reason", sa.String(500)),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", name="fk_order_status_events_organization_id_organizations"),
        sa.ForeignKeyConstraint(["organization_id", "order_id"], ["orders.organization_id", "orders.id"], ondelete="CASCADE", name="fk_order_status_events_tenant_order"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="SET NULL", name="fk_order_status_events_changed_by_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_order_status_events"),
        tenant_unique("order_status_events"),
        sa.CheckConstraint("from_status IS NULL OR from_status IN ('pending', 'paid', 'processing', 'completed', 'cancelled', 'refunded')", name="ck_order_status_events_from_status_allowed"),
        sa.CheckConstraint("to_status IN ('pending', 'paid', 'processing', 'completed', 'cancelled', 'refunded')", name="ck_order_status_events_to_status_allowed"),
    )
    op.create_index("ix_order_status_events_order", "order_status_events", ["organization_id", "order_id", "occurred_at"])

    _create_import_and_analytics_tables()
    _create_operations_tables()


def _create_import_and_analytics_tables() -> None:
    op.create_table(
        "data_imports",
        uuid_column(), uuid_column("organization_id"), uuid_column("requested_by_user_id"),
        sa.Column("kind", sa.String(20), nullable=False), sa.Column("status", sa.String(24), server_default="uploaded", nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False), sa.Column("storage_key", sa.Text()),
        sa.Column("content_sha256", sa.CHAR(64), nullable=False), sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("template_version", sa.SmallInteger(), nullable=False), sa.Column("mapping", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("total_rows", sa.Integer(), server_default="0", nullable=False), sa.Column("valid_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("invalid_rows", sa.Integer(), server_default="0", nullable=False), sa.Column("imported_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("validation_summary", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        created_at(), sa.Column("confirmed_at", sa.DateTime(timezone=True)), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", name="fk_data_imports_organization_id_organizations"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT", name="fk_data_imports_requested_by_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_data_imports"), tenant_unique("data_imports"),
        sa.CheckConstraint("kind IN ('customers', 'products', 'orders')", name="ck_data_imports_kind_allowed"),
        sa.CheckConstraint("status IN ('uploaded', 'validating', 'ready', 'importing', 'completed', 'validation_failed', 'import_failed', 'cancelled', 'expired')", name="ck_data_imports_status_allowed"),
        sa.CheckConstraint("size_bytes >= 0", name="ck_data_imports_size_non_negative"),
        sa.CheckConstraint("total_rows >= 0 AND valid_rows >= 0 AND invalid_rows >= 0 AND imported_rows >= 0", name="ck_data_imports_row_counts_non_negative"),
    )
    op.create_index("ix_data_imports_org_created", "data_imports", ["organization_id", "created_at"])
    op.create_index("ix_data_imports_org_status", "data_imports", ["organization_id", "status"])
    op.create_table(
        "data_import_errors",
        uuid_column(), uuid_column("organization_id"), uuid_column("import_id"),
        sa.Column("row_number", sa.Integer(), nullable=False), sa.Column("column_name", sa.String(120)),
        sa.Column("error_code", sa.String(80), nullable=False), sa.Column("safe_message", sa.Text(), nullable=False), sa.Column("raw_value_excerpt", sa.String(240)),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", name="fk_data_import_errors_organization_id_organizations"),
        sa.ForeignKeyConstraint(["organization_id", "import_id"], ["data_imports.organization_id", "data_imports.id"], ondelete="CASCADE", name="fk_data_import_errors_tenant_import"),
        sa.PrimaryKeyConstraint("id", name="pk_data_import_errors"), tenant_unique("data_import_errors"),
        sa.CheckConstraint("row_number > 0", name="ck_data_import_errors_row_number_positive"),
    )
    op.create_index("ix_data_import_errors_import", "data_import_errors", ["organization_id", "import_id", "row_number"])
    op.create_table(
        "metric_observations",
        uuid_column(), uuid_column("organization_id"), sa.Column("metric_key", sa.String(80), nullable=False),
        sa.Column("observed_on", sa.Date(), nullable=False), sa.Column("value_numeric", sa.Numeric(18, 4), nullable=False), sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("dimensions", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False), sa.Column("dimensions_hash", sa.CHAR(64), nullable=False),
        uuid_column("source_import_id", nullable=True), created_at(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", name="fk_metric_observations_organization_id_organizations"),
        sa.ForeignKeyConstraint(["organization_id", "source_import_id"], ["data_imports.organization_id", "data_imports.id"], name="fk_metric_observations_tenant_import"),
        sa.PrimaryKeyConstraint("id", name="pk_metric_observations"), tenant_unique("metric_observations"),
        sa.UniqueConstraint("organization_id", "metric_key", "observed_on", "dimensions_hash", name="uq_metric_observations_identity"),
    )
    op.create_index("ix_metric_observations_org_date", "metric_observations", ["organization_id", "observed_on"])
    op.create_table(
        "metric_snapshots",
        uuid_column(), uuid_column("organization_id"), sa.Column("cache_key", sa.CHAR(64), nullable=False), sa.Column("metric_key", sa.String(80), nullable=False),
        sa.Column("grain", sa.String(16), nullable=False), sa.Column("period_start", sa.Date(), nullable=False), sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False), sa.Column("source_revision", sa.BigInteger(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", name="fk_metric_snapshots_organization_id_organizations"),
        sa.PrimaryKeyConstraint("id", name="pk_metric_snapshots"), tenant_unique("metric_snapshots"),
        sa.UniqueConstraint("organization_id", "cache_key", "source_revision", name="uq_metric_snapshots_cache_revision"),
        sa.CheckConstraint("grain IN ('day', 'week', 'month')", name="ck_metric_snapshots_grain_allowed"),
        sa.CheckConstraint("period_start < period_end", name="ck_metric_snapshots_period_valid"),
        sa.CheckConstraint("source_revision >= 0", name="ck_metric_snapshots_source_revision_non_negative"),
    )
    op.create_index("ix_metric_snapshots_org_metric", "metric_snapshots", ["organization_id", "metric_key", "period_start"])
    op.create_table(
        "ai_insights",
        uuid_column(), uuid_column("organization_id"), sa.Column("title", sa.Text(), nullable=False), sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(24), nullable=False), sa.Column("severity", sa.String(16), nullable=False), sa.Column("supporting_metrics", postgresql.JSONB(), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False), sa.Column("model", sa.String(80)), sa.Column("prompt_version", sa.String(32), nullable=False),
        sa.Column("generation_mode", sa.String(24), nullable=False), sa.Column("status", sa.String(24), server_default="active", nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False), sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True)), sa.Column("superseded_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", name="fk_ai_insights_organization_id_organizations"),
        sa.PrimaryKeyConstraint("id", name="pk_ai_insights"), tenant_unique("ai_insights"),
        sa.CheckConstraint("category IN ('growth', 'warning', 'opportunity', 'performance', 'anomaly')", name="ck_ai_insights_category_allowed"),
        sa.CheckConstraint("severity IN ('info', 'low', 'medium', 'high')", name="ck_ai_insights_severity_allowed"),
        sa.CheckConstraint("status IN ('active', 'superseded', 'failed')", name="ck_ai_insights_status_allowed"),
        sa.CheckConstraint("generation_mode IN ('deterministic', 'provider', 'fallback')", name="ck_ai_insights_generation_mode_allowed"),
        sa.CheckConstraint("period_start < period_end", name="ck_ai_insights_period_valid"),
    )
    op.create_index("ix_ai_insights_org_generated", "ai_insights", ["organization_id", "generated_at"])
    op.create_index("ix_ai_insights_org_status", "ai_insights", ["organization_id", "status", "severity"])
    op.create_table(
        "assistant_queries",
        uuid_column(), uuid_column("organization_id"), uuid_column("user_id"), sa.Column("question_redacted", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(80), nullable=False), sa.Column("parameters", postgresql.JSONB(), nullable=False), sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("answer_status", sa.String(24), nullable=False), sa.Column("applied_range", postgresql.JSONB(), nullable=False), sa.Column("confidence", sa.Numeric(4, 3)),
        sa.Column("follow_ups", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False), sa.Column("supporting_metrics", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False), created_at(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", name="fk_assistant_queries_organization_id_organizations"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_assistant_queries_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_assistant_queries"), tenant_unique("assistant_queries"),
        sa.CheckConstraint("answer_status IN ('answered', 'unsupported', 'insufficient_data', 'blocked')", name="ck_assistant_queries_answer_status_allowed"),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_assistant_queries_confidence_range"),
    )
    op.create_index("ix_assistant_queries_org_user", "assistant_queries", ["organization_id", "user_id", "created_at"])
    op.create_table(
        "weekly_summaries",
        uuid_column(), uuid_column("organization_id"), sa.Column("week_start", sa.Date(), nullable=False), sa.Column("week_end", sa.Date(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False), sa.Column("summary", sa.Text(), nullable=False), sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("model", sa.String(80)), uuid_column("generated_by_user_id", nullable=True), sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", name="fk_weekly_summaries_organization_id_organizations"),
        sa.ForeignKeyConstraint(["generated_by_user_id"], ["users.id"], ondelete="SET NULL", name="fk_weekly_summaries_generated_by_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_weekly_summaries"), tenant_unique("weekly_summaries"),
        sa.UniqueConstraint("organization_id", "week_start", name="uq_weekly_summaries_week"), sa.CheckConstraint("week_start < week_end", name="ck_weekly_summaries_week_valid"),
    )


def _create_operations_tables() -> None:
    op.create_table(
        "reports",
        uuid_column(), uuid_column("organization_id"), uuid_column("created_by_user_id"), sa.Column("report_type", sa.String(32), nullable=False),
        sa.Column("name", sa.String(160), nullable=False), sa.Column("filters", postgresql.JSONB(), nullable=False), sa.Column("status", sa.String(20), server_default="queued", nullable=False),
        sa.Column("format", sa.String(12), nullable=False), sa.Column("source_revision", sa.BigInteger(), nullable=False), sa.Column("result_summary", postgresql.JSONB()),
        sa.Column("storage_key", sa.Text()), sa.Column("generated_at", sa.DateTime(timezone=True)), sa.Column("expires_at", sa.DateTime(timezone=True)), created_at(), updated_at(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", name="fk_reports_organization_id_organizations"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT", name="fk_reports_created_by_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_reports"), tenant_unique("reports"),
        sa.CheckConstraint("report_type IN ('monthly_performance', 'sales', 'customer', 'product_performance')", name="ck_reports_type_allowed"),
        sa.CheckConstraint("status IN ('queued', 'generating', 'ready', 'failed', 'expired')", name="ck_reports_status_allowed"),
        sa.CheckConstraint("format IN ('json', 'csv')", name="ck_reports_format_allowed"), sa.CheckConstraint("source_revision >= 0", name="ck_reports_source_revision_non_negative"),
    )
    op.create_index("ix_reports_org_created", "reports", ["organization_id", "created_at"])
    op.create_index("ix_reports_org_status", "reports", ["organization_id", "status"])
    op.create_table(
        "subscriptions",
        uuid_column(), uuid_column("organization_id"), sa.Column("plan", sa.String(20), server_default="free", nullable=False),
        sa.Column("status", sa.String(20), server_default="active", nullable=False), sa.Column("provider", sa.String(20), server_default="demo", nullable=False),
        sa.Column("provider_customer_id", sa.Text()), sa.Column("provider_subscription_id", sa.Text()), sa.Column("current_period_start", sa.DateTime(timezone=True)),
        sa.Column("current_period_end", sa.DateTime(timezone=True)), sa.Column("cancel_at_period_end", sa.Boolean(), server_default=sa.text("false"), nullable=False), created_at(), updated_at(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", name="fk_subscriptions_organization_id_organizations"),
        sa.PrimaryKeyConstraint("id", name="pk_subscriptions"), tenant_unique("subscriptions"), sa.UniqueConstraint("organization_id", name="uq_subscriptions_organization"),
        sa.UniqueConstraint("provider_customer_id", name="uq_subscriptions_provider_customer"), sa.UniqueConstraint("provider_subscription_id", name="uq_subscriptions_provider_subscription"),
        sa.CheckConstraint("plan IN ('free', 'pro', 'business')", name="ck_subscriptions_plan_allowed"),
        sa.CheckConstraint("status IN ('active', 'trialing', 'past_due', 'cancelled')", name="ck_subscriptions_status_allowed"),
        sa.CheckConstraint("provider IN ('demo', 'stripe')", name="ck_subscriptions_provider_allowed"),
    )
    op.create_table(
        "billing_events",
        uuid_column(), uuid_column("organization_id"), sa.Column("provider_event_id", sa.String(255), nullable=False), uuid_column("subscription_id", nullable=True),
        sa.Column("event_type", sa.String(120), nullable=False), sa.Column("payload_digest", sa.CHAR(64), nullable=False), sa.Column("status", sa.String(20), server_default="received", nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", name="fk_billing_events_organization_id_organizations"),
        sa.ForeignKeyConstraint(["organization_id", "subscription_id"], ["subscriptions.organization_id", "subscriptions.id"], name="fk_billing_events_tenant_subscription"),
        sa.PrimaryKeyConstraint("id", name="pk_billing_events"), tenant_unique("billing_events"), sa.UniqueConstraint("provider_event_id", name="uq_billing_events_provider_event"),
        sa.CheckConstraint("status IN ('received', 'processed', 'failed')", name="ck_billing_events_status_allowed"),
    )
    op.create_index("ix_billing_events_org_received", "billing_events", ["organization_id", "received_at"])
    op.create_table(
        "audit_logs",
        uuid_column(), uuid_column("organization_id", nullable=True), uuid_column("actor_user_id", nullable=True), sa.Column("action", sa.String(120), nullable=False),
        sa.Column("resource_type", sa.String(80)), uuid_column("resource_id", nullable=True), uuid_column("request_id"), sa.Column("actor_type", sa.String(16), nullable=False),
        sa.Column("safe_metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False), sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL", name="fk_audit_logs_organization_id_organizations"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL", name="fk_audit_logs_actor_user_id_users"), sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
        sa.CheckConstraint("actor_type IN ('user', 'system', 'demo')", name="ck_audit_logs_actor_type_allowed"),
    )
    op.create_index("ix_audit_logs_org_occurred", "audit_logs", ["organization_id", "occurred_at"])
    op.create_index("ix_audit_logs_actor_occurred", "audit_logs", ["actor_user_id", "occurred_at"])
    op.create_index("ix_audit_logs_resource", "audit_logs", ["organization_id", "resource_type", "resource_id"])
    op.create_table(
        "background_jobs",
        uuid_column(), uuid_column("organization_id", nullable=True), uuid_column("requested_by_user_id", nullable=True), sa.Column("actor_type", sa.String(16), nullable=False),
        sa.Column("job_type", sa.String(80), nullable=False), sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("progress", postgresql.JSONB(), server_default=sa.text("jsonb_build_object('current', 0, 'total', NULL, 'unit', 'items')"), nullable=False),
        sa.Column("status", sa.String(24), server_default="queued", nullable=False), sa.Column("priority", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("run_after", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("attempt_count", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.SmallInteger(), server_default="5", nullable=False), sa.Column("locked_by", sa.String(120)), sa.Column("locked_until", sa.DateTime(timezone=True)),
        uuid_column("idempotency_record_id", nullable=True), sa.Column("trace_id", sa.String(80)), sa.Column("last_error_code", sa.String(80)),
        sa.Column("last_error_message", sa.String(500)), uuid_column("last_error_request_id", nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("completed_at", sa.DateTime(timezone=True)), created_at(), updated_at(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE", name="fk_background_jobs_organization_id_organizations"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL", name="fk_background_jobs_requested_by_user_id_users"),
        sa.ForeignKeyConstraint(["idempotency_record_id"], ["idempotency_records.id"], ondelete="SET NULL", name="fk_background_jobs_idempotency_record_id_idempotency_records"),
        sa.PrimaryKeyConstraint("id", name="pk_background_jobs"),
        sa.CheckConstraint("actor_type IN ('user', 'system', 'demo')", name="ck_background_jobs_actor_type_allowed"),
        sa.CheckConstraint("status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')", name="ck_background_jobs_status_allowed"),
        sa.CheckConstraint("priority >= -100 AND priority <= 100", name="ck_background_jobs_priority_bounded"),
        sa.CheckConstraint("attempt_count >= 0 AND max_attempts > 0 AND attempt_count <= max_attempts", name="ck_background_jobs_attempts_bounded"),
        sa.CheckConstraint("(locked_by IS NULL) = (locked_until IS NULL)", name="ck_background_jobs_lease_fields_consistent"),
    )
    op.create_index("ix_background_jobs_claim", "background_jobs", ["status", "run_after", "priority"], postgresql_where=sa.text("status IN ('queued', 'running')"))
    op.create_index("ix_background_jobs_org_created", "background_jobs", ["organization_id", "created_at"])
    op.create_index("ix_background_jobs_idempotency", "background_jobs", ["idempotency_record_id"])


def downgrade() -> None:
    for table_name in (
        "background_jobs", "audit_logs", "billing_events", "subscriptions", "reports",
        "weekly_summaries", "assistant_queries", "ai_insights", "metric_snapshots", "metric_observations",
        "data_import_errors", "data_imports", "order_status_events", "order_items", "orders", "products", "customers",
        "idempotency_records", "organization_invitations", "organization_members", "organizations",
        "account_action_tokens", "user_sessions", "user_preferences", "users",
    ):
        op.drop_table(table_name)

# fmt: on
