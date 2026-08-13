from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.core.pagination import PageResult
from insightforge.models import BackgroundJob, DataImport, DataImportError

if TYPE_CHECKING:
    from insightforge.api.dependencies import TenantContext


class ImportRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

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
    ) -> PageResult[DataImport]:
        filters = [DataImport.organization_id == context.organization.id]
        if kinds:
            filters.append(DataImport.kind.in_(kinds))
        if statuses:
            filters.append(DataImport.status.in_(statuses))
        if requested_by_user_id:
            filters.append(DataImport.requested_by_user_id == requested_by_user_id)
        if created_from:
            filters.append(DataImport.created_at >= created_from)
        if created_to:
            filters.append(DataImport.created_at < created_to)
        total = int(await self.db.scalar(select(func.count(DataImport.id)).where(*filters)) or 0)
        rows = list(
            (
                await self.db.scalars(
                    select(DataImport)
                    .where(*filters)
                    .order_by(DataImport.created_at.desc(), DataImport.id.asc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return PageResult(items=rows, page=page, page_size=page_size, total=total)

    async def get(
        self,
        context: TenantContext,
        import_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> DataImport | None:
        statement = select(DataImport).where(
            DataImport.organization_id == context.organization.id,
            DataImport.id == import_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(DataImport | None, await self.db.scalar(statement))

    async def get_trusted(
        self,
        organization_id: uuid.UUID,
        import_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> DataImport | None:
        statement = select(DataImport).where(
            DataImport.organization_id == organization_id,
            DataImport.id == import_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(DataImport | None, await self.db.scalar(statement))

    async def errors(
        self,
        context: TenantContext,
        import_id: uuid.UUID,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[DataImportError]:
        filters = (
            DataImportError.organization_id == context.organization.id,
            DataImportError.import_id == import_id,
        )
        total = int(
            await self.db.scalar(select(func.count(DataImportError.id)).where(*filters)) or 0
        )
        rows = list(
            (
                await self.db.scalars(
                    select(DataImportError)
                    .where(*filters)
                    .order_by(DataImportError.row_number.asc(), DataImportError.id.asc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return PageResult(items=rows, page=page, page_size=page_size, total=total)

    async def latest_job(
        self,
        organization_id: uuid.UUID,
        import_id: uuid.UUID,
    ) -> BackgroundJob | None:
        return cast(
            BackgroundJob | None,
            await self.db.scalar(
                select(BackgroundJob)
                .where(
                    BackgroundJob.organization_id == organization_id,
                    BackgroundJob.payload["import_id"].as_string() == str(import_id),
                )
                .order_by(BackgroundJob.created_at.desc(), BackgroundJob.id.asc())
                .limit(1)
            ),
        )
