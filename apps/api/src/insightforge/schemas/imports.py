from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from insightforge.schemas.common import StrictSchema


class ImportView(StrictSchema):
    id: uuid.UUID
    kind: str
    status: str
    original_filename: str
    content_sha256: str
    size_bytes: int
    template_version: int
    mapping: dict[str, object]
    total_rows: int
    valid_rows: int
    invalid_rows: int
    imported_rows: int
    validation_summary: dict[str, object]
    progress: dict[str, object]
    created_at: datetime
    confirmed_at: datetime | None
    completed_at: datetime | None
    expires_at: datetime


class ImportPreviewView(StrictSchema):
    import_id: uuid.UUID
    headers: list[str]
    rows: list[dict[str, object]]
    formula_cells: list[dict[str, object]]
    rows_truncated: bool


class ImportErrorView(StrictSchema):
    id: uuid.UUID
    row_number: int
    column: str | None
    code: str
    message: str


class ImportCommitRequest(StrictSchema):
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    duplicate_policy: Literal["create_only"] = "create_only"


class ImportCancelRequest(StrictSchema):
    reason: str = Field(default="Cancelled by the user.", min_length=3, max_length=200)
