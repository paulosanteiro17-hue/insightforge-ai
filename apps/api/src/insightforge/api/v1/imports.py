from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    Query,
    Response,
    UploadFile,
    status,
)

from insightforge.api.dependencies import (
    TenantContext,
    TenantContextDependency,
    get_import_service,
    require_csrf,
    require_permission,
)
from insightforge.core.policies import Permission
from insightforge.imports import CSV_HEADERS, CsvImportKind
from insightforge.models.enums import ImportStatus
from insightforge.schemas.common import (
    CollectionEnvelope,
    CollectionMeta,
    DataEnvelope,
    PaginationView,
)
from insightforge.schemas.imports import (
    ImportCommitRequest,
    ImportErrorView,
    ImportPreviewView,
    ImportView,
)
from insightforge.services.imports import ImportService

router = APIRouter(prefix="/imports", tags=["Imports"])
ImportServiceDependency = Annotated[ImportService, Depends(get_import_service)]
ImportContext = Annotated[TenantContext, require_permission(Permission.IMPORT_DATA)]


@router.get("", response_model=CollectionEnvelope[ImportView])
async def list_imports(
    context: ImportContext,
    service: ImportServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    kind: Annotated[list[CsvImportKind] | None, Query()] = None,
    import_status: Annotated[list[ImportStatus] | None, Query(alias="status")] = None,
    requested_by_user_id: uuid.UUID | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> CollectionEnvelope[ImportView]:
    result = await service.list(
        context,
        page=page,
        page_size=page_size,
        kinds=tuple(value.value for value in kind or []),
        statuses=tuple(value.value for value in import_status or []),
        requested_by_user_id=requested_by_user_id,
        created_from=created_from,
        created_to=created_to,
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
                "kind": [value.value for value in kind or []],
                "status": [value.value for value in import_status or []],
                "requested_by_user_id": (
                    str(requested_by_user_id) if requested_by_user_id else None
                ),
            },
        ),
    )


@router.post(
    "",
    response_model=DataEnvelope[ImportView],
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_csrf)],
)
async def create_import(
    response: Response,
    context: ImportContext,
    service: ImportServiceDependency,
    file: Annotated[UploadFile, File()],
    kind: Annotated[str, Form()],
    content_sha256: Annotated[str | None, Header(alias="X-Content-SHA256")] = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> DataEnvelope[ImportView]:
    data_import, replayed = await service.upload(
        context,
        kind_value=kind,
        upload=file,
        claimed_sha256=content_sha256,
        idempotency_key=idempotency_key,
    )
    response.headers["Location"] = f"/api/v1/imports/{data_import.id}"
    response.headers["Idempotency-Replayed"] = "true" if replayed else "false"
    return DataEnvelope(data=data_import)


@router.get("/templates/{kind}")
async def import_template(kind: CsvImportKind, _context: TenantContextDependency) -> Response:
    examples = {
        CsvImportKind.CUSTOMERS: (
            "CUS-001",
            "Avery Morgan",
            "avery@example.com",
            "Blue Oak Studio",
            "active",
            "2026-01-15T10:00:00Z",
        ),
        CsvImportKind.PRODUCTS: (
            "PRD-001",
            "ANALYTICS-PLAN",
            "Analytics Plan",
            "Software",
            "249.00",
            "active",
        ),
        CsvImportKind.ORDERS: (
            "ORD-001",
            "IF-1001",
            "CUS-001",
            "paid",
            "2026-02-01T12:00:00Z",
            "USD",
            "ANALYTICS-PLAN",
            "1",
            "249.00",
            "0.00",
            "0.00",
        ),
    }
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(CSV_HEADERS[kind])
    writer.writerow(examples[kind])
    return Response(
        content=stream.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{kind.value}-template.csv"'},
    )


@router.get("/{import_id}", response_model=DataEnvelope[ImportView])
async def get_import(
    import_id: uuid.UUID,
    context: ImportContext,
    service: ImportServiceDependency,
) -> DataEnvelope[ImportView]:
    return DataEnvelope(data=await service.get(context, import_id))


@router.get("/{import_id}/preview", response_model=DataEnvelope[ImportPreviewView])
async def get_import_preview(
    import_id: uuid.UUID,
    context: ImportContext,
    service: ImportServiceDependency,
) -> DataEnvelope[ImportPreviewView]:
    return DataEnvelope(data=await service.preview(context, import_id))


@router.get("/{import_id}/errors", response_model=CollectionEnvelope[ImportErrorView])
async def list_import_errors(
    import_id: uuid.UUID,
    context: ImportContext,
    service: ImportServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> CollectionEnvelope[ImportErrorView]:
    result = await service.errors(
        context,
        import_id,
        page=page,
        page_size=page_size,
    )
    return CollectionEnvelope(
        data=result.items,
        meta=CollectionMeta(
            pagination=PaginationView.from_values(
                page=result.page,
                page_size=result.page_size,
                total=result.total,
            ),
            filters={"import_id": str(import_id)},
        ),
    )


@router.post(
    "/{import_id}/commit",
    response_model=DataEnvelope[ImportView],
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_csrf)],
)
async def commit_import(
    import_id: uuid.UUID,
    payload: ImportCommitRequest,
    response: Response,
    context: ImportContext,
    service: ImportServiceDependency,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> DataEnvelope[ImportView]:
    data_import, replayed = await service.commit(
        context,
        import_id,
        payload,
        idempotency_key,
    )
    response.headers["Location"] = f"/api/v1/imports/{import_id}"
    response.headers["Idempotency-Replayed"] = "true" if replayed else "false"
    return DataEnvelope(data=data_import)


@router.post(
    "/{import_id}/cancel",
    response_model=DataEnvelope[ImportView],
    dependencies=[Depends(require_csrf)],
)
async def cancel_import(
    import_id: uuid.UUID,
    context: ImportContext,
    service: ImportServiceDependency,
) -> DataEnvelope[ImportView]:
    return DataEnvelope(data=await service.cancel(context, import_id))
