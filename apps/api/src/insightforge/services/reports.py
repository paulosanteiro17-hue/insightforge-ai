from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Literal, cast

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.core.pagination import PageResult
from insightforge.core.problems import AppError
from insightforge.core.time import utc_now
from insightforge.models import BackgroundJob, Report
from insightforge.repositories.reports import ReportRepository
from insightforge.schemas.analytics import AnalyticsView
from insightforge.schemas.reports import (
    ReportCreateRequest,
    ReportDownloadMetadata,
    ReportFilters,
    ReportFormatValue,
    ReportTemplateView,
    ReportTypeValue,
    ReportView,
)
from insightforge.services.idempotency import (
    IdempotencyService,
    canonical_request_hash,
    validate_uuid_idempotency_key,
)
from insightforge.storage.local import LocalPrivateStorage

if TYPE_CHECKING:
    from insightforge.api.dependencies import TenantContext

ReportScalar = str | int | float | bool | None
ReportRow = dict[str, ReportScalar]

_FORMULA_PREFIX = re.compile(r"^[\s]*[=+\-@]")
_SAFE_FILENAME_CHARACTER = re.compile(r"[^a-z0-9]+")

REPORT_TEMPLATES: tuple[ReportTemplateView, ...] = (
    ReportTemplateView(
        report_type="monthly_performance",
        label="Monthly performance",
        description="Compare core revenue, order, and customer performance metrics.",
        default_name="Monthly Performance Report",
        supported_formats=["json", "csv"],
    ),
    ReportTemplateView(
        report_type="sales",
        label="Sales",
        description="Review aggregate revenue and order volume over time.",
        default_name="Sales Report",
        supported_formats=["json", "csv"],
    ),
    ReportTemplateView(
        report_type="customer",
        label="Customer",
        description="Review aggregate customer acquisition over time.",
        default_name="Customer Report",
        supported_formats=["json", "csv"],
    ),
    ReportTemplateView(
        report_type="product_performance",
        label="Product performance",
        description="Compare aggregate product revenue, units, and revenue share.",
        default_name="Product Performance Report",
        supported_formats=["json", "csv"],
    ),
)


@dataclass(frozen=True, slots=True)
class ReportRows:
    columns: tuple[str, ...]
    rows: list[ReportRow]


@dataclass(frozen=True, slots=True)
class ReportArtifact:
    metadata: ReportDownloadMetadata
    payload: bytes


def _metric_value(analytics: AnalyticsView, key: str, field: str) -> ReportScalar:
    metric = analytics.metrics.get(key)
    if metric is None:
        return None
    return cast(ReportScalar, getattr(metric, field))


def build_report_rows(
    report_type: ReportTypeValue,
    analytics: AnalyticsView,
) -> ReportRows:
    """Build bounded aggregate rows from the canonical analytics view."""

    if report_type == "monthly_performance":
        labels = {
            "revenue_minor": "Revenue",
            "order_count": "Orders",
            "customers": "Customers",
            "new_customers": "New customers",
            "average_order_value_minor": "Average order value",
            "repeat_rate": "Repeat customer rate",
        }
        rows: list[ReportRow] = []
        for key, label in labels.items():
            rows.append(
                {
                    "metric": key,
                    "label": label,
                    "value": _metric_value(analytics, key, "value"),
                    "comparison_value": _metric_value(analytics, key, "comparison_value"),
                    "change_ratio": _metric_value(analytics, key, "change_ratio"),
                    "change_status": _metric_value(analytics, key, "change_status"),
                }
            )
        return ReportRows(
            columns=(
                "metric",
                "label",
                "value",
                "comparison_value",
                "change_ratio",
                "change_status",
            ),
            rows=rows,
        )

    if report_type == "sales":
        return ReportRows(
            columns=("period_start", "revenue_minor", "order_count"),
            rows=[
                {
                    "period_start": point.period_start.isoformat(),
                    "revenue_minor": point.revenue_minor,
                    "order_count": point.order_count,
                }
                for point in analytics.revenue_series
            ],
        )

    if report_type == "customer":
        return ReportRows(
            columns=("period_start", "new_customer_count"),
            rows=[
                {
                    "period_start": point.period_start.isoformat(),
                    "new_customer_count": point.new_customers,
                }
                for point in analytics.customer_acquisition
            ],
        )

    return ReportRows(
        columns=(
            "rank",
            "product",
            "revenue_minor",
            "units_sold",
            "revenue_share",
        ),
        rows=[
            {
                "rank": rank,
                "product": item.label,
                "revenue_minor": item.revenue_minor,
                "units_sold": item.units,
                "revenue_share": item.share_ratio,
            }
            for rank, item in enumerate(analytics.products, start=1)
        ],
    )


def formula_safe_csv_cell(value: ReportScalar) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    return f"'{text}" if _FORMULA_PREFIX.match(text) else text


def serialize_report_rows(
    *,
    report_format: ReportFormatValue,
    report_type: ReportTypeValue,
    report_name: str,
    filters: ReportFilters,
    source_revision: int,
    report_rows: ReportRows,
) -> tuple[bytes, Literal["application/json", "text/csv; charset=utf-8"]]:
    if report_format == "json":
        document = {
            "filters": filters.model_dump(mode="json"),
            "name": report_name,
            "report_type": report_type,
            "rows": report_rows.rows,
            "source_revision": source_revision,
        }
        return (
            json.dumps(
                document,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8"),
            "application/json",
        )

    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(report_rows.columns)
    for row in report_rows.rows:
        writer.writerow(formula_safe_csv_cell(row.get(column)) for column in report_rows.columns)
    return output.getvalue().encode("utf-8"), "text/csv; charset=utf-8"


def _report_view(row: Report) -> ReportView:
    return ReportView(
        id=row.id,
        report_type=cast(ReportTypeValue, row.report_type),
        name=row.name,
        filters=ReportFilters.model_validate(row.filters),
        status=cast(
            Literal["queued", "generating", "ready", "failed", "expired"],
            row.status,
        ),
        format=cast(ReportFormatValue, row.format),
        source_revision=row.source_revision,
        result_summary=row.result_summary,
        generated_at=row.generated_at,
        expires_at=row.expires_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _safe_report_filename(name: str, report_format: ReportFormatValue) -> str:
    stem = _SAFE_FILENAME_CHARACTER.sub("-", name.casefold()).strip("-")[:100]
    return f"{stem or 'report'}.{report_format}"


class ReportService:
    def __init__(
        self,
        db: AsyncSession,
        storage: LocalPrivateStorage,
        *,
        max_export_bytes: int = 20 * 1024 * 1024,
        max_export_rows: int = 50_000,
        retention: timedelta = timedelta(days=7),
    ) -> None:
        if max_export_bytes <= 0 or max_export_rows <= 0:
            raise ValueError("Report export limits must be greater than zero.")
        if retention <= timedelta(0):
            raise ValueError("Report retention must be greater than zero.")
        self.db = db
        self.storage = storage
        self.max_export_bytes = max_export_bytes
        self.max_export_rows = max_export_rows
        self.retention = retention
        self.repository = ReportRepository(db)
        self.idempotency = IdempotencyService(db)

    @staticmethod
    def templates() -> tuple[ReportTemplateView, ...]:
        return REPORT_TEMPLATES

    async def list(
        self,
        context: TenantContext,
        *,
        page: int,
        page_size: int,
        report_types: tuple[str, ...] = (),
        statuses: tuple[str, ...] = (),
    ) -> PageResult[ReportView]:
        result = await self.repository.list(
            context,
            page=page,
            page_size=page_size,
            report_types=report_types,
            statuses=statuses,
        )
        return PageResult(
            items=[_report_view(row) for row in result.items],
            page=page,
            page_size=page_size,
            total=result.total,
        )

    async def get(self, context: TenantContext, report_id: uuid.UUID) -> ReportView:
        row = await self.repository.get(context, report_id)
        if row is None:
            raise self._not_found()
        return _report_view(row)

    async def create(
        self,
        context: TenantContext,
        request: ReportCreateRequest,
        *,
        idempotency_key: str | None,
    ) -> tuple[ReportView, bool]:
        key = validate_uuid_idempotency_key(idempotency_key)
        request_hash = canonical_request_hash(
            {
                "report": request.model_dump(mode="json"),
                "source_revision": context.data_revision,
            }
        )
        scope = f"{context.organization_id}:{context.user_id}"
        operation = "create_report"
        replay_body = await self.idempotency.replay_response_body(
            scope_key=scope,
            operation=operation,
            key=key,
            request_hash=request_hash,
        )
        if replay_body is not None:
            return ReportView.model_validate(replay_body), True

        now = utc_now()
        report = Report(
            id=uuid.uuid4(),
            organization_id=context.organization_id,
            created_by_user_id=context.user_id,
            report_type=request.report_type,
            name=request.name,
            filters=request.filters.model_dump(mode="json"),
            status="queued",
            format=request.format,
            source_revision=context.data_revision,
            created_at=now,
            updated_at=now,
        )
        record = self.idempotency.start(
            scope_key=scope,
            actor_user_id=context.user_id,
            operation=operation,
            key=key,
            request_hash=request_hash,
        )
        self.db.add(report)
        try:
            await self.db.flush()
            self.db.add(
                BackgroundJob(
                    id=uuid.uuid4(),
                    organization_id=context.organization_id,
                    requested_by_user_id=context.user_id,
                    actor_type="demo" if context.is_demo else "user",
                    job_type="generate_report",
                    payload={"report_id": str(report.id)},
                    progress={"current": 0, "total": 1, "unit": "report"},
                    status="queued",
                    idempotency_record_id=record.id,
                )
            )
            await self.db.flush()
            view = _report_view(report)
            self.idempotency.complete(
                record,
                status_code=202,
                resource_type="report",
                resource_id=report.id,
                response_body=view.model_dump(mode="json"),
            )
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
            return ReportView.model_validate(replay_body), True
        except Exception:
            await self.db.rollback()
            raise
        return view, False

    async def generate_trusted(
        self,
        *,
        organization_id: uuid.UUID,
        report_id: uuid.UUID,
        analytics: AnalyticsView,
    ) -> ReportView:
        row = await self.repository.get_trusted(organization_id, report_id, for_update=True)
        if row is None:
            raise self._not_found()
        if row.status == "ready":
            return _report_view(row)
        if row.status == "expired":
            raise AppError(
                status=410,
                code="resource_expired",
                title="Report expired",
                detail="Create a new report to download current results.",
            )

        storage_key: str | None = None
        try:
            filters = ReportFilters.model_validate(row.filters)
            self._validate_canonical_analytics(row, filters, analytics)
            report_rows = build_report_rows(cast(ReportTypeValue, row.report_type), analytics)
            if len(report_rows.rows) > self.max_export_rows:
                raise AppError(
                    status=413,
                    code="export_too_large",
                    title="Export is too large",
                    detail="Narrow the report filters before generating another export.",
                )

            row.status = "generating"
            await self.db.flush()
            payload, content_type = serialize_report_rows(
                report_format=cast(ReportFormatValue, row.format),
                report_type=cast(ReportTypeValue, row.report_type),
                report_name=row.name,
                filters=filters,
                source_revision=row.source_revision,
                report_rows=report_rows,
            )
            storage_key = (
                f"reports/{organization_id.hex}/{row.id.hex}.{cast(ReportFormatValue, row.format)}"
            )
            stored = self.storage.store_bytes(
                storage_key,
                payload,
                max_bytes=self.max_export_bytes,
            )
            generated_at = utc_now()
            filename = _safe_report_filename(row.name, cast(ReportFormatValue, row.format))
            row.status = "ready"
            row.storage_key = stored.storage_key
            row.result_summary = {
                "content_sha256": stored.content_sha256,
                "content_type": content_type,
                "filename": filename,
                "row_count": len(report_rows.rows),
                "size_bytes": stored.size_bytes,
            }
            row.generated_at = generated_at
            row.expires_at = generated_at + self.retention
            await self.db.commit()
            return _report_view(row)
        except Exception:
            await self.db.rollback()
            self.storage.delete(storage_key)
            await self._mark_generation_failed(organization_id, report_id)
            raise

    async def download(
        self,
        context: TenantContext,
        report_id: uuid.UUID,
    ) -> ReportArtifact:
        row = await self.repository.get(context, report_id)
        if row is None:
            raise self._not_found()
        if (
            row.status != "ready"
            or row.storage_key is None
            or row.generated_at is None
            or row.result_summary is None
        ):
            raise AppError(
                status=409,
                code="report_not_ready",
                title="Report is not ready",
                detail="Wait for report generation to finish before downloading it.",
            )
        if row.expires_at is not None and row.expires_at <= utc_now():
            raise AppError(
                status=410,
                code="resource_expired",
                title="Report expired",
                detail="Create a new report to download current results.",
            )

        payload = self.storage.read_export_bytes(row.storage_key, max_bytes=self.max_export_bytes)
        expected_digest = row.result_summary.get("content_sha256")
        if (
            not isinstance(expected_digest, str)
            or hashlib.sha256(payload).hexdigest() != expected_digest
        ):
            raise AppError(
                status=410,
                code="export_file_invalid",
                title="Export is unavailable",
                detail="Create a new report to replace the invalid export.",
            )
        filename = row.result_summary.get("filename")
        content_type = row.result_summary.get("content_type")
        size_bytes = row.result_summary.get("size_bytes")
        if (
            not isinstance(filename, str)
            or content_type not in {"application/json", "text/csv; charset=utf-8"}
            or not isinstance(size_bytes, int)
            or size_bytes != len(payload)
        ):
            raise AppError(
                status=410,
                code="export_metadata_invalid",
                title="Export is unavailable",
                detail="Create a new report to replace the invalid export.",
            )
        metadata = ReportDownloadMetadata(
            report_id=row.id,
            filename=filename,
            content_type=cast(
                Literal["application/json", "text/csv; charset=utf-8"],
                content_type,
            ),
            size_bytes=size_bytes,
            content_sha256=expected_digest,
            generated_at=row.generated_at,
        )
        return ReportArtifact(metadata=metadata, payload=payload)

    async def cleanup_expired(self, *, limit: int = 100) -> int:
        """Expire reports and delete only their exact tenant-scoped artifact paths."""

        if limit <= 0 or limit > 1_000:
            raise ValueError("Report cleanup limit must be between 1 and 1,000.")
        now = utc_now()
        rows = list(
            (
                await self.db.scalars(
                    select(Report)
                    .where(
                        Report.status == "ready",
                        Report.expires_at.is_not(None),
                        Report.expires_at <= now,
                    )
                    .order_by(Report.expires_at.asc(), Report.id.asc())
                    .with_for_update(skip_locked=True)
                    .limit(limit)
                )
            ).all()
        )
        trusted_keys: list[str] = []
        for row in rows:
            expected_key = (
                f"reports/{row.organization_id.hex}/{row.id.hex}."
                f"{cast(ReportFormatValue, row.format)}"
            )
            key_is_trusted = row.storage_key is None or row.storage_key == expected_key
            if row.storage_key == expected_key:
                trusted_keys.append(expected_key)
            summary = dict(row.result_summary or {})
            summary.update(
                {
                    "artifact_purge_status": (
                        "purged" if key_is_trusted else "skipped_untrusted_key"
                    ),
                    "artifact_purged_at": now.isoformat(),
                }
            )
            row.status = "expired"
            row.storage_key = None
            row.result_summary = summary
        try:
            for storage_key in trusted_keys:
                self.storage.delete(storage_key)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        return len(trusted_keys)

    @staticmethod
    def _validate_canonical_analytics(
        row: Report,
        filters: ReportFilters,
        analytics: AnalyticsView,
    ) -> None:
        if analytics.source_revision != row.source_revision:
            raise AppError(
                status=409,
                code="report_source_changed",
                title="Report data changed",
                detail="Create a new report using the latest data revision.",
            )
        if (
            analytics.range.start != filters.date_from
            or analytics.range.end != filters.date_to
            or analytics.granularity != filters.granularity
        ):
            raise AppError(
                status=409,
                code="report_filter_mismatch",
                title="Report filters do not match",
                detail="Generate the report from its saved canonical filters.",
            )

    async def _mark_generation_failed(
        self,
        organization_id: uuid.UUID,
        report_id: uuid.UUID,
    ) -> None:
        try:
            row = await self.repository.get_trusted(organization_id, report_id, for_update=True)
            if row is not None and row.status != "ready":
                row.status = "failed"
                row.storage_key = None
                row.result_summary = {"error_code": "report_generation_failed"}
                row.generated_at = None
                row.expires_at = None
                await self.db.commit()
        except Exception:
            await self.db.rollback()

    @staticmethod
    def _not_found() -> AppError:
        return AppError(
            status=404,
            code="resource_not_found",
            title="Resource not found",
            detail="The requested resource was not found.",
        )
