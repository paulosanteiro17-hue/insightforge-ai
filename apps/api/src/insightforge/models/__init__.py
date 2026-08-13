"""SQLAlchemy persistence models exposed for metadata discovery."""

from insightforge.models.analytics import (
    AIInsight,
    AssistantQuery,
    MetricObservation,
    MetricSnapshot,
    WeeklySummary,
)
from insightforge.models.commerce import Customer, Order, OrderItem, OrderStatusEvent, Product
from insightforge.models.identity import (
    AccountActionToken,
    IdempotencyRecord,
    Organization,
    OrganizationInvitation,
    OrganizationMember,
    User,
    UserPreference,
    UserSession,
)
from insightforge.models.operations import (
    AuditLog,
    BackgroundJob,
    BillingEvent,
    DataImport,
    DataImportError,
    Report,
    Subscription,
)

__all__ = [
    "AIInsight",
    "AccountActionToken",
    "AssistantQuery",
    "AuditLog",
    "BackgroundJob",
    "BillingEvent",
    "Customer",
    "DataImport",
    "DataImportError",
    "IdempotencyRecord",
    "MetricObservation",
    "MetricSnapshot",
    "Order",
    "OrderItem",
    "OrderStatusEvent",
    "Organization",
    "OrganizationInvitation",
    "OrganizationMember",
    "Product",
    "Report",
    "Subscription",
    "User",
    "UserPreference",
    "UserSession",
    "WeeklySummary",
]
