from __future__ import annotations

from enum import StrEnum


class UserStatus(StrEnum):
    ACTIVE = "active"
    INVITED = "invited"
    DISABLED = "disabled"


class AccountActionKind(StrEnum):
    PASSWORD_RESET = "password_reset"  # noqa: S105 - action kind, not a credential
    EMAIL_VERIFICATION = "email_verification"
    EMAIL_CHANGE = "email_change"


class OrganizationStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING_DELETION = "pending_deletion"


class OnboardingState(StrEnum):
    ORGANIZATION = "organization"
    DATA = "data"
    COMPLETE = "complete"


class DemoStatus(StrEnum):
    PREPARING = "preparing"
    READY = "ready"
    RESETTING = "resetting"
    EXPIRED = "expired"


class OrganizationRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class CustomerStatus(StrEnum):
    ACTIVE = "active"
    AT_RISK = "at_risk"
    INACTIVE = "inactive"


class CustomerSegment(StrEnum):
    NEW = "new"
    REPEAT = "repeat"
    LOYAL = "loyal"
    HIGH_VALUE = "high_value"
    AT_RISK = "at_risk"
    INACTIVE = "inactive"


class ProductStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class OrderStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class MetricGrain(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class InsightCategory(StrEnum):
    GROWTH = "growth"
    WARNING = "warning"
    OPPORTUNITY = "opportunity"
    PERFORMANCE = "performance"
    ANOMALY = "anomaly"


class InsightSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ImportKind(StrEnum):
    CUSTOMERS = "customers"
    PRODUCTS = "products"
    ORDERS = "orders"


class ImportStatus(StrEnum):
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    READY = "ready"
    IMPORTING = "importing"
    COMPLETED = "completed"
    VALIDATION_FAILED = "validation_failed"
    IMPORT_FAILED = "import_failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ReportType(StrEnum):
    MONTHLY_PERFORMANCE = "monthly_performance"
    SALES = "sales"
    CUSTOMER = "customer"
    PRODUCT_PERFORMANCE = "product_performance"


class ReportStatus(StrEnum):
    QUEUED = "queued"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    EXPIRED = "expired"


class ReportFormat(StrEnum):
    JSON = "json"
    CSV = "csv"


class Plan(StrEnum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"


class BillingProvider(StrEnum):
    DEMO = "demo"
    STRIPE = "stripe"


class BillingEventStatus(StrEnum):
    RECEIVED = "received"
    PROCESSED = "processed"
    FAILED = "failed"


class ActorType(StrEnum):
    USER = "user"
    SYSTEM = "system"
    DEMO = "demo"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IdempotencyState(StrEnum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
