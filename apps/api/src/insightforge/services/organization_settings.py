from __future__ import annotations

import uuid
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.core.concurrency import ensure_version
from insightforge.core.problems import AppError
from insightforge.core.time import utc_now
from insightforge.models import (
    BackgroundJob,
    Customer,
    Order,
    Organization,
    OrganizationMember,
    Product,
)
from insightforge.models.enums import OnboardingState, OrganizationRole
from insightforge.schemas.organizations import OrganizationJobView
from insightforge.services.auditing import add_audit_event
from insightforge.services.idempotency import (
    IdempotencyService,
    canonical_request_hash,
    validate_idempotency_key,
)
from insightforge.services.seed import DemoSeedService


class OrganizationSettingsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.idempotency = IdempotencyService(db)

    async def update(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_is_demo: bool,
        changes: dict[str, object],
        expected_version: int,
        request_id: uuid.UUID,
    ) -> Organization:
        organization, _actor = await self._lock_organization_and_actor(
            organization_id,
            actor_user_id,
            allowed_roles={OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value},
        )
        ensure_version(organization.version, expected_version)
        currency = changes.get("reporting_currency")
        if currency is not None and currency != organization.reporting_currency:
            order_count = int(
                await self.db.scalar(
                    select(func.count())
                    .select_from(Order)
                    .where(Order.organization_id == organization_id)
                )
                or 0
            )
            if order_count:
                raise AppError(
                    status=409,
                    code="currency_change_requires_empty_organization",
                    title="Reporting currency cannot be changed",
                    detail="Remove transactional data before changing the reporting currency.",
                )
        changed_fields: list[str] = []
        timezone_changed = False
        for field in ("name", "slug", "reporting_currency", "timezone", "industry"):
            if field in changes and changes[field] is not None:
                value = changes[field]
                if getattr(organization, field) != value:
                    setattr(organization, field, value)
                    changed_fields.append(field)
                    timezone_changed = timezone_changed or field == "timezone"
        if changed_fields:
            organization.version += 1
            if timezone_changed:
                organization.data_revision += 1
            add_audit_event(
                self.db,
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                actor_is_demo=actor_is_demo,
                action="organization.settings.updated",
                request_id=request_id,
                resource_type="organization",
                resource_id=organization_id,
                metadata={"changed_fields": changed_fields},
            )
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise AppError(
                status=409,
                code="duplicate_resource",
                title="Organization slug is unavailable",
                detail="Choose a different organization slug.",
            ) from exc
        return organization

    async def complete_onboarding(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_is_demo: bool,
        source_job_id: uuid.UUID | None,
        empty_workspace: bool,
        request_id: uuid.UUID,
    ) -> Organization:
        organization, _actor = await self._lock_organization_and_actor(
            organization_id,
            actor_user_id,
            allowed_roles={OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value},
        )
        if organization.onboarding_state == OnboardingState.COMPLETE.value:
            return organization
        if source_job_id is not None:
            job = await self.db.scalar(
                select(BackgroundJob).where(
                    BackgroundJob.organization_id == organization_id,
                    BackgroundJob.id == source_job_id,
                    BackgroundJob.job_type.in_(("apply_import", "seed_demo_data")),
                )
            )
            if job is None:
                raise self._not_found()
            if job.status in {"queued", "running"}:
                raise AppError(
                    status=409,
                    code="onboarding_source_pending",
                    title="Onboarding source is still processing",
                    detail="Wait for the selected job to finish before completing onboarding.",
                )
            if job.status != "succeeded":
                raise AppError(
                    status=409,
                    code="onboarding_source_failed",
                    title="Onboarding source did not succeed",
                    detail="Choose a successful import or demo-data job.",
                )
        elif not empty_workspace:
            if await self._business_record_count(organization_id) == 0:
                raise AppError(
                    status=409,
                    code="onboarding_data_required",
                    title="Business data is required",
                    detail=(
                        "Import data, load demo data, or explicitly continue with an empty "
                        "workspace."
                    ),
                )
        organization.onboarding_state = OnboardingState.COMPLETE.value
        organization.version += 1
        add_audit_event(
            self.db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            actor_is_demo=actor_is_demo,
            action="organization.onboarding.completed",
            request_id=request_id,
            resource_type="organization",
            resource_id=organization_id,
            metadata={
                "source_job_id": str(source_job_id) if source_job_id is not None else None,
                "empty_workspace": empty_workspace,
            },
        )
        await self.db.commit()
        return organization

    async def provision_demo_data(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_is_demo: bool,
        request_id: uuid.UUID,
        idempotency_key: str | None,
    ) -> tuple[OrganizationJobView, bool]:
        organization, _actor = await self._lock_organization_and_actor(
            organization_id,
            actor_user_id,
            allowed_roles={OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value},
        )
        key = validate_idempotency_key(idempotency_key)
        request_hash = canonical_request_hash({"seed_version": "v1"})
        replayed_id = await self.idempotency.replay_resource_id(
            scope_key=f"organization:{organization_id}",
            operation="seed_demo_data",
            key=key,
            request_hash=request_hash,
        )
        if replayed_id is not None:
            job = await self._job(organization_id, replayed_id)
            if job is None:
                raise self._not_found()
            return self.job_view(job), True
        if await self._business_record_count(organization_id):
            raise AppError(
                status=409,
                code="demo_data_requires_empty_organization",
                title="Workspace is not empty",
                detail="Demo data can be loaded only before business records are added.",
            )
        now = utc_now()
        job = BackgroundJob(
            id=uuid.uuid4(),
            organization_id=organization_id,
            requested_by_user_id=actor_user_id,
            actor_type="demo" if actor_is_demo else "user",
            job_type="seed_demo_data",
            payload={"seed_version": "v1"},
            progress={"current": 0, "total": None, "unit": "records"},
            status="running",
            attempt_count=1,
            max_attempts=1,
            run_after=now,
            started_at=now,
        )
        self.db.add(job)
        record = self.idempotency.start(
            scope_key=f"organization:{organization_id}",
            actor_user_id=actor_user_id,
            operation="seed_demo_data",
            key=key,
            request_hash=request_hash,
        )
        await self.db.flush()
        summary = await DemoSeedService(self.db).seed(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            anchor=now,
            currency=organization.reporting_currency,
        )
        result: dict[str, object] = {
            "customers": summary.customers,
            "products": summary.products,
            "orders": summary.orders,
            "seed_version": "v1",
        }
        total = summary.customers + summary.products + summary.orders
        job.payload = {"seed_version": "v1", "result": result}
        job.progress = {"current": total, "total": total, "unit": "records"}
        job.status = "succeeded"
        job.completed_at = utc_now()
        organization.data_revision += 1
        organization.version += 1
        self.idempotency.complete(
            record,
            status_code=202,
            resource_type="background_job",
            resource_id=job.id,
        )
        add_audit_event(
            self.db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            actor_is_demo=actor_is_demo,
            action="organization.demo_data.loaded",
            request_id=request_id,
            resource_type="background_job",
            resource_id=job.id,
            metadata={"seed_version": "v1", "record_count": total},
        )
        await self.db.commit()
        return self.job_view(job), False

    async def demo_data_job(
        self, organization_id: uuid.UUID, job_id: uuid.UUID
    ) -> OrganizationJobView:
        job = await self._job(organization_id, job_id)
        if job is None or job.job_type != "seed_demo_data":
            raise self._not_found()
        return self.job_view(job)

    async def _lock_organization_and_actor(
        self,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        *,
        allowed_roles: set[str],
    ) -> tuple[Organization, OrganizationMember]:
        organization = await self.db.scalar(
            select(Organization).where(Organization.id == organization_id).with_for_update()
        )
        actor = await self.db.scalar(
            select(OrganizationMember)
            .where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == actor_user_id,
                OrganizationMember.removed_at.is_(None),
            )
            .with_for_update()
        )
        if organization is None or actor is None:
            raise self._not_found()
        if actor.role not in allowed_roles:
            raise AppError(
                status=403,
                code="permission_denied",
                title="Permission denied",
                detail="You do not have permission to perform this action.",
            )
        return organization, actor

    async def _business_record_count(self, organization_id: uuid.UUID) -> int:
        counts = []
        for model in (Customer, Product, Order):
            counts.append(
                int(
                    await self.db.scalar(
                        select(func.count())
                        .select_from(model)
                        .where(model.organization_id == organization_id)
                    )
                    or 0
                )
            )
        return sum(counts)

    async def _job(self, organization_id: uuid.UUID, job_id: uuid.UUID) -> BackgroundJob | None:
        return cast(
            BackgroundJob | None,
            await self.db.scalar(
                select(BackgroundJob).where(
                    BackgroundJob.organization_id == organization_id,
                    BackgroundJob.id == job_id,
                )
            ),
        )

    @staticmethod
    def job_view(job: BackgroundJob) -> OrganizationJobView:
        result = job.payload.get("result")
        return OrganizationJobView(
            id=job.id,
            job_type=job.job_type,
            status=job.status,
            progress=job.progress,
            result=cast(dict[str, object] | None, result),
            created_at=job.created_at,
            completed_at=job.completed_at,
        )

    @staticmethod
    def _not_found() -> AppError:
        return AppError(
            status=404,
            code="resource_not_found",
            title="Resource not found",
            detail="The requested resource was not found.",
        )
