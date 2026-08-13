from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from insightforge.schemas.common import StrictSchema
from insightforge.schemas.organizations import OrganizationSummaryView


class RegisterRequest(StrictSchema):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=2, max_length=120)

    @field_validator("display_name")
    @classmethod
    def clean_display_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Display name is too short.")
        return normalized


class LoginRequest(StrictSchema):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class DemoSessionRequest(StrictSchema):
    pass


class PasswordResetRequest(StrictSchema):
    email: EmailStr


class PasswordResetRequestView(StrictSchema):
    message: str
    recovery_path: str | None = None


class PasswordResetConfirmationRequest(StrictSchema):
    token: str = Field(min_length=32, max_length=512)
    password: str = Field(min_length=12, max_length=128)


class UserView(StrictSchema):
    id: uuid.UUID
    email: EmailStr
    display_name: str
    status: str
    email_verified_at: datetime | None
    locale: str
    time_zone: str
    created_at: datetime


class PreferenceView(StrictSchema):
    weekly_summary_email: bool
    insight_alert_email: bool
    product_updates_email: bool
    compact_tables: bool


class SessionMetadataView(StrictSchema):
    id: uuid.UUID
    is_demo: bool
    idle_expires_at: datetime
    absolute_expires_at: datetime


class SessionView(StrictSchema):
    user: UserView
    session: SessionMetadataView
    organizations: list[OrganizationSummaryView]


class CsrfTokenView(StrictSchema):
    csrf_token: str
