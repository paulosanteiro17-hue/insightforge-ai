from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from insightforge.schemas.common import StrictSchema

GenerationJobType = Literal["generate_insights", "generate_weekly_summary"]
GenerationJobStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]


class GenerationJobView(StrictSchema):
    id: uuid.UUID
    job_type: GenerationJobType
    status: GenerationJobStatus
    progress: dict[str, object]
    result: dict[str, object] | None
    error_code: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
