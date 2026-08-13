from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import EmailStr

from insightforge.schemas.common import StrictSchema


class TeamMemberView(StrictSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    email: EmailStr
    display_name: str
    role: str
    joined_at: datetime


class TeamRoleUpdateRequest(StrictSchema):
    role: Literal["admin", "member"]


class InvitationCreateRequest(StrictSchema):
    email: EmailStr
    role: Literal["admin", "member"] = "member"


class InvitationView(StrictSchema):
    id: uuid.UUID
    email: EmailStr
    role: str
    status: Literal["pending", "expired", "accepted", "revoked"]
    invited_by_user_id: uuid.UUID
    expires_at: datetime
    created_at: datetime


class InvitationDeliveryView(InvitationView):
    acceptance_token: str


class InvitationPreviewView(StrictSchema):
    organization_name: str
    email_hint: str
    role: str
    expires_at: datetime


class InvitationAcceptedView(StrictSchema):
    organization_id: uuid.UUID
    organization_name: str
    member: TeamMemberView
