from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, model_validator

from insightforge.schemas.auth import PreferenceView, UserView
from insightforge.schemas.common import StrictSchema


class CurrentUserView(UserView):
    preferences: PreferenceView


class ProfileUpdateRequest(StrictSchema):
    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    locale: str | None = Field(default=None, pattern=r"^en(?:-[A-Z]{2})?$")
    time_zone: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_update(self) -> ProfileUpdateRequest:
        if not self.model_fields_set:
            raise ValueError("Provide at least one profile field to update.")
        if self.display_name is not None:
            self.display_name = " ".join(self.display_name.split())
            if len(self.display_name) < 2:
                raise ValueError("Display name is too short.")
        if self.time_zone is not None:
            try:
                ZoneInfo(self.time_zone)
            except ZoneInfoNotFoundError as exc:
                raise ValueError("Time zone is not recognized.") from exc
        return self


class PreferenceUpdateRequest(StrictSchema):
    weekly_summary_email: bool | None = None
    insight_alert_email: bool | None = None
    product_updates_email: bool | None = None
    compact_tables: bool | None = None

    @model_validator(mode="after")
    def require_preference(self) -> PreferenceUpdateRequest:
        if not self.model_fields_set:
            raise ValueError("Provide at least one preference to update.")
        return self


class PasswordChangeRequest(StrictSchema):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)

    @model_validator(mode="after")
    def reject_unchanged_password(self) -> PasswordChangeRequest:
        if self.current_password == self.new_password:
            raise ValueError("The new password must be different from the current password.")
        return self
