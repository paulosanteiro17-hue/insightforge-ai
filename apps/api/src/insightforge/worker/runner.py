from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from openai import AsyncOpenAI
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.analytics.ranges import DateTimeRange, EffectiveAnalyticsRange, Granularity
from insightforge.api.dependencies import CurrentIdentity, TenantContext
from insightforge.core.config import Settings, get_settings
from insightforge.core.logging import configure_logging
from insightforge.core.policies import Permission, permissions_for
from insightforge.core.problems import AppError
from insightforge.core.time import utc_now
from insightforge.db.session import get_engine, get_session_factory
from insightforge.models import (
    AuditLog,
    BackgroundJob,
    DataImport,
    Organization,
    OrganizationMember,
    Report,
    User,
    UserSession,
)
from insightforge.models.enums import DemoStatus, ImportStatus, OrganizationStatus, UserStatus
from insightforge.repositories.reports import ReportRepository
from insightforge.schemas.analytics import AnalyticsView
from insightforge.schemas.reports import ReportFilters
from insightforge.services.analytics import AnalyticsService
from insightforge.services.import_jobs import (
    ImportJobHandler,
    ImportProcessingFailure,
    SafeImportError,
    persist_import_failure,
)
from insightforge.services.intelligence import IntelligenceService
from insightforge.services.reports import ReportService
from insightforge.storage import LocalPrivateStorage

logger = logging.getLogger(__name__)
IMPORT_JOB_TYPES = ("validate_import", "apply_import")
DELETE_ORGANIZATION_JOB_TYPE = "delete_organization"
INTELLIGENCE_JOB_TYPES = ("generate_insights", "generate_weekly_summary")
REPORT_JOB_TYPE = "generate_report"
WORKER_JOB_TYPES = (
    *IMPORT_JOB_TYPES,
    DELETE_ORGANIZATION_JOB_TYPE,
    *INTELLIGENCE_JOB_TYPES,
    REPORT_JOB_TYPE,
)


@dataclass(frozen=True, slots=True)
class JobProcessingFailure(Exception):
    code: str
    safe_message: str
    retryable: bool = False


async def claim_next_job(settings: Settings) -> uuid.UUID | None:
    now = utc_now()
    async with get_session_factory(settings.database_url)() as db:
        exhausted = await db.scalar(
            select(BackgroundJob)
            .where(
                BackgroundJob.job_type.in_(WORKER_JOB_TYPES),
                BackgroundJob.status == "running",
                BackgroundJob.locked_until.is_not(None),
                BackgroundJob.locked_until < now,
                BackgroundJob.attempt_count >= BackgroundJob.max_attempts,
            )
            .order_by(BackgroundJob.locked_until.asc(), BackgroundJob.id.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if exhausted is not None:
            exhausted.status = "failed"
            exhausted.completed_at = now
            exhausted.locked_by = None
            exhausted.locked_until = None
            exhausted.last_error_code = "retry_limit_exhausted"
            exhausted.last_error_message = "The background job exhausted its retry limit."
            if exhausted.job_type in IMPORT_JOB_TYPES and exhausted.organization_id is not None:
                try:
                    exhausted_import_id = _payload_import_id(exhausted)
                except ImportProcessingFailure:
                    exhausted_import_id = None
                if exhausted_import_id is not None:
                    await persist_import_failure(
                        db,
                        organization_id=exhausted.organization_id,
                        import_id=exhausted_import_id,
                        code="retry_limit_exhausted",
                        message="The import job exhausted its retry limit.",
                        errors=[],
                        max_errors=settings.import_max_errors,
                    )
            await db.commit()
            return exhausted.id
        job = await db.scalar(
            select(BackgroundJob)
            .where(
                BackgroundJob.job_type.in_(WORKER_JOB_TYPES),
                BackgroundJob.attempt_count < BackgroundJob.max_attempts,
                or_(
                    (BackgroundJob.status == "queued") & (BackgroundJob.run_after <= now),
                    (BackgroundJob.status == "running")
                    & (BackgroundJob.locked_until.is_not(None))
                    & (BackgroundJob.locked_until < now),
                ),
            )
            .order_by(
                BackgroundJob.priority.desc(),
                BackgroundJob.run_after.asc(),
                BackgroundJob.id.asc(),
            )
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            await db.commit()
            return None
        job.status = "running"
        job.locked_by = settings.worker_id
        job.locked_until = now + timedelta(seconds=settings.worker_lease_seconds)
        job.attempt_count += 1
        job.started_at = job.started_at or now
        await db.commit()
        return job.id


def _payload_import_id(job: BackgroundJob) -> uuid.UUID:
    try:
        return uuid.UUID(str(job.payload["import_id"]))
    except (KeyError, ValueError) as exc:
        raise ImportProcessingFailure(
            "invalid_job_payload",
            "The import job payload is invalid.",
        ) from exc


def _payload_uuid(job: BackgroundJob, key: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(job.payload[key]))
    except (KeyError, ValueError) as exc:
        raise JobProcessingFailure(
            "invalid_job_payload",
            "The background job payload is invalid.",
        ) from exc


def _aware_datetime(value: object) -> datetime:
    if not isinstance(value, str):
        raise JobProcessingFailure(
            "invalid_job_payload",
            "The background job payload is invalid.",
        )
    try:
        result = datetime.fromisoformat(value)
    except ValueError as exc:
        raise JobProcessingFailure(
            "invalid_job_payload",
            "The background job payload is invalid.",
        ) from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise JobProcessingFailure(
            "invalid_job_payload",
            "The background job payload is invalid.",
        )
    return result


def _payload_analytics_range(job: BackgroundJob) -> EffectiveAnalyticsRange:
    payload = job.payload.get("analytics_range")
    if not isinstance(payload, dict):
        raise JobProcessingFailure(
            "invalid_job_payload",
            "The background job payload is invalid.",
        )
    granularity = payload.get("granularity")
    time_zone = payload.get("time_zone")
    if granularity not in {"day", "week", "month"} or not isinstance(time_zone, str):
        raise JobProcessingFailure(
            "invalid_job_payload",
            "The background job payload is invalid.",
        )
    comparison_start = payload.get("comparison_start")
    comparison_end = payload.get("comparison_end")
    if (comparison_start is None) != (comparison_end is None):
        raise JobProcessingFailure(
            "invalid_job_payload",
            "The background job payload is invalid.",
        )
    start = _aware_datetime(payload.get("start"))
    end = _aware_datetime(payload.get("end"))
    if start >= end:
        raise JobProcessingFailure(
            "invalid_job_payload",
            "The background job payload is invalid.",
        )
    try:
        ZoneInfo(time_zone)
    except ZoneInfoNotFoundError as exc:
        raise JobProcessingFailure(
            "invalid_job_payload",
            "The background job payload is invalid.",
        ) from exc
    return EffectiveAnalyticsRange(
        current=DateTimeRange(
            start=start,
            end=end,
        ),
        comparison=(
            DateTimeRange(
                start=_aware_datetime(comparison_start),
                end=_aware_datetime(comparison_end),
            )
            if comparison_start is not None
            else None
        ),
        granularity=cast(Granularity, granularity),
        time_zone=time_zone,
    )


async def _job_tenant_context(
    db: AsyncSession,
    job: BackgroundJob,
    *,
    permission: Permission,
) -> TenantContext:
    if job.organization_id is None or job.requested_by_user_id is None:
        raise JobProcessingFailure(
            "tenant_missing",
            "The background job has no organization context.",
        )
    row = (
        await db.execute(
            select(Organization, OrganizationMember, User)
            .join(
                OrganizationMember,
                OrganizationMember.organization_id == Organization.id,
            )
            .join(User, User.id == OrganizationMember.user_id)
            .where(
                Organization.id == job.organization_id,
                OrganizationMember.user_id == job.requested_by_user_id,
                OrganizationMember.removed_at.is_(None),
                User.status == UserStatus.ACTIVE.value,
            )
        )
    ).first()
    if row is None:
        raise JobProcessingFailure(
            "permission_denied",
            "The requester no longer has access to this organization.",
        )
    organization, membership, user = row
    if organization.status != OrganizationStatus.ACTIVE.value:
        raise JobProcessingFailure(
            "organization_unavailable",
            "The organization is not available for background processing.",
        )
    now = utc_now()
    if organization.is_demo and (
        organization.demo_status == DemoStatus.EXPIRED.value
        or organization.demo_expires_at is None
        or organization.demo_expires_at <= now
    ):
        raise JobProcessingFailure(
            "resource_expired",
            "The demo organization has expired.",
        )
    permission_set = permissions_for(membership.role, is_demo=organization.is_demo)
    if not permission_set.allows(permission):
        raise JobProcessingFailure(
            "permission_denied",
            "The requester no longer has permission to run this background job.",
        )
    worker_session = cast(
        UserSession,
        SimpleNamespace(is_demo=organization.is_demo),
    )
    return TenantContext(
        identity=CurrentIdentity(user=user, session=worker_session),
        organization=organization,
        membership=membership,
        permissions=permission_set,
    )


def _assert_source_revision(job: BackgroundJob, context: TenantContext) -> None:
    value = job.payload.get("source_revision")
    if not isinstance(value, int) or isinstance(value, bool):
        raise JobProcessingFailure(
            "invalid_job_payload",
            "The background job payload is invalid.",
        )
    if value != context.data_revision:
        raise JobProcessingFailure(
            "source_revision_changed",
            "The organization data changed after this job was requested.",
        )


async def process_import_job(settings: Settings, job_id: uuid.UUID) -> None:
    try:
        async with get_session_factory(settings.database_url)() as db:
            job = await db.get(BackgroundJob, job_id)
            if job is None or job.status != "running" or job.job_type not in IMPORT_JOB_TYPES:
                return
            if job.organization_id is None:
                raise ImportProcessingFailure(
                    "tenant_missing",
                    "The import job has no organization context.",
                )
            import_id = _payload_import_id(job)
            data_import = await ImportJobHandler(db, settings).repository.get_trusted(
                job.organization_id,
                import_id,
                for_update=True,
            )
            if data_import is None:
                raise ImportProcessingFailure(
                    "resource_not_found",
                    "The import resource is unavailable.",
                )
            handler = ImportJobHandler(db, settings)
            if job.job_type == "validate_import":
                await handler.validate(job, data_import)
            else:
                await handler.apply(job, data_import)
            if job.status != "cancelled":
                job.status = "succeeded"
                job.completed_at = utc_now()
            job.locked_by = None
            job.locked_until = None
            job.last_error_code = None
            job.last_error_message = None
            await db.commit()
    except ImportProcessingFailure as exc:
        await _record_failure(
            settings,
            job_id,
            code=exc.code,
            message=exc.safe_message,
            errors=exc.errors,
            retryable=False,
        )
    except Exception as exc:
        logger.error(
            "import_job_failed",
            extra={"job_id": str(job_id), "exception_type": type(exc).__name__},
        )
        await _record_failure(
            settings,
            job_id,
            code="temporary_worker_error",
            message="The import worker encountered a temporary error.",
            errors=[],
            retryable=True,
        )


async def _run_intelligence_generation(
    job: BackgroundJob,
    context: TenantContext,
    analytics: AnalyticsView,
    service: IntelligenceService,
) -> dict[str, object]:
    if job.job_type == "generate_insights":
        insights = await service.regenerate_insights(context, analytics)
        return {
            "insight_ids": [str(item.id) for item in insights],
            "insight_count": len(insights),
            "source_revision": analytics.source_revision,
        }
    summary = await service.regenerate_weekly_summary(context, analytics)
    return {
        "weekly_summary_id": str(summary.id),
        "week_start": summary.week_start.isoformat(),
        "week_end": summary.week_end.isoformat(),
        "source_revision": analytics.source_revision,
    }


async def process_intelligence_job(settings: Settings, job_id: uuid.UUID) -> None:
    try:
        async with get_session_factory(settings.database_url)() as db:
            job = await db.scalar(
                select(BackgroundJob)
                .where(
                    BackgroundJob.id == job_id,
                    BackgroundJob.job_type.in_(INTELLIGENCE_JOB_TYPES),
                    BackgroundJob.status == "running",
                )
                .with_for_update()
            )
            if job is None:
                return
            context = await _job_tenant_context(
                db,
                job,
                permission=Permission.ASK_ANALYTICS,
            )
            _assert_source_revision(job, context)
            effective_range = _payload_analytics_range(job)
            analytics = await AnalyticsService(db).snapshot(context, effective_range)
            if settings.ai_provider == "openai":
                api_key = settings.openai_api_key
                if api_key is None:
                    raise JobProcessingFailure(
                        "provider_configuration_error",
                        "The configured intelligence provider is unavailable.",
                    )
                async with AsyncOpenAI(api_key=api_key.get_secret_value()) as client:
                    service = IntelligenceService.with_openai(
                        db,
                        client,
                        timeout_seconds=settings.openai_timeout_seconds,
                        model=settings.openai_model,
                    )
                    result = await _run_intelligence_generation(
                        job,
                        context,
                        analytics,
                        service,
                    )
            else:
                result = await _run_intelligence_generation(
                    job,
                    context,
                    analytics,
                    IntelligenceService(db),
                )
            job.payload = dict(job.payload) | {"result": result}
            job.progress = {"current": 1, "total": 1, "unit": "generation"}
            job.status = "succeeded"
            job.completed_at = utc_now()
            job.locked_by = None
            job.locked_until = None
            job.last_error_code = None
            job.last_error_message = None
            await db.commit()
    except JobProcessingFailure as exc:
        await _record_failure(
            settings,
            job_id,
            code=exc.code,
            message=exc.safe_message,
            errors=[],
            retryable=exc.retryable,
        )
    except AppError as exc:
        await _record_failure(
            settings,
            job_id,
            code=exc.code,
            message="The intelligence generation request could not be completed.",
            errors=[],
            retryable=exc.status >= 500,
        )
    except Exception as exc:
        logger.error(
            "intelligence_job_failed",
            extra={"job_id": str(job_id), "exception_type": type(exc).__name__},
        )
        await _record_failure(
            settings,
            job_id,
            code="temporary_worker_error",
            message="The intelligence worker encountered a temporary error.",
            errors=[],
            retryable=True,
        )


async def process_report_job(settings: Settings, job_id: uuid.UUID) -> None:
    try:
        async with get_session_factory(settings.database_url)() as db:
            job = await db.scalar(
                select(BackgroundJob)
                .where(
                    BackgroundJob.id == job_id,
                    BackgroundJob.job_type == REPORT_JOB_TYPE,
                    BackgroundJob.status == "running",
                )
                .with_for_update()
            )
            if job is None:
                return
            context = await _job_tenant_context(
                db,
                job,
                permission=Permission.GENERATE_REPORTS,
            )
            report_id = _payload_uuid(job, "report_id")
            report = await ReportRepository(db).get_trusted(
                context.organization_id,
                report_id,
            )
            if report is None:
                raise JobProcessingFailure(
                    "resource_not_found",
                    "The report resource is unavailable.",
                )
            try:
                filters = ReportFilters.model_validate(report.filters)
            except ValidationError as exc:
                raise JobProcessingFailure(
                    "invalid_job_payload",
                    "The report filters are invalid.",
                ) from exc
            effective_range = EffectiveAnalyticsRange(
                current=DateTimeRange(
                    start=filters.date_from,
                    end=filters.date_to,
                ),
                comparison=None,
                granularity=filters.granularity,
                time_zone=context.time_zone,
            )
            analytics = await AnalyticsService(db).snapshot(context, effective_range)
            generated = await ReportService(
                db,
                LocalPrivateStorage(settings.private_storage_path),
                max_export_bytes=settings.export_max_bytes,
                max_export_rows=settings.export_max_rows,
                retention=timedelta(hours=settings.export_retention_hours),
            ).generate_trusted(
                organization_id=context.organization_id,
                report_id=report_id,
                analytics=analytics,
            )
            job.payload = dict(job.payload) | {
                "result": {
                    "report_id": str(generated.id),
                    "status": generated.status,
                    "source_revision": generated.source_revision,
                }
            }
            job.progress = {"current": 1, "total": 1, "unit": "report"}
            job.status = "succeeded"
            job.completed_at = utc_now()
            job.locked_by = None
            job.locked_until = None
            job.last_error_code = None
            job.last_error_message = None
            await db.commit()
    except JobProcessingFailure as exc:
        await _record_failure(
            settings,
            job_id,
            code=exc.code,
            message=exc.safe_message,
            errors=[],
            retryable=exc.retryable,
        )
    except AppError as exc:
        await _record_failure(
            settings,
            job_id,
            code=exc.code,
            message="The report generation request could not be completed.",
            errors=[],
            retryable=exc.status >= 500,
        )
    except Exception as exc:
        logger.error(
            "report_job_failed",
            extra={"job_id": str(job_id), "exception_type": type(exc).__name__},
        )
        await _record_failure(
            settings,
            job_id,
            code="temporary_worker_error",
            message="The report worker encountered a temporary error.",
            errors=[],
            retryable=True,
        )


async def process_delete_organization_job(settings: Settings, job_id: uuid.UUID) -> None:
    """Delete only the exact tenant bound to a due, uncancelled deletion job."""

    try:
        async with get_session_factory(settings.database_url)() as db:
            job = await db.scalar(
                select(BackgroundJob)
                .where(
                    BackgroundJob.id == job_id,
                    BackgroundJob.job_type == DELETE_ORGANIZATION_JOB_TYPE,
                    BackgroundJob.status == "running",
                )
                .with_for_update()
            )
            if job is None:
                return
            if job.organization_id is None:
                raise ImportProcessingFailure(
                    "tenant_missing",
                    "The deletion job has no organization context.",
                )
            effective_at = _deletion_effective_at(job)
            now = utc_now()
            if effective_at > now:
                job.status = "queued"
                job.run_after = effective_at
                job.locked_by = None
                job.locked_until = None
                await db.commit()
                return
            organization = await db.scalar(
                select(Organization).where(Organization.id == job.organization_id).with_for_update()
            )
            if organization is None:
                job.status = "succeeded"
                job.completed_at = now
                job.locked_by = None
                job.locked_until = None
                await db.commit()
                return
            if organization.status != OrganizationStatus.PENDING_DELETION.value:
                job.status = "cancelled"
                job.completed_at = now
                job.locked_by = None
                job.locked_until = None
                await db.commit()
                return
            organization_id = organization.id
            imports = list(
                (
                    await db.scalars(
                        select(DataImport).where(
                            DataImport.organization_id == organization_id,
                            DataImport.storage_key.is_not(None),
                        )
                    )
                ).all()
            )
            export_jobs = list(
                (
                    await db.scalars(
                        select(BackgroundJob).where(
                            BackgroundJob.organization_id == organization_id,
                            BackgroundJob.job_type == "export_organization_data",
                        )
                    )
                ).all()
            )
            reports = list(
                (
                    await db.scalars(
                        select(Report).where(
                            Report.organization_id == organization_id,
                            Report.storage_key.is_not(None),
                        )
                    )
                ).all()
            )
            report_prefix = f"reports/{organization_id.hex}/"
            storage = LocalPrivateStorage(settings.private_storage_path)
            for data_import in imports:
                expected_key = f"imports/{organization_id.hex}/{data_import.id.hex}.csv"
                if data_import.storage_key == expected_key:
                    storage.delete(expected_key)
            for export_job in export_jobs:
                storage_key = export_job.payload.get("storage_key")
                expected_key = f"exports/{organization_id.hex}/{export_job.id.hex}.json"
                if storage_key == expected_key:
                    storage.delete(expected_key)
            for report in reports:
                expected_key = f"{report_prefix}{report.id.hex}.{report.format}"
                if report.storage_key == expected_key:
                    storage.delete(expected_key)
            db.add(
                AuditLog(
                    id=uuid.uuid4(),
                    organization_id=organization_id,
                    actor_user_id=job.requested_by_user_id,
                    action="organization.deletion.completed",
                    resource_type="organization",
                    resource_id=organization_id,
                    request_id=job.last_error_request_id or uuid.uuid4(),
                    actor_type="system",
                    safe_metadata={"deletion_job_id": str(job.id)},
                )
            )
            await db.flush()
            await db.delete(organization)
            await db.commit()
    except ImportProcessingFailure as exc:
        await _record_failure(
            settings,
            job_id,
            code=exc.code,
            message=exc.safe_message,
            errors=[],
            retryable=False,
        )
    except Exception as exc:
        logger.error(
            "organization_deletion_job_failed",
            extra={"job_id": str(job_id), "exception_type": type(exc).__name__},
        )
        await _record_failure(
            settings,
            job_id,
            code="temporary_worker_error",
            message="The organization deletion worker encountered a temporary error.",
            errors=[],
            retryable=True,
        )


def _deletion_effective_at(job: BackgroundJob) -> datetime:
    value = job.payload.get("effective_deletion_at")
    if not isinstance(value, str):
        raise ImportProcessingFailure(
            "invalid_job_payload",
            "The deletion job payload is invalid.",
        )
    try:
        effective_at = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ImportProcessingFailure(
            "invalid_job_payload",
            "The deletion job payload is invalid.",
        ) from exc
    if effective_at.tzinfo is None or effective_at.utcoffset() is None:
        raise ImportProcessingFailure(
            "invalid_job_payload",
            "The deletion job payload is invalid.",
        )
    return effective_at


async def _record_failure(
    settings: Settings,
    job_id: uuid.UUID,
    *,
    code: str,
    message: str,
    errors: list[SafeImportError],
    retryable: bool,
) -> None:
    async with get_session_factory(settings.database_url)() as db:
        job = await db.scalar(
            select(BackgroundJob).where(BackgroundJob.id == job_id).with_for_update()
        )
        if job is None or job.status == "cancelled":
            return
        if retryable and job.attempt_count < job.max_attempts:
            delay_seconds = min(300, 2 ** max(1, job.attempt_count))
            job.status = "queued"
            job.run_after = utc_now() + timedelta(seconds=delay_seconds)
            job.locked_by = None
            job.locked_until = None
            job.last_error_code = code
            job.last_error_message = message
            await db.commit()
            return
        job.status = "failed"
        job.completed_at = utc_now()
        job.locked_by = None
        job.locked_until = None
        job.last_error_code = code
        job.last_error_message = message
        if job.job_type == REPORT_JOB_TYPE and job.organization_id is not None:
            try:
                report_id = _payload_uuid(job, "report_id")
            except JobProcessingFailure:
                report_id = None
            if report_id is not None:
                report = await ReportRepository(db).get_trusted(
                    job.organization_id,
                    report_id,
                    for_update=True,
                )
                if report is not None and report.status != "ready":
                    report.status = "failed"
                    report.storage_key = None
                    report.result_summary = {"error_code": code}
                    report.generated_at = None
                    report.expires_at = None
        if job.organization_id is not None:
            try:
                import_id = _payload_import_id(job)
            except ImportProcessingFailure:
                import_id = None
            if import_id is not None:
                await persist_import_failure(
                    db,
                    organization_id=job.organization_id,
                    import_id=import_id,
                    code=code,
                    message=message,
                    errors=errors,
                    max_errors=settings.import_max_errors,
                )
        await db.commit()


async def cleanup_expired_imports(settings: Settings) -> int:
    now = utc_now()
    storage_keys: list[str] = []
    known_storage_keys: set[str] = set()
    async with get_session_factory(settings.database_url)() as db:
        imports = list(
            (
                await db.scalars(
                    select(DataImport)
                    .where(
                        DataImport.expires_at <= now,
                        DataImport.status.not_in(
                            (ImportStatus.IMPORTING.value, ImportStatus.EXPIRED.value)
                        ),
                    )
                    .with_for_update(skip_locked=True)
                    .limit(100)
                )
            ).all()
        )
        for data_import in imports:
            data_import.status = ImportStatus.EXPIRED.value
            if data_import.storage_key:
                storage_keys.append(data_import.storage_key)
            data_import.storage_key = None
            jobs = (
                await db.scalars(
                    select(BackgroundJob).where(
                        BackgroundJob.organization_id == data_import.organization_id,
                        BackgroundJob.payload["import_id"].as_string() == str(data_import.id),
                        BackgroundJob.status.in_(("queued", "running")),
                    )
                )
            ).all()
            for job in jobs:
                job.status = "cancelled"
                job.completed_at = now
                job.locked_by = None
                job.locked_until = None
        known_storage_keys = {
            key
            for key in (
                await db.scalars(
                    select(DataImport.storage_key).where(DataImport.storage_key.is_not(None))
                )
            ).all()
            if key is not None
        }
        await db.commit()
    storage = LocalPrivateStorage(settings.private_storage_path)
    for storage_key in storage_keys:
        storage.delete(storage_key)
    orphan_count = storage.cleanup_orphans(
        known_storage_keys=known_storage_keys,
        temporary_before_epoch=(now - timedelta(hours=1)).timestamp(),
        retained_before_epoch=(now - timedelta(hours=settings.import_retention_hours)).timestamp(),
    )
    return len(storage_keys) + orphan_count


async def cleanup_expired_exports(settings: Settings) -> int:
    now = utc_now()
    storage = LocalPrivateStorage(settings.private_storage_path)
    removed = 0
    async with get_session_factory(settings.database_url)() as db:
        jobs = list(
            (
                await db.scalars(
                    select(BackgroundJob)
                    .where(
                        BackgroundJob.job_type == "export_organization_data",
                        BackgroundJob.payload.op("?")("storage_key"),
                        BackgroundJob.payload["expires_at"].as_string() <= now.isoformat(),
                    )
                    .order_by(BackgroundJob.created_at.asc())
                    .with_for_update(skip_locked=True)
                    .limit(500)
                )
            ).all()
        )
        for job in jobs:
            expires_at_value = job.payload.get("expires_at")
            if not isinstance(expires_at_value, str):
                continue
            try:
                expires_at = datetime.fromisoformat(expires_at_value)
            except ValueError:
                job.payload = {
                    key: value for key, value in job.payload.items() if key != "storage_key"
                } | {
                    "purge_error_code": "invalid_expiration",
                    "purged_at": now.isoformat(),
                }
                continue
            if expires_at.tzinfo is None or expires_at.utcoffset() is None:
                job.payload = {
                    key: value for key, value in job.payload.items() if key != "storage_key"
                } | {
                    "purge_error_code": "invalid_expiration",
                    "purged_at": now.isoformat(),
                }
                continue
            if expires_at > now:
                continue
            storage_key = job.payload.get("storage_key")
            expected_key = (
                f"exports/{job.organization_id.hex}/{job.id.hex}.json"
                if job.organization_id is not None
                else None
            )
            if storage_key == expected_key and expected_key is not None:
                storage.delete(expected_key)
                removed += 1
            job.payload = {
                key: value for key, value in job.payload.items() if key != "storage_key"
            } | {"purged_at": now.isoformat()}
        await db.commit()
    return removed


async def cleanup_expired_reports(settings: Settings) -> int:
    async with get_session_factory(settings.database_url)() as db:
        return await ReportService(
            db,
            LocalPrivateStorage(settings.private_storage_path),
            max_export_bytes=settings.export_max_bytes,
            max_export_rows=settings.export_max_rows,
            retention=timedelta(hours=settings.export_retention_hours),
        ).cleanup_expired(limit=500)


async def cleanup_expired_demo_organizations(settings: Settings) -> int:
    """Purge only expired demo tenants and their exact tenant-prefixed private files."""

    now = utc_now()
    storage = LocalPrivateStorage(settings.private_storage_path)
    removed = 0
    async with get_session_factory(settings.database_url)() as db:
        organizations = list(
            (
                await db.scalars(
                    select(Organization)
                    .where(
                        Organization.is_demo.is_(True),
                        Organization.demo_expires_at.is_not(None),
                        Organization.demo_expires_at <= now,
                    )
                    .order_by(Organization.demo_expires_at.asc(), Organization.id.asc())
                    .with_for_update(skip_locked=True)
                    .limit(50)
                )
            ).all()
        )
        for organization in organizations:
            organization_id = organization.id
            creator_user_id = organization.created_by_user_id
            demo_expires_at = organization.demo_expires_at
            if demo_expires_at is None:
                continue
            report_prefix = f"reports/{organization_id.hex}/"
            imports = list(
                (
                    await db.scalars(
                        select(DataImport).where(
                            DataImport.organization_id == organization_id,
                            DataImport.storage_key.is_not(None),
                        )
                    )
                ).all()
            )
            export_jobs = list(
                (
                    await db.scalars(
                        select(BackgroundJob).where(
                            BackgroundJob.organization_id == organization_id,
                            BackgroundJob.job_type == "export_organization_data",
                        )
                    )
                ).all()
            )
            reports = list(
                (
                    await db.scalars(
                        select(Report).where(
                            Report.organization_id == organization_id,
                            Report.storage_key.is_not(None),
                        )
                    )
                ).all()
            )
            for data_import in imports:
                expected_key = f"imports/{organization_id.hex}/{data_import.id.hex}.csv"
                if data_import.storage_key == expected_key:
                    storage.delete(expected_key)
            for export_job in export_jobs:
                export_storage_key = export_job.payload.get("storage_key")
                expected_key = f"exports/{organization_id.hex}/{export_job.id.hex}.json"
                if export_storage_key == expected_key:
                    storage.delete(expected_key)
            for report in reports:
                expected_key = f"{report_prefix}{report.id.hex}.{report.format}"
                if report.storage_key == expected_key:
                    storage.delete(expected_key)
            db.add(
                AuditLog(
                    id=uuid.uuid4(),
                    organization_id=organization_id,
                    actor_user_id=None,
                    action="demo.organization.expired",
                    resource_type="organization",
                    resource_id=organization_id,
                    request_id=uuid.uuid4(),
                    actor_type="system",
                    safe_metadata={"expired_at": demo_expires_at.isoformat()},
                )
            )
            await db.flush()
            await db.delete(organization)
            await db.flush()
            remaining_organizations = int(
                await db.scalar(
                    select(func.count())
                    .select_from(Organization)
                    .where(Organization.created_by_user_id == creator_user_id)
                )
                or 0
            )
            remaining_memberships = int(
                await db.scalar(
                    select(func.count())
                    .select_from(OrganizationMember)
                    .where(OrganizationMember.user_id == creator_user_id)
                )
                or 0
            )
            creator = await db.get(User, creator_user_id)
            expected_demo_email = f"demo-{creator_user_id.hex}@example.com"
            if (
                creator is not None
                and creator.email == expected_demo_email
                and remaining_organizations == 0
                and remaining_memberships == 0
            ):
                await db.delete(creator)
            removed += 1
        await db.commit()
    return removed


async def process_job(settings: Settings, job_id: uuid.UUID) -> None:
    async with get_session_factory(settings.database_url)() as db:
        job_type = await db.scalar(select(BackgroundJob.job_type).where(BackgroundJob.id == job_id))
    if job_type in IMPORT_JOB_TYPES:
        await process_import_job(settings, job_id)
    elif job_type == DELETE_ORGANIZATION_JOB_TYPE:
        await process_delete_organization_job(settings, job_id)
    elif job_type in INTELLIGENCE_JOB_TYPES:
        await process_intelligence_job(settings, job_id)
    elif job_type == REPORT_JOB_TYPE:
        await process_report_job(settings, job_id)


async def run_worker_once(settings: Settings) -> bool:
    job_id = await claim_next_job(settings)
    if job_id is None:
        return False
    await process_job(settings, job_id)
    return True


async def run_worker() -> None:
    settings = get_settings()
    logger.info("worker_started")
    cleanup_counter = 0
    try:
        while True:
            processed = await run_worker_once(settings)
            cleanup_counter += 1
            if cleanup_counter >= 60:
                await cleanup_expired_imports(settings)
                await cleanup_expired_exports(settings)
                await cleanup_expired_reports(settings)
                await cleanup_expired_demo_organizations(settings)
                cleanup_counter = 0
            if not processed:
                await asyncio.sleep(settings.worker_poll_seconds)
    finally:
        await get_engine(settings.database_url).dispose()
        logger.info("worker_stopped")


def main() -> None:
    configure_logging(get_settings())
    asyncio.run(run_worker())
