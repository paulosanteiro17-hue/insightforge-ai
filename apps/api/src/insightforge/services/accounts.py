from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.core.problems import AppError
from insightforge.core.security import hash_password, verify_password
from insightforge.core.time import utc_now
from insightforge.models import User, UserPreference, UserSession
from insightforge.services.auditing import add_audit_event


class AccountService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def preference_for(self, user_id: uuid.UUID) -> UserPreference:
        preference = await self.db.get(UserPreference, user_id)
        if preference is not None:
            return preference
        preference = UserPreference(user_id=user_id)
        self.db.add(preference)
        await self.db.commit()
        return preference

    async def update_profile(
        self,
        *,
        user: User,
        changes: dict[str, object],
        request_id: uuid.UUID,
        actor_is_demo: bool,
    ) -> User:
        locked_user = await self.db.scalar(select(User).where(User.id == user.id).with_for_update())
        if locked_user is None:
            raise self._not_found()
        changed_fields: list[str] = []
        for field in ("display_name", "locale", "time_zone"):
            if field in changes and changes[field] is not None:
                setattr(locked_user, field, changes[field])
                changed_fields.append(field)
        add_audit_event(
            self.db,
            organization_id=None,
            actor_user_id=locked_user.id,
            actor_is_demo=actor_is_demo,
            action="user.profile.updated",
            request_id=request_id,
            resource_type="user",
            resource_id=locked_user.id,
            metadata={"changed_fields": changed_fields},
        )
        await self.db.commit()
        return locked_user

    async def update_preferences(
        self,
        *,
        user: User,
        changes: dict[str, object],
        request_id: uuid.UUID,
        actor_is_demo: bool,
    ) -> UserPreference:
        preference = await self.db.scalar(
            select(UserPreference).where(UserPreference.user_id == user.id).with_for_update()
        )
        if preference is None:
            preference = UserPreference(user_id=user.id)
            self.db.add(preference)
        changed_fields: list[str] = []
        for field in (
            "weekly_summary_email",
            "insight_alert_email",
            "product_updates_email",
            "compact_tables",
        ):
            if field in changes and changes[field] is not None:
                setattr(preference, field, changes[field])
                changed_fields.append(field)
        add_audit_event(
            self.db,
            organization_id=None,
            actor_user_id=user.id,
            actor_is_demo=actor_is_demo,
            action="user.preferences.updated",
            request_id=request_id,
            resource_type="user",
            resource_id=user.id,
            metadata={"changed_fields": changed_fields},
        )
        await self.db.commit()
        return preference

    async def change_password(
        self,
        *,
        user: User,
        current_session: UserSession,
        current_password: str,
        new_password: str,
        request_id: uuid.UUID,
    ) -> None:
        if current_session.is_demo:
            raise AppError(
                status=403,
                code="demo_policy_denied",
                title="Action unavailable in demo mode",
                detail="Demo sessions cannot change account credentials.",
            )
        locked_user = await self.db.scalar(select(User).where(User.id == user.id).with_for_update())
        if locked_user is None:
            raise self._not_found()
        if not verify_password(current_password, locked_user.password_hash):
            raise AppError(
                status=400,
                code="invalid_current_password",
                title="Current password is incorrect",
                detail="Enter your current password and try again.",
            )
        locked_user.password_hash = hash_password(new_password)
        now = utc_now()
        await self.db.execute(
            update(UserSession)
            .where(
                UserSession.user_id == locked_user.id,
                UserSession.id != current_session.id,
                UserSession.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        add_audit_event(
            self.db,
            organization_id=None,
            actor_user_id=locked_user.id,
            actor_is_demo=False,
            action="user.password.changed",
            request_id=request_id,
            resource_type="user",
            resource_id=locked_user.id,
            metadata={"other_sessions_revoked": True},
        )
        await self.db.commit()

    @staticmethod
    def _not_found() -> AppError:
        return AppError(
            status=404,
            code="resource_not_found",
            title="Resource not found",
            detail="The requested resource was not found.",
        )
