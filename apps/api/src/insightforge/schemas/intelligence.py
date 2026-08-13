from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import Field

from insightforge.schemas.common import StrictSchema


class InsightView(StrictSchema):
    id: uuid.UUID
    category: Literal["growth", "warning", "opportunity", "performance", "anomaly"]
    severity: Literal["info", "low", "medium", "high"]
    title: str
    description: str
    supporting_metrics: list[dict[str, object]]
    provider: str
    model: str | None
    prompt_version: str
    generation_mode: Literal["deterministic", "provider", "fallback"]
    status: Literal["active", "superseded", "failed"]
    source_revision: int
    period_start: date
    period_end: date
    generated_at: datetime
    expires_at: datetime | None
    superseded_at: datetime | None


class WeeklySummaryView(StrictSchema):
    id: uuid.UUID
    week_start: date
    week_end: date
    headline: str
    overview: str
    highlights: list[str]
    watch_items: list[str]
    provider: str
    model: str | None
    prompt_version: str
    generation_mode: Literal["deterministic", "provider", "fallback"]
    source_revision: int
    generated_at: datetime


class AskQuestionRequest(StrictSchema):
    question: str = Field(min_length=3, max_length=500)


class AnswerCitationView(StrictSchema):
    metric: str
    label: str
    value: int | float | str
    unit: str
    source: Literal["tenant_analytics"] = "tenant_analytics"


class AssistantAnswerView(StrictSchema):
    id: uuid.UUID
    question_redacted: str
    intent: str
    parameters: dict[str, object]
    answer: str
    answer_status: Literal["answered", "unsupported", "insufficient_data", "blocked"]
    applied_range: dict[str, object]
    confidence: float | None
    follow_ups: list[str]
    citations: list[AnswerCitationView]
    provider: str
    created_at: datetime


class AskCapabilityView(StrictSchema):
    intent: Literal[
        "sales_status",
        "top_product",
        "revenue_decline",
        "top_customers",
        "business_summary",
    ]
    label: str
    example: str


class AskCapabilitiesView(StrictSchema):
    capabilities: list[AskCapabilityView]
    safety_note: str = (
        "Questions are mapped to documented aggregate analytics. Arbitrary database queries "
        "and instructions are not supported."
    )
