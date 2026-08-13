from __future__ import annotations

import uuid
from datetime import timedelta
from typing import TYPE_CHECKING

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from insightforge.core.config import Settings
from insightforge.core.pagination import PageResult, validate_time_range
from insightforge.core.problems import AppError
from insightforge.core.time import utc_now
from insightforge.imports import CSV_TEMPLATE_VERSION, CsvImportKind
from insightforge.models import BackgroundJob, DataImport
from insightforge.models.enums import ImportStatus
from insightforge.repositories.imports import ImportRepository
from insightforge.schemas.imports import (
    ImportCommitRequest,
    ImportErrorView,
    ImportPreviewView,
    ImportView,
)
from insightforge.services.idempotency import (
    IdempotencyService,
    canonical_request_hash,
    validate_idempotency_key,
)
from insightforge.storage import LocalPrivateStorage
from insightforge.storage.local import validate_content_sha256

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession

    from insightforge.api.dependencies import TenantContext


def _not_found() -> AppError:
    return AppError(
        status=404,
        code="resource_not_found",
        title="Resource not found",
        detail="The requested resource was not found.",
    )


class ImportService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.repository = ImportRepository(db)
        self.idempotency = IdempotencyService(db)
        self.storage = LocalPrivateStorage(settings.private_storage_path)

    async def _view(self, data_import: DataImport) -> ImportView:
        job = await self.repository.latest_job(data_import.organization_id, data_import.id)
        return ImportView(
            id=data_import.id,
            kind=data_import.kind,
            status=data_import.status,
            original_filename=data_import.original_filename,
            content_sha256=data_import.content_sha256,
            size_bytes=data_import.size_bytes,
            template_version=data_import.template_version,
            mapping=data_import.mapping,
            total_rows=data_import.total_rows,
            valid_rows=data_import.valid_rows,
            invalid_rows=data_import.invalid_rows,
            imported_rows=data_import.imported_rows,
            validation_summary=data_import.validation_summary,
            progress=(
                job.progress
                if job is not None
                else {
                    "current": data_import.imported_rows,
                    "total": data_import.total_rows,
                    "unit": "rows",
                }
            ),
            created_at=data_import.created_at,
            confirmed_at=data_import.confirmed_at,
            completed_at=data_import.completed_at,
            expires_at=data_import.expires_at,
        )

    async def list(
        self,
        context: TenantContext,
        *,
        page: int,
        page_size: int,
        kinds: tuple[str, ...],
        statuses: tuple[str, ...],
        requested_by_user_id: uuid.UUID | None,
        created_from: datetime | None,
        created_to: datetime | None,
    ) -> PageResult[ImportView]:
        validate_time_range(created_from, created_to)
        result = await self.repository.list(
            context,
            page=page,
            page_size=page_size,
            kinds=kinds,
            statuses=statuses,
            requested_by_user_id=requested_by_user_id,
            created_from=created_from,
            created_to=created_to,
        )
        return PageResult(
            items=[await self._view(item) for item in result.items],
            page=page,
            page_size=page_size,
            total=result.total,
        )

    async def get(self, context: TenantContext, import_id: uuid.UUID) -> ImportView:
        data_import = await self.repository.get(context, import_id)
        if data_import is None:
            raise _not_found()
        return await self._view(data_import)

    async def upload(
        self,
        context: TenantContext,
        *,
        kind_value: str,
        upload: UploadFile,
        claimed_sha256: str | None,
        idempotency_key: str | None,
    ) -> tuple[ImportView, bool]:
        try:
            kind = CsvImportKind(kind_value)
        except ValueError as exc:
            raise AppError(
                status=422,
                code="validation_error",
                title="Request validation failed",
                detail="Choose customers, products, or orders as the import kind.",
            ) from exc
        content_sha256 = validate_content_sha256(claimed_sha256)
        key = validate_idempotency_key(idempotency_key)
        request_hash = canonical_request_hash(
            {"kind": kind.value, "content_sha256": content_sha256}
        )
        scope = f"{context.organization.id}:{context.identity.user.id}"
        operation = "create_import"
        replay_body = await self.idempotency.replay_response_body(
            scope_key=scope,
            operation=operation,
            key=key,
            request_hash=request_hash,
        )
        if replay_body is not None:
            await upload.close()
            return ImportView.model_validate(replay_body), True

        import_id = uuid.uuid4()
        stored = await self.storage.store_upload(
            organization_id=context.organization.id,
            import_id=import_id,
            upload=upload,
            expected_sha256=content_sha256,
            max_bytes=self.settings.upload_max_bytes,
        )
        now = utc_now()
        data_import = DataImport(
            id=import_id,
            organization_id=context.organization.id,
            requested_by_user_id=context.identity.user.id,
            kind=kind.value,
            status=ImportStatus.VALIDATING.value,
            original_filename=stored.original_filename,
            storage_key=stored.storage_key,
            content_sha256=stored.content_sha256,
            size_bytes=stored.size_bytes,
            template_version=CSV_TEMPLATE_VERSION,
            mapping={},
            validation_summary={},
            created_at=now,
            expires_at=now + timedelta(hours=self.settings.import_retention_hours),
        )
        record = self.idempotency.start(
            scope_key=scope,
            actor_user_id=context.identity.user.id,
            operation=operation,
            key=key,
            request_hash=request_hash,
        )
        self.db.add(data_import)
        try:
            await self.db.flush()
            job = BackgroundJob(
                id=uuid.uuid4(),
                organization_id=context.organization.id,
                requested_by_user_id=context.identity.user.id,
                actor_type="demo" if context.identity.session.is_demo else "user",
                job_type="validate_import",
                payload={"import_id": str(import_id)},
                progress={"current": 0, "total": None, "unit": "rows"},
                status="queued",
                idempotency_record_id=record.id,
            )
            self.db.add(job)
            await self.db.flush()
            view = await self._view(data_import)
            self.idempotency.complete(
                record,
                status_code=202,
                resource_type="data_import",
                resource_id=import_id,
                response_body=view.model_dump(mode="json"),
            )
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            self.storage.delete(stored.storage_key)
            replay_body = await self.idempotency.replay_response_body(
                scope_key=scope,
                operation=operation,
                key=key,
                request_hash=request_hash,
            )
            if replay_body is None:
                raise
            return ImportView.model_validate(replay_body), True
        except Exception:
            await self.db.rollback()
            self.storage.delete(stored.storage_key)
            raise
        return view, False

    async def preview(
        self,
        context: TenantContext,
        import_id: uuid.UUID,
    ) -> ImportPreviewView:
        data_import = await self.repository.get(context, import_id)
        if data_import is None:
            raise _not_found()
        summary = data_import.validation_summary
        headers = summary.get("headers", [])
        preview_rows = summary.get("preview_rows", [])
        formula_cells = summary.get("formula_cells", [])
        return ImportPreviewView(
            import_id=import_id,
            headers=[str(value) for value in headers] if isinstance(headers, list) else [],
            rows=[dict(value) for value in preview_rows if isinstance(value, dict)]
            if isinstance(preview_rows, list)
            else [],
            formula_cells=[dict(value) for value in formula_cells if isinstance(value, dict)]
            if isinstance(formula_cells, list)
            else [],
            rows_truncated=bool(summary.get("preview_rows_truncated", False)),
        )

    async def errors(
        self,
        context: TenantContext,
        import_id: uuid.UUID,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[ImportErrorView]:
        if await self.repository.get(context, import_id) is None:
            raise _not_found()
        result = await self.repository.errors(
            context,
            import_id,
            page=page,
            page_size=page_size,
        )
        return PageResult(
            items=[
                ImportErrorView(
                    id=item.id,
                    row_number=item.row_number,
                    column=item.column_name,
                    code=item.error_code,
                    message=item.safe_message,
                )
                for item in result.items
            ],
            page=page,
            page_size=page_size,
            total=result.total,
        )

    async def commit(
        self,
        context: TenantContext,
        import_id: uuid.UUID,
        payload: ImportCommitRequest,
        idempotency_key: str | None,
    ) -> tuple[ImportView, bool]:
        key = validate_idempotency_key(idempotency_key)
        request_hash = canonical_request_hash(
            {
                "import_id": str(import_id),
                "content_sha256": payload.content_sha256,
                "duplicate_policy": payload.duplicate_policy,
            }
        )
        scope = f"{context.organization.id}:{context.identity.user.id}"
        operation = f"commit_import:{import_id}"
        replay_body = await self.idempotency.replay_response_body(
            scope_key=scope,
            operation=operation,
            key=key,
            request_hash=request_hash,
        )
        if replay_body is not None:
            return ImportView.model_validate(replay_body), True
        data_import = await self.repository.get(context, import_id, for_update=True)
        if data_import is None:
            raise _not_found()
        if data_import.content_sha256 != payload.content_sha256:
            raise AppError(
                status=409,
                code="validation_revision_changed",
                title="Validated file changed",
                detail="Refresh the import and confirm its current content digest.",
            )
        if data_import.status != ImportStatus.READY.value:
            raise AppError(
                status=409,
                code="import_not_ready",
                title="Import is not ready",
                detail="Only a successfully validated import can be committed.",
            )
        now = utc_now()
        record = self.idempotency.start(
            scope_key=scope,
            actor_user_id=context.identity.user.id,
            operation=operation,
            key=key,
            request_hash=request_hash,
        )
        data_import.status = ImportStatus.IMPORTING.value
        data_import.confirmed_at = now
        await self.db.flush()
        job = BackgroundJob(
            id=uuid.uuid4(),
            organization_id=context.organization.id,
            requested_by_user_id=context.identity.user.id,
            actor_type="demo" if context.identity.session.is_demo else "user",
            job_type="apply_import",
            payload={
                "import_id": str(import_id),
                "content_sha256": payload.content_sha256,
                "duplicate_policy": payload.duplicate_policy,
            },
            progress={"current": 0, "total": data_import.total_rows, "unit": "rows"},
            status="queued",
            idempotency_record_id=record.id,
        )
        self.db.add(job)
        await self.db.flush()
        view = await self._view(data_import)
        self.idempotency.complete(
            record,
            status_code=202,
            resource_type="data_import",
            resource_id=import_id,
            response_body=view.model_dump(mode="json"),
        )
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            replay_body = await self.idempotency.replay_response_body(
                scope_key=scope,
                operation=operation,
                key=key,
                request_hash=request_hash,
            )
            if replay_body is None:
                raise
            return ImportView.model_validate(replay_body), True
        return view, False

    async def cancel(self, context: TenantContext, import_id: uuid.UUID) -> ImportView:
        data_import = await self.repository.get(context, import_id, for_update=True)
        if data_import is None:
            raise _not_found()
        if data_import.status in {
            ImportStatus.COMPLETED.value,
            ImportStatus.CANCELLED.value,
            ImportStatus.EXPIRED.value,
        }:
            return await self._view(data_import)
        data_import.status = ImportStatus.CANCELLED.value
        jobs = (
            await self.db.scalars(
                select(BackgroundJob).where(
                    BackgroundJob.organization_id == context.organization.id,
                    BackgroundJob.payload["import_id"].as_string() == str(import_id),
                    BackgroundJob.status.in_(("queued", "running")),
                )
            )
        ).all()
        for job in jobs:
            job.status = "cancelled"
            job.locked_by = None
            job.locked_until = None
            job.completed_at = utc_now()
        await self.db.commit()
        return await self._view(data_import)
