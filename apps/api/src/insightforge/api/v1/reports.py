from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response, status

from insightforge.api.dependencies import (
    TenantContext,
    get_report_service,
    require_csrf,
    require_permission,
)
from insightforge.api.rate_limits import REPORT_GENERATION, RequestRateLimitsDependency
from insightforge.core.policies import Permission
from insightforge.models.enums import ReportStatus, ReportType
from insightforge.schemas.common import (
    CollectionEnvelope,
    CollectionMeta,
    DataEnvelope,
    PaginationView,
)
from insightforge.schemas.reports import (
    ReportCreateRequest,
    ReportTemplateView,
    ReportView,
)
from insightforge.services.reports import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])
ReportContext = Annotated[
    TenantContext,
    require_permission(Permission.GENERATE_REPORTS),
]
ExportContext = Annotated[
    TenantContext,
    require_permission(Permission.EXPORT_REPORTS),
]
ReportServiceDependency = Annotated[ReportService, Depends(get_report_service)]


@router.get("/templates", response_model=CollectionEnvelope[ReportTemplateView])
async def report_templates(
    _context: ReportContext,
    service: ReportServiceDependency,
) -> CollectionEnvelope[ReportTemplateView]:
    templates = list(service.templates())
    return CollectionEnvelope(
        data=templates,
        meta=CollectionMeta(
            pagination=PaginationView.from_values(
                page=1,
                page_size=len(templates),
                total=len(templates),
            ),
            filters={},
        ),
    )


@router.get("", response_model=CollectionEnvelope[ReportView])
async def list_reports(
    context: ReportContext,
    service: ReportServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    report_type: Annotated[list[ReportType] | None, Query()] = None,
    report_status: Annotated[list[ReportStatus] | None, Query(alias="status")] = None,
) -> CollectionEnvelope[ReportView]:
    result = await service.list(
        context,
        page=page,
        page_size=page_size,
        report_types=tuple(value.value for value in report_type or []),
        statuses=tuple(value.value for value in report_status or []),
    )
    return CollectionEnvelope(
        data=result.items,
        meta=CollectionMeta(
            pagination=PaginationView.from_values(
                page=result.page,
                page_size=result.page_size,
                total=result.total,
            ),
            filters={
                "report_type": [value.value for value in report_type or []],
                "status": [value.value for value in report_status or []],
            },
        ),
    )


@router.post(
    "",
    response_model=DataEnvelope[ReportView],
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_csrf)],
)
async def create_report(
    payload: ReportCreateRequest,
    response: Response,
    context: ReportContext,
    service: ReportServiceDependency,
    rate_limits: RequestRateLimitsDependency,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> DataEnvelope[ReportView]:
    await rate_limits.enforce(
        scope=REPORT_GENERATION,
        subject=f"{context.organization_id}:{context.user_id}",
    )
    report, replayed = await service.create(
        context,
        payload,
        idempotency_key=idempotency_key,
    )
    response.headers["Location"] = f"/api/v1/reports/{report.id}"
    response.headers["Idempotency-Replayed"] = "true" if replayed else "false"
    return DataEnvelope(data=report)


@router.get("/{report_id}", response_model=DataEnvelope[ReportView])
async def get_report(
    report_id: uuid.UUID,
    context: ReportContext,
    service: ReportServiceDependency,
) -> DataEnvelope[ReportView]:
    return DataEnvelope(data=await service.get(context, report_id))


@router.get("/{report_id}/download")
async def download_report(
    report_id: uuid.UUID,
    context: ExportContext,
    service: ReportServiceDependency,
) -> Response:
    artifact = await service.download(context, report_id)
    return Response(
        content=artifact.payload,
        media_type=artifact.metadata.content_type,
        headers={
            "Content-Disposition": (f'attachment; filename="{artifact.metadata.filename}"'),
            "Digest": f"sha-256={artifact.metadata.content_sha256}",
        },
    )
