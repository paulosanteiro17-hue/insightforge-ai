from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from insightforge.db.base import Base
from insightforge.models import *  # noqa: F403


def test_foundation_declares_every_required_domain_table() -> None:
    expected = {
        "users",
        "user_preferences",
        "user_sessions",
        "account_action_tokens",
        "organizations",
        "organization_members",
        "organization_invitations",
        "idempotency_records",
        "customers",
        "products",
        "orders",
        "order_items",
        "order_status_events",
        "metric_observations",
        "metric_snapshots",
        "data_imports",
        "data_import_errors",
        "ai_insights",
        "assistant_queries",
        "weekly_summaries",
        "reports",
        "subscriptions",
        "billing_events",
        "audit_logs",
        "background_jobs",
    }

    assert expected <= set(Base.metadata.tables)


def test_cross_tenant_order_references_are_composite() -> None:
    orders = Base.metadata.tables["orders"]
    order_items = Base.metadata.tables["order_items"]

    order_targets = {
        tuple(element.target_fullname for element in constraint.elements)
        for constraint in orders.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    item_targets = {
        tuple(element.target_fullname for element in constraint.elements)
        for constraint in order_items.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }

    assert ("customers.organization_id", "customers.id") in order_targets
    assert ("orders.organization_id", "orders.id") in item_targets
    assert ("products.organization_id", "products.id") in item_targets


def test_tenant_tables_expose_composite_organization_identifiers() -> None:
    for table_name in ("customers", "products", "orders", "reports", "ai_insights"):
        table = Base.metadata.tables[table_name]
        unique_columns = {
            tuple(column.name for column in constraint.columns)
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        }
        assert ("organization_id", "id") in unique_columns


def test_state_columns_use_varchar_check_constraints_instead_of_native_enums() -> None:
    organizations = Base.metadata.tables["organizations"]
    assert organizations.c.status.type.__class__.__name__ == "String"
    assert any(
        isinstance(constraint, CheckConstraint) and "status IN" in str(constraint.sqltext)
        for constraint in organizations.constraints
    )


def test_optimistic_versions_exist_only_on_mutable_contract_resources() -> None:
    for table_name in ("organizations", "customers", "products", "orders"):
        assert "version" in Base.metadata.tables[table_name].c
    assert "version" not in Base.metadata.tables["order_items"].c
    assert "version" not in Base.metadata.tables["reports"].c
