from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.core.config import Settings
from insightforge.core.problems import AppError
from insightforge.core.security import constant_time_equal
from insightforge.core.time import utc_now
from insightforge.models import (
    BackgroundJob,
    Customer,
    Order,
    OrderItem,
    Organization,
    OrganizationMember,
    Product,
    User,
)
from insightforge.models.enums import OrganizationRole, OrganizationStatus
from insightforge.schemas.organizations import DataExportView, OrganizationDeletionView
from insightforge.services.auditing import add_audit_event
from insightforge.services.idempotency import (
    IdempotencyService,
    canonical_request_hash,
    validate_idempotency_key,
)
from insightforge.storage import LocalPrivateStorage


class DataManagementService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.storage = LocalPrivateStorage(settings.private_storage_path)
        self.idempotency = IdempotencyService(db)

    async def request_deletion(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_is_demo: bool,
        confirmation_name: str,
        request_id: uuid.UUID,
    ) -> OrganizationDeletionView:
        organization = await self._lock_owner(
            organization_id, actor_user_id, actor_is_demo=actor_is_demo
        )
        if not constant_time_equal(confirmation_name, organization.name):
            raise AppError(
                status=422,
                code="deletion_confirmation_mismatch",
                title="Organization name does not match",
                detail="Enter the exact organization name to confirm deletion.",
            )
        existing = await self.db.scalar(
            select(BackgroundJob)
            .where(
                BackgroundJob.organization_id == organization_id,
                BackgroundJob.job_type == "delete_organization",
                BackgroundJob.status.in_(("queued", "running")),
            )
            .order_by(BackgroundJob.created_at.desc())
            .with_for_update()
            .limit(1)
        )
        if existing is not None:
            return self.deletion_view(existing)
        now = utc_now()
        effective_at = now + timedelta(hours=self.settings.organization_deletion_grace_hours)
        job = BackgroundJob(
            id=uuid.uuid4(),
            organization_id=organization_id,
            requested_by_user_id=actor_user_id,
            actor_type="user",
            job_type="delete_organization",
            payload={"effective_deletion_at": effective_at.isoformat()},
            progress={"current": 0, "total": 1, "unit": "organization"},
            status="queued",
            run_after=effective_at,
            max_attempts=3,
        )
        self.db.add(job)
        organization.status = OrganizationStatus.PENDING_DELETION.value
        organization.version += 1
        add_audit_event(
            self.db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            actor_is_demo=False,
            action="organization.deletion.requested",
            request_id=request_id,
            resource_type="organization",
            resource_id=organization_id,
            metadata={"effective_deletion_at": effective_at.isoformat()},
        )
        await self.db.commit()
        return self.deletion_view(job)

    async def deletion_status(self, organization_id: uuid.UUID) -> OrganizationDeletionView:
        job = await self.db.scalar(
            select(BackgroundJob)
            .where(
                BackgroundJob.organization_id == organization_id,
                BackgroundJob.job_type == "delete_organization",
            )
            .order_by(BackgroundJob.created_at.desc(), BackgroundJob.id.desc())
            .limit(1)
        )
        if job is None:
            raise self._not_found()
        return self.deletion_view(job)

    async def cancel_deletion(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_is_demo: bool,
        request_id: uuid.UUID,
    ) -> None:
        organization = await self._lock_owner(
            organization_id, actor_user_id, actor_is_demo=actor_is_demo
        )
        job = await self.db.scalar(
            select(BackgroundJob)
            .where(
                BackgroundJob.organization_id == organization_id,
                BackgroundJob.job_type == "delete_organization",
                BackgroundJob.status.in_(("queued", "running")),
            )
            .order_by(BackgroundJob.created_at.desc())
            .with_for_update()
            .limit(1)
        )
        if job is None:
            raise self._not_found()
        if self._effective_deletion_at(job) <= utc_now():
            raise AppError(
                status=409,
                code="deletion_cannot_be_cancelled",
                title="Deletion can no longer be cancelled",
                detail="The deletion grace period has ended.",
            )
        now = utc_now()
        job.status = "cancelled"
        job.completed_at = now
        organization.status = OrganizationStatus.ACTIVE.value
        organization.version += 1
        add_audit_event(
            self.db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            actor_is_demo=False,
            action="organization.deletion.cancelled",
            request_id=request_id,
            resource_type="organization",
            resource_id=organization_id,
        )
        await self.db.commit()

    async def request_export(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_is_demo: bool,
        request_id: uuid.UUID,
        idempotency_key: str | None,
    ) -> tuple[DataExportView, bool]:
        organization = await self._lock_owner(
            organization_id, actor_user_id, actor_is_demo=actor_is_demo, allow_demo=True
        )
        key = validate_idempotency_key(idempotency_key)
        request_hash = canonical_request_hash({"format": "json"})
        replayed_id = await self.idempotency.replay_resource_id(
            scope_key=f"organization:{organization_id}",
            operation="export_organization_data",
            key=key,
            request_hash=request_hash,
        )
        if replayed_id is not None:
            job = await self._export_job(organization_id, replayed_id)
            if job is None:
                raise self._not_found()
            return self.export_view(job), True

        row_count = await self._export_row_count(organization_id)
        if row_count > self.settings.export_max_rows:
            raise AppError(
                status=413,
                code="export_row_limit_exceeded",
                title="Export contains too many records",
                detail="Reduce retained data before requesting another export.",
            )
        now = utc_now()
        job_id = uuid.uuid4()
        expires_at = now + timedelta(hours=self.settings.export_retention_hours)
        document = await self._export_document(organization, generated_at=now)
        payload = json.dumps(
            document,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        filename = f"insightforge-data-{job_id.hex}.json"
        stored = self.storage.store_bytes(
            f"exports/{organization_id.hex}/{job_id.hex}.json",
            payload,
            max_bytes=self.settings.export_max_bytes,
        )
        metadata: dict[str, object] = {
            "format": "json",
            "filename": filename,
            "content_type": "application/json",
            "size_bytes": stored.size_bytes,
            "content_sha256": stored.content_sha256,
            "storage_key": stored.storage_key,
            "expires_at": expires_at.isoformat(),
            "record_count": row_count,
        }
        job = BackgroundJob(
            id=job_id,
            organization_id=organization_id,
            requested_by_user_id=actor_user_id,
            actor_type="demo" if actor_is_demo else "user",
            job_type="export_organization_data",
            payload=metadata,
            progress={"current": row_count, "total": row_count, "unit": "records"},
            status="succeeded",
            run_after=now,
            attempt_count=1,
            max_attempts=1,
            started_at=now,
            completed_at=now,
        )
        self.db.add(job)
        record = self.idempotency.start(
            scope_key=f"organization:{organization_id}",
            actor_user_id=actor_user_id,
            operation="export_organization_data",
            key=key,
            request_hash=request_hash,
        )
        self.idempotency.complete(
            record,
            status_code=202,
            resource_type="background_job",
            resource_id=job_id,
        )
        add_audit_event(
            self.db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            actor_is_demo=actor_is_demo,
            action="organization.data_export.created",
            request_id=request_id,
            resource_type="background_job",
            resource_id=job_id,
            metadata={
                "format": "json",
                "record_count": row_count,
                "expires_at": expires_at.isoformat(),
            },
        )
        try:
            await self.db.commit()
        except Exception:
            self.storage.delete(stored.storage_key)
            raise
        return self.export_view(job), False

    async def export_status(
        self, organization_id: uuid.UUID, export_id: uuid.UUID
    ) -> DataExportView:
        job = await self._export_job(organization_id, export_id)
        if job is None:
            raise self._not_found()
        return self.export_view(job)

    async def download_export(
        self, organization_id: uuid.UUID, export_id: uuid.UUID
    ) -> tuple[bytes, str, str, str]:
        job = await self._export_job(organization_id, export_id)
        if job is None:
            raise self._not_found()
        expires_at = self._export_expires_at(job)
        if expires_at <= utc_now():
            raise AppError(
                status=410,
                code="export_expired",
                title="Export expired",
                detail="Request a new data export.",
            )
        if job.status != "succeeded":
            raise AppError(
                status=409,
                code="export_not_ready",
                title="Export is not ready",
                detail="Wait for the export to finish before downloading it.",
            )
        storage_key = job.payload.get("storage_key")
        filename = job.payload.get("filename")
        content_type = job.payload.get("content_type")
        content_sha256 = job.payload.get("content_sha256")
        metadata = (storage_key, filename, content_type, content_sha256)
        if not all(isinstance(value, str) for value in metadata):
            raise self._not_found()
        payload = self.storage.read_export_bytes(
            cast(str, storage_key), max_bytes=self.settings.export_max_bytes
        )
        return (
            payload,
            cast(str, filename),
            cast(str, content_type),
            cast(str, content_sha256),
        )

    async def _lock_owner(
        self,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        *,
        actor_is_demo: bool,
        allow_demo: bool = False,
    ) -> Organization:
        organization = await self.db.scalar(
            select(Organization).where(Organization.id == organization_id).with_for_update()
        )
        membership = await self.db.scalar(
            select(OrganizationMember)
            .where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == actor_user_id,
                OrganizationMember.removed_at.is_(None),
            )
            .with_for_update()
        )
        if organization is None or membership is None:
            raise self._not_found()
        if membership.role != OrganizationRole.OWNER.value:
            raise AppError(
                status=403,
                code="permission_denied",
                title="Permission denied",
                detail="Only an organization owner can perform this action.",
            )
        if (organization.is_demo or actor_is_demo) and not allow_demo:
            raise AppError(
                status=403,
                code="demo_policy_denied",
                title="Action unavailable in demo mode",
                detail="Demo workspaces cannot schedule organization deletion.",
            )
        return organization

    async def _export_job(
        self, organization_id: uuid.UUID, export_id: uuid.UUID
    ) -> BackgroundJob | None:
        return cast(
            BackgroundJob | None,
            await self.db.scalar(
                select(BackgroundJob).where(
                    BackgroundJob.organization_id == organization_id,
                    BackgroundJob.id == export_id,
                    BackgroundJob.job_type == "export_organization_data",
                )
            ),
        )

    async def _export_row_count(self, organization_id: uuid.UUID) -> int:
        total = 0
        for model in (OrganizationMember, Customer, Product, Order, OrderItem):
            total += int(
                await self.db.scalar(
                    select(func.count())
                    .select_from(model)
                    .where(model.organization_id == organization_id)
                )
                or 0
            )
        return total

    async def _export_document(
        self, organization: Organization, *, generated_at: datetime
    ) -> dict[str, object]:
        organization_id = organization.id
        member_rows = (
            await self.db.execute(
                select(OrganizationMember, User)
                .join(User, User.id == OrganizationMember.user_id)
                .where(OrganizationMember.organization_id == organization_id)
                .order_by(OrganizationMember.joined_at.asc())
            )
        ).all()
        customers = list(
            (
                await self.db.scalars(
                    select(Customer)
                    .where(Customer.organization_id == organization_id)
                    .order_by(Customer.created_at.asc(), Customer.id.asc())
                )
            ).all()
        )
        products = list(
            (
                await self.db.scalars(
                    select(Product)
                    .where(Product.organization_id == organization_id)
                    .order_by(Product.created_at.asc(), Product.id.asc())
                )
            ).all()
        )
        orders = list(
            (
                await self.db.scalars(
                    select(Order)
                    .where(Order.organization_id == organization_id)
                    .order_by(Order.ordered_at.asc(), Order.id.asc())
                )
            ).all()
        )
        items = list(
            (
                await self.db.scalars(
                    select(OrderItem)
                    .where(OrderItem.organization_id == organization_id)
                    .order_by(OrderItem.created_at.asc(), OrderItem.id.asc())
                )
            ).all()
        )
        return {
            "schema_version": 1,
            "generated_at": generated_at.isoformat(),
            "organization": {
                "id": str(organization.id),
                "name": organization.name,
                "slug": organization.slug,
                "reporting_currency": organization.reporting_currency,
                "timezone": organization.timezone,
                "industry": organization.industry,
                "status": organization.status,
                "onboarding_state": organization.onboarding_state,
            },
            "members": [
                {
                    "membership_id": str(member.id),
                    "user_id": str(user.id),
                    "email": user.email,
                    "display_name": user.display_name,
                    "role": member.role,
                    "joined_at": member.joined_at.isoformat(),
                    "removed_at": self._iso(member.removed_at),
                }
                for member, user in member_rows
            ],
            "customers": [
                {
                    "id": str(customer.id),
                    "external_id": customer.external_id,
                    "name": customer.name,
                    "email": customer.email,
                    "company": customer.company,
                    "status": customer.status,
                    "segment": customer.segment,
                    "acquired_at": customer.acquired_at.isoformat(),
                    "last_order_at": self._iso(customer.last_order_at),
                    "lifetime_value": self._decimal(customer.lifetime_value),
                    "deleted_at": self._iso(customer.deleted_at),
                }
                for customer in customers
            ],
            "products": [
                {
                    "id": str(product.id),
                    "external_id": product.external_id,
                    "sku": product.sku,
                    "name": product.name,
                    "category": product.category,
                    "unit_price": self._decimal(product.unit_price),
                    "status": product.status,
                    "deleted_at": self._iso(product.deleted_at),
                }
                for product in products
            ],
            "orders": [
                {
                    "id": str(order.id),
                    "customer_id": str(order.customer_id),
                    "external_id": order.external_id,
                    "order_number": order.order_number,
                    "status": order.status,
                    "ordered_at": order.ordered_at.isoformat(),
                    "subtotal": self._decimal(order.subtotal),
                    "discount": self._decimal(order.discount),
                    "tax": self._decimal(order.tax),
                    "total": self._decimal(order.total),
                    "currency": order.currency,
                    "source": order.source,
                }
                for order in orders
            ],
            "order_items": [
                {
                    "id": str(item.id),
                    "order_id": str(item.order_id),
                    "product_id": str(item.product_id),
                    "product_name": item.product_name,
                    "sku": item.sku,
                    "quantity": item.quantity,
                    "unit_price": self._decimal(item.unit_price),
                    "discount": self._decimal(item.discount),
                    "line_total": self._decimal(item.line_total),
                }
                for item in items
            ],
        }

    @classmethod
    def export_view(cls, job: BackgroundJob) -> DataExportView:
        expires_at = cls._export_expires_at(job)
        ready = job.status == "succeeded" and expires_at > utc_now()
        return DataExportView(
            id=job.id,
            status="expired" if expires_at <= utc_now() else job.status,
            format="json",
            filename=cast(str | None, job.payload.get("filename")),
            content_type=cast(str | None, job.payload.get("content_type")),
            size_bytes=cast(int | None, job.payload.get("size_bytes")),
            content_sha256=cast(str | None, job.payload.get("content_sha256")),
            expires_at=expires_at,
            download_url=(
                f"/api/v1/organizations/current/data-exports/{job.id}/download" if ready else None
            ),
            created_at=job.created_at,
        )

    @classmethod
    def deletion_view(cls, job: BackgroundJob) -> OrganizationDeletionView:
        effective_at = cls._effective_deletion_at(job)
        return OrganizationDeletionView(
            job_id=job.id,
            status=job.status,
            requested_at=job.created_at,
            effective_deletion_at=effective_at,
            cancellable=job.status in {"queued", "running"} and effective_at > utc_now(),
        )

    @staticmethod
    def _effective_deletion_at(job: BackgroundJob) -> datetime:
        value = job.payload.get("effective_deletion_at")
        if not isinstance(value, str):
            raise DataManagementService._not_found()
        return datetime.fromisoformat(value)

    @staticmethod
    def _export_expires_at(job: BackgroundJob) -> datetime:
        value = job.payload.get("expires_at")
        if not isinstance(value, str):
            raise DataManagementService._not_found()
        return datetime.fromisoformat(value)

    @staticmethod
    def _decimal(value: Decimal) -> str:
        return format(value, "f")

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

    @staticmethod
    def _not_found() -> AppError:
        return AppError(
            status=404,
            code="resource_not_found",
            title="Resource not found",
            detail="The requested resource was not found.",
        )
