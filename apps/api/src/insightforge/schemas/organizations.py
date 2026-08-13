from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator, model_validator

from insightforge.schemas.common import StrictSchema


class OrganizationCreateRequest(StrictSchema):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=80,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    reporting_currency: str = Field(default="USD", min_length=3, max_length=3)
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    industry: str | None = Field(default=None, max_length=80)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("reporting_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized = value.upper()
        if not normalized.isalpha():
            raise ValueError("Currency must be a three-letter ISO code.")
        return normalized

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Time zone is not recognized.") from exc
        return value


class OrganizationSummaryView(StrictSchema):
    id: uuid.UUID
    name: str
    slug: str
    role: str
    status: str
    onboarding_state: str
    reporting_currency: str
    timezone: str
    is_demo: bool
    demo_expires_at: datetime | None


class CurrentOrganizationView(StrictSchema):
    id: uuid.UUID
    name: str
    slug: str
    reporting_currency: str
    timezone: str
    industry: str | None
    status: str
    onboarding_state: str
    data_revision: int
    version: int
    role: str
    permissions: list[str]
    is_demo: bool
    demo_expires_at: datetime | None
    demo_status: str | None
    plan: str


class OrganizationUpdateRequest(StrictSchema):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=80,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    reporting_currency: str | None = Field(default=None, min_length=3, max_length=3)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    industry: str | None = Field(default=None, max_length=80)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value is not None else None

    @field_validator("reporting_currency")
    @classmethod
    def normalize_updated_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.upper()
        if not normalized.isalpha():
            raise ValueError("Currency must be a three-letter ISO code.")
        return normalized

    @field_validator("timezone")
    @classmethod
    def validate_updated_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Time zone is not recognized.") from exc
        return value

    @model_validator(mode="after")
    def require_update(self) -> OrganizationUpdateRequest:
        if not self.model_fields_set:
            raise ValueError("Provide at least one organization field to update.")
        return self


class OnboardingCompleteRequest(StrictSchema):
    source_job_id: uuid.UUID | None = None
    empty_workspace: bool = False

    @model_validator(mode="after")
    def validate_source(self) -> OnboardingCompleteRequest:
        if self.source_job_id is not None and self.empty_workspace:
            raise ValueError("Choose a source job or an empty workspace, not both.")
        return self


class OrganizationJobView(StrictSchema):
    id: uuid.UUID
    job_type: str
    status: str
    progress: dict[str, object]
    result: dict[str, object] | None
    created_at: datetime
    completed_at: datetime | None


class OrganizationDeletionRequest(StrictSchema):
    organization_name: str = Field(min_length=2, max_length=120)


class OrganizationDeletionView(StrictSchema):
    job_id: uuid.UUID
    status: str
    requested_at: datetime
    effective_deletion_at: datetime
    cancellable: bool


class DataExportRequest(StrictSchema):
    format: Literal["json"] = "json"


class DataExportView(StrictSchema):
    id: uuid.UUID
    status: str
    format: Literal["json"]
    filename: str | None
    content_type: str | None
    size_bytes: int | None
    content_sha256: str | None
    expires_at: datetime
    download_url: str | None
    created_at: datetime
