from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from insightforge.schemas.common import StrictSchema

ReportTypeValue = Literal["monthly_performance", "sales", "customer", "product_performance"]
ReportFormatValue = Literal["json", "csv"]


class ReportFilters(StrictSchema):
    date_from: datetime
    date_to: datetime
    granularity: Literal["day", "week", "month"] = "day"

    @field_validator("date_from", "date_to")
    @classmethod
    def require_aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Report date filters must include a UTC offset.")
        return value

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.date_from >= self.date_to:
            raise ValueError("date_from must be earlier than date_to.")
        return self


class ReportCreateRequest(StrictSchema):
    report_type: ReportTypeValue
    name: str = Field(min_length=1, max_length=160)
    format: ReportFormatValue
    filters: ReportFilters

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Report name cannot be blank.")
        return normalized


class ReportTemplateView(StrictSchema):
    report_type: ReportTypeValue
    label: str
    description: str
    default_name: str
    supported_formats: list[ReportFormatValue]


class ReportView(StrictSchema):
    id: uuid.UUID
    report_type: ReportTypeValue
    name: str
    filters: ReportFilters
    status: Literal["queued", "generating", "ready", "failed", "expired"]
    format: ReportFormatValue
    source_revision: int
    result_summary: dict[str, object] | None
    generated_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReportDownloadMetadata(StrictSchema):
    report_id: uuid.UUID
    filename: str
    content_type: Literal["application/json", "text/csv; charset=utf-8"]
    size_bytes: int = Field(ge=0)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generated_at: datetime
