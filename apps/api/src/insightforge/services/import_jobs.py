from __future__ import annotations

import hashlib
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import cast

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.core.config import Settings
from insightforge.core.money import MAX_MONEY_MINOR, minor_to_decimal
from insightforge.core.policies import Permission, permissions_for
from insightforge.core.problems import AppError
from insightforge.core.revisions import increment_data_revision
from insightforge.core.time import utc_now
from insightforge.imports import (
    CsvImportKind,
    CsvImportLimits,
    CsvImportRejected,
    CsvRowError,
    CustomerCsvRow,
    OrderCsvRow,
    ProductCsvRow,
    validate_csv,
)
from insightforge.models import (
    AuditLog,
    BackgroundJob,
    Customer,
    DataImport,
    DataImportError,
    Order,
    OrderItem,
    OrderStatusEvent,
    Organization,
    OrganizationMember,
    Product,
)
from insightforge.models.enums import ImportStatus
from insightforge.repositories.commerce import REVENUE_STATUSES
from insightforge.repositories.imports import ImportRepository
from insightforge.storage import LocalPrivateStorage


@dataclass(frozen=True, slots=True)
class SafeImportError:
    row_number: int
    column: str | None
    code: str
    message: str


class ImportProcessingFailure(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        errors: list[SafeImportError] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message
        self.errors = errors or []


def _json_value(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _safe_error(error: CsvRowError) -> SafeImportError:
    return SafeImportError(
        row_number=error.row_number,
        column=error.column,
        code=error.code,
        message=error.message,
    )


class ImportJobHandler:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.repository = ImportRepository(db)
        self.storage = LocalPrivateStorage(settings.private_storage_path)

    def _limits(self, *, retain_all_rows: bool = False) -> CsvImportLimits:
        return CsvImportLimits(
            max_bytes=self.settings.upload_max_bytes,
            max_rows=self.settings.upload_max_rows,
            max_errors=self.settings.import_max_errors,
            max_preview_rows=(
                self.settings.upload_max_rows
                if retain_all_rows
                else self.settings.import_preview_rows
            ),
        )

    def _read_verified(self, data_import: DataImport) -> bytes:
        if data_import.storage_key is None:
            raise ImportProcessingFailure(
                "retained_file_missing",
                "The retained import file is unavailable.",
            )
        try:
            payload = self.storage.read_bytes(
                data_import.storage_key,
                max_bytes=self.settings.upload_max_bytes,
            )
        except AppError as exc:
            raise ImportProcessingFailure(exc.code, exc.detail) from exc
        if len(payload) != data_import.size_bytes:
            raise ImportProcessingFailure(
                "retained_file_changed",
                "The retained import file size changed after upload.",
            )
        if hashlib.sha256(payload).hexdigest() != data_import.content_sha256:
            raise ImportProcessingFailure(
                "retained_file_changed",
                "The retained import file digest changed after upload.",
            )
        return payload

    async def validate(self, job: BackgroundJob, data_import: DataImport) -> None:
        if data_import.status in {
            ImportStatus.CANCELLED.value,
            ImportStatus.EXPIRED.value,
        }:
            return
        if data_import.status != ImportStatus.VALIDATING.value:
            raise ImportProcessingFailure(
                "invalid_import_state",
                "The import is not waiting for validation.",
            )
        payload = self._read_verified(data_import)
        await self.db.execute(
            delete(DataImportError).where(
                DataImportError.organization_id == data_import.organization_id,
                DataImportError.import_id == data_import.id,
            )
        )
        try:
            result = validate_csv(
                payload,
                kind=CsvImportKind(data_import.kind),
                limits=self._limits(),
            )
        except CsvImportRejected as exc:
            data_import.status = ImportStatus.VALIDATION_FAILED.value
            data_import.validation_summary = {
                "file_error": {"code": exc.code, "message": exc.message},
                "headers": [],
                "preview_rows": [],
                "formula_cells": [],
            }
            self.db.add(
                DataImportError(
                    id=uuid.uuid4(),
                    organization_id=data_import.organization_id,
                    import_id=data_import.id,
                    row_number=exc.row_number or 1,
                    column_name=None,
                    error_code=exc.code,
                    safe_message=exc.message,
                    raw_value_excerpt=None,
                )
            )
            job.progress = {"current": 0, "total": 0, "unit": "rows"}
            return

        data_import.total_rows = result.total_rows
        data_import.valid_rows = result.valid_rows
        data_import.invalid_rows = result.invalid_rows
        data_import.mapping = {
            "template_version": result.template_version,
            "headers": list(result.headers),
        }
        data_import.validation_summary = {
            "headers": list(result.headers),
            "preview_rows": [
                cast(dict[str, object], _json_value(asdict(row))) for row in result.preview_rows
            ],
            "preview_rows_truncated": result.valid_rows > len(result.preview_rows),
            "error_count": result.error_count,
            "errors_truncated": result.errors_truncated,
            "formula_cells": [asdict(cell) for cell in result.formula_cells],
            "formula_cell_count": result.formula_cell_count,
            "formula_cells_truncated": result.formula_cells_truncated,
        }
        for error in result.errors:
            self.db.add(
                DataImportError(
                    id=uuid.uuid4(),
                    organization_id=data_import.organization_id,
                    import_id=data_import.id,
                    row_number=error.row_number,
                    column_name=error.column,
                    error_code=error.code,
                    safe_message=error.message,
                    raw_value_excerpt=None,
                )
            )
        data_import.status = (
            ImportStatus.READY.value if result.is_valid else ImportStatus.VALIDATION_FAILED.value
        )
        job.progress = {
            "current": result.total_rows,
            "total": result.total_rows,
            "unit": "rows",
        }

    async def apply(self, job: BackgroundJob, data_import: DataImport) -> None:
        if data_import.status == ImportStatus.CANCELLED.value:
            return
        if data_import.status != ImportStatus.IMPORTING.value:
            raise ImportProcessingFailure(
                "import_not_ready",
                "The import is not in a committable state.",
            )
        await self._recheck_requester(job, data_import)
        payload = self._read_verified(data_import)
        if job.payload.get("content_sha256") != data_import.content_sha256:
            raise ImportProcessingFailure(
                "validation_revision_changed",
                "The validated content digest no longer matches the commit request.",
            )
        try:
            result = validate_csv(
                payload,
                kind=CsvImportKind(data_import.kind),
                limits=self._limits(retain_all_rows=True),
            )
        except CsvImportRejected as exc:
            raise ImportProcessingFailure(exc.code, exc.message) from exc
        if not result.is_valid:
            raise ImportProcessingFailure(
                "validation_failed",
                "The retained CSV no longer passes validation.",
                errors=[_safe_error(error) for error in result.errors],
            )

        if result.kind is CsvImportKind.CUSTOMERS:
            await self._apply_customers(data_import, result.preview_rows)
        elif result.kind is CsvImportKind.PRODUCTS:
            await self._apply_products(data_import, result.preview_rows)
        else:
            await self._apply_orders(data_import, result.preview_rows)

        organization = await self.db.get(Organization, data_import.organization_id)
        if organization is None:
            raise ImportProcessingFailure("tenant_missing", "The organization is unavailable.")
        await increment_data_revision(self.db, organization)
        now = utc_now()
        data_import.status = ImportStatus.COMPLETED.value
        data_import.imported_rows = result.total_rows
        data_import.completed_at = now
        job.progress = {
            "current": result.total_rows,
            "total": result.total_rows,
            "unit": "rows",
        }
        self.db.add(
            AuditLog(
                id=uuid.uuid4(),
                organization_id=data_import.organization_id,
                actor_user_id=data_import.requested_by_user_id,
                action="data_import.completed",
                resource_type="data_import",
                resource_id=data_import.id,
                request_id=uuid.uuid4(),
                actor_type=job.actor_type,
                safe_metadata={
                    "kind": data_import.kind,
                    "imported_rows": result.total_rows,
                },
                occurred_at=now,
            )
        )

    async def _recheck_requester(
        self,
        job: BackgroundJob,
        data_import: DataImport,
    ) -> None:
        if job.requested_by_user_id is None:
            raise ImportProcessingFailure(
                "requester_unavailable",
                "The requesting user is unavailable.",
            )
        row = (
            await self.db.execute(
                select(Organization, OrganizationMember)
                .join(
                    OrganizationMember,
                    OrganizationMember.organization_id == Organization.id,
                )
                .where(
                    Organization.id == data_import.organization_id,
                    OrganizationMember.user_id == job.requested_by_user_id,
                    OrganizationMember.removed_at.is_(None),
                )
            )
        ).one_or_none()
        if row is None:
            raise ImportProcessingFailure(
                "permission_denied",
                "The requester no longer has access to this organization.",
            )
        organization, membership = row[0], row[1]
        if not permissions_for(membership.role, is_demo=organization.is_demo).allows(
            Permission.IMPORT_DATA
        ):
            raise ImportProcessingFailure(
                "permission_denied",
                "The requester no longer has permission to import data.",
            )
        if organization.is_demo != (job.actor_type == "demo"):
            raise ImportProcessingFailure(
                "tenant_context_changed",
                "The import actor no longer matches the organization context.",
            )
        if organization.status != "active":
            raise ImportProcessingFailure(
                "organization_unavailable",
                "The organization is not available for imports.",
            )
        if organization.is_demo and (
            organization.demo_expires_at is None or organization.demo_expires_at <= utc_now()
        ):
            raise ImportProcessingFailure(
                "resource_expired",
                "The demo workspace expired before the import completed.",
            )

    async def _apply_customers(
        self,
        data_import: DataImport,
        rows: tuple[object, ...],
    ) -> None:
        typed_rows = [row for row in rows if isinstance(row, CustomerCsvRow)]
        external_ids = [row.external_id for row in typed_rows]
        emails = [row.email for row in typed_rows if row.email]
        duplicate = await self.db.scalar(
            select(Customer.id)
            .where(
                Customer.organization_id == data_import.organization_id,
                or_(Customer.external_id.in_(external_ids), Customer.email.in_(emails)),
            )
            .limit(1)
        )
        if duplicate is not None:
            raise ImportProcessingFailure(
                "duplicate_resource",
                "A customer external ID or email already exists in this organization.",
            )
        now = utc_now()
        self.db.add_all(
            [
                Customer(
                    id=uuid.uuid4(),
                    organization_id=data_import.organization_id,
                    external_id=row.external_id,
                    name=row.name,
                    email=row.email,
                    company=row.company,
                    status=row.status,
                    segment="new",
                    acquired_at=row.acquired_at,
                    lifetime_value=Decimal("0.00"),
                    created_at=now,
                    updated_at=now,
                )
                for row in typed_rows
            ]
        )
        await self.db.flush()

    async def _apply_products(
        self,
        data_import: DataImport,
        rows: tuple[object, ...],
    ) -> None:
        typed_rows = [row for row in rows if isinstance(row, ProductCsvRow)]
        external_ids = [row.external_id for row in typed_rows]
        skus = [row.sku for row in typed_rows]
        duplicate = await self.db.scalar(
            select(Product.id)
            .where(
                Product.organization_id == data_import.organization_id,
                or_(Product.external_id.in_(external_ids), Product.sku.in_(skus)),
            )
            .limit(1)
        )
        if duplicate is not None:
            raise ImportProcessingFailure(
                "duplicate_resource",
                "A product external ID or SKU already exists in this organization.",
            )
        now = utc_now()
        self.db.add_all(
            [
                Product(
                    id=uuid.uuid4(),
                    organization_id=data_import.organization_id,
                    external_id=row.external_id,
                    sku=row.sku,
                    name=row.name,
                    category=row.category,
                    unit_price=minor_to_decimal(row.unit_price_minor),
                    status=row.status,
                    deleted_at=now if row.status == "archived" else None,
                    created_at=now,
                    updated_at=now,
                )
                for row in typed_rows
            ]
        )
        await self.db.flush()

    async def _apply_orders(
        self,
        data_import: DataImport,
        rows: tuple[object, ...],
    ) -> None:
        typed_rows = [row for row in rows if isinstance(row, OrderCsvRow)]
        customer_refs = {row.customer_external_id for row in typed_rows}
        product_skus = {row.product_sku for row in typed_rows}
        customers = list(
            (
                await self.db.scalars(
                    select(Customer).where(
                        Customer.organization_id == data_import.organization_id,
                        Customer.external_id.in_(customer_refs),
                        Customer.deleted_at.is_(None),
                    )
                )
            ).all()
        )
        products = list(
            (
                await self.db.scalars(
                    select(Product).where(
                        Product.organization_id == data_import.organization_id,
                        Product.sku.in_(product_skus),
                    )
                )
            ).all()
        )
        customer_map = {customer.external_id: customer for customer in customers}
        product_map = {product.sku: product for product in products}
        reference_errors = [
            SafeImportError(
                row.row_number,
                "customer_external_id",
                "unknown_reference",
                "The customer external ID does not exist in this organization.",
            )
            for row in typed_rows
            if row.customer_external_id not in customer_map
        ]
        reference_errors.extend(
            SafeImportError(
                row.row_number,
                "product_sku",
                "unknown_reference",
                "The product SKU does not exist in this organization.",
            )
            for row in typed_rows
            if row.product_sku not in product_map
        )
        organization = await self.db.get(Organization, data_import.organization_id)
        if organization is None:
            raise ImportProcessingFailure("tenant_missing", "The organization is unavailable.")
        reference_errors.extend(
            SafeImportError(
                row.row_number,
                "currency",
                "currency_mismatch",
                "Order currency must match the organization reporting currency.",
            )
            for row in typed_rows
            if row.currency != organization.reporting_currency
        )
        if reference_errors:
            raise ImportProcessingFailure(
                "reference_validation_failed",
                "One or more order references are invalid.",
                errors=reference_errors[: self.settings.import_max_errors],
            )
        external_ids = {row.external_id for row in typed_rows}
        order_numbers = {row.order_number for row in typed_rows}
        duplicate = await self.db.scalar(
            select(Order.id)
            .where(
                Order.organization_id == data_import.organization_id,
                or_(Order.external_id.in_(external_ids), Order.order_number.in_(order_numbers)),
            )
            .limit(1)
        )
        if duplicate is not None:
            raise ImportProcessingFailure(
                "duplicate_resource",
                "An order external ID or order number already exists in this organization.",
            )

        grouped: dict[str, list[OrderCsvRow]] = defaultdict(list)
        for row in typed_rows:
            grouped[row.external_id].append(row)
        now = utc_now()
        orders: list[Order] = []
        items: list[OrderItem] = []
        events: list[OrderStatusEvent] = []
        for external_id, order_rows in grouped.items():
            first = order_rows[0]
            order_id = uuid.uuid4()
            subtotal_minor = sum(row.unit_price_minor * row.quantity for row in order_rows)
            discount_minor = sum(row.discount_minor for row in order_rows)
            tax_minor = sum(row.tax_minor for row in order_rows)
            if any(row.discount_minor > row.unit_price_minor * row.quantity for row in order_rows):
                raise ImportProcessingFailure(
                    "invalid_order_total",
                    "A line discount exceeds its gross line amount.",
                )
            total_minor = subtotal_minor - discount_minor + tax_minor
            if (
                total_minor < 0
                or max(
                    subtotal_minor,
                    discount_minor,
                    tax_minor,
                    total_minor,
                )
                > MAX_MONEY_MINOR
            ):
                raise ImportProcessingFailure(
                    "invalid_order_total",
                    "An imported order total is outside the supported money range.",
                )
            customer = customer_map[first.customer_external_id]
            orders.append(
                Order(
                    id=order_id,
                    organization_id=data_import.organization_id,
                    customer_id=customer.id,
                    external_id=external_id,
                    order_number=first.order_number,
                    status=first.status,
                    ordered_at=first.ordered_at,
                    subtotal=minor_to_decimal(subtotal_minor),
                    discount=minor_to_decimal(discount_minor),
                    tax=minor_to_decimal(tax_minor),
                    total=minor_to_decimal(total_minor),
                    currency=first.currency,
                    source="csv_import",
                    created_at=now,
                    updated_at=now,
                )
            )
            events.append(
                OrderStatusEvent(
                    id=uuid.uuid4(),
                    organization_id=data_import.organization_id,
                    order_id=order_id,
                    changed_by_user_id=data_import.requested_by_user_id,
                    from_status=None,
                    to_status=first.status,
                    reason="Created by a validated CSV import.",
                    occurred_at=first.ordered_at,
                )
            )
            for row in order_rows:
                product = product_map[row.product_sku]
                gross_minor = row.unit_price_minor * row.quantity
                items.append(
                    OrderItem(
                        id=uuid.uuid4(),
                        organization_id=data_import.organization_id,
                        order_id=order_id,
                        product_id=product.id,
                        product_name=product.name,
                        sku=product.sku,
                        quantity=row.quantity,
                        unit_price=minor_to_decimal(row.unit_price_minor),
                        discount=minor_to_decimal(row.discount_minor),
                        line_total=minor_to_decimal(gross_minor - row.discount_minor),
                        created_at=now,
                    )
                )
        self.db.add_all(orders)
        await self.db.flush()
        self.db.add_all([*items, *events])
        await self.db.flush()
        await self._refresh_customer_projections(
            data_import.organization_id,
            {order.customer_id for order in orders},
            customer_map,
        )

    async def _refresh_customer_projections(
        self,
        organization_id: uuid.UUID,
        customer_ids: set[uuid.UUID],
        customer_map: dict[str | None, Customer],
    ) -> None:
        rows = (
            await self.db.execute(
                select(
                    Order.customer_id,
                    func.sum(Order.total),
                    func.max(Order.ordered_at),
                    func.count(Order.id),
                )
                .where(
                    Order.organization_id == organization_id,
                    Order.customer_id.in_(customer_ids),
                    Order.status.in_(REVENUE_STATUSES),
                )
                .group_by(Order.customer_id)
            )
        ).all()
        by_id = {customer.id: customer for customer in customer_map.values()}
        for customer_id, spend, last_order_at, count in rows:
            customer = by_id[customer_id]
            customer.lifetime_value = Decimal(spend)
            customer.last_order_at = last_order_at
            order_count = int(count)
            if order_count >= 10 or customer.lifetime_value >= Decimal("5000.00"):
                customer.segment = "high_value"
            elif order_count >= 5:
                customer.segment = "loyal"
            elif order_count >= 2:
                customer.segment = "repeat"
            else:
                customer.segment = "new"


async def persist_import_failure(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    import_id: uuid.UUID,
    code: str,
    message: str,
    errors: list[SafeImportError],
    max_errors: int,
) -> None:
    data_import = await ImportRepository(db).get_trusted(
        organization_id,
        import_id,
        for_update=True,
    )
    if data_import is None or data_import.status == ImportStatus.CANCELLED.value:
        return
    data_import.status = ImportStatus.IMPORT_FAILED.value
    data_import.validation_summary = {
        **data_import.validation_summary,
        "commit_error": {"code": code, "message": message},
    }
    await db.execute(
        delete(DataImportError).where(
            DataImportError.organization_id == organization_id,
            DataImportError.import_id == import_id,
        )
    )
    for error in errors[:max_errors]:
        db.add(
            DataImportError(
                id=uuid.uuid4(),
                organization_id=organization_id,
                import_id=import_id,
                row_number=max(1, error.row_number),
                column_name=error.column,
                error_code=error.code,
                safe_message=error.message,
                raw_value_excerpt=None,
            )
        )
