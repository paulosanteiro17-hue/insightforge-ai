from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.core.pagination import PageResult
from insightforge.models import Report

if TYPE_CHECKING:
    from insightforge.api.dependencies import TenantContext


class ReportRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        context: TenantContext,
        *,
        page: int,
        page_size: int,
        report_types: tuple[str, ...] = (),
        statuses: tuple[str, ...] = (),
    ) -> PageResult[Report]:
        filters = [Report.organization_id == context.organization_id]
        if report_types:
            filters.append(Report.report_type.in_(report_types))
        if statuses:
            filters.append(Report.status.in_(statuses))
        total = int(await self.db.scalar(select(func.count(Report.id)).where(*filters)) or 0)
        items = list(
            (
                await self.db.scalars(
                    select(Report)
                    .where(*filters)
                    .order_by(Report.created_at.desc(), Report.id.asc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return PageResult(items=items, page=page, page_size=page_size, total=total)

    async def get(
        self,
        context: TenantContext,
        report_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> Report | None:
        statement = select(Report).where(
            Report.organization_id == context.organization_id,
            Report.id == report_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(Report | None, await self.db.scalar(statement))

    async def get_trusted(
        self,
        organization_id: uuid.UUID,
        report_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> Report | None:
        statement = select(Report).where(
            Report.organization_id == organization_id,
            Report.id == report_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(Report | None, await self.db.scalar(statement))
