from __future__ import annotations

import uuid
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.core.problems import AppError
from insightforge.models import Organization, OrganizationMember, User
from insightforge.schemas.team import TeamMemberView


class TeamAccessService:
    """Shared tenant locking and safe team errors for member and invitation commands."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def lock_organization_and_actor(
        self,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        *,
        allowed_roles: set[str],
    ) -> tuple[Organization, OrganizationMember]:
        organization = await self.db.scalar(
            select(Organization).where(Organization.id == organization_id).with_for_update()
        )
        actor = await self.db.scalar(
            select(OrganizationMember)
            .where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == actor_user_id,
                OrganizationMember.removed_at.is_(None),
            )
            .with_for_update()
        )
        if organization is None or actor is None:
            raise self.not_found()
        if actor.role not in allowed_roles:
            raise self.permission_denied()
        return organization, actor

    async def member(
        self,
        organization_id: uuid.UUID,
        member_id: uuid.UUID,
        *,
        for_update: bool,
    ) -> OrganizationMember | None:
        statement = select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.id == member_id,
            OrganizationMember.removed_at.is_(None),
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(OrganizationMember | None, await self.db.scalar(statement))

    @staticmethod
    def member_view(member: OrganizationMember, user: User) -> TeamMemberView:
        return TeamMemberView(
            id=member.id,
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=member.role,
            joined_at=member.joined_at,
        )

    @staticmethod
    def reject_demo(organization: Organization, actor_is_demo: bool) -> None:
        if organization.is_demo or actor_is_demo:
            raise AppError(
                status=403,
                code="demo_policy_denied",
                title="Action unavailable in demo mode",
                detail="Demo workspaces cannot send or manage external invitations.",
            )

    @staticmethod
    def permission_denied() -> AppError:
        return AppError(
            status=403,
            code="permission_denied",
            title="Permission denied",
            detail="You do not have permission to perform this action.",
        )

    @staticmethod
    def not_found() -> AppError:
        return AppError(
            status=404,
            code="resource_not_found",
            title="Resource not found",
            detail="The requested resource was not found.",
        )

    @staticmethod
    def final_owner_error() -> AppError:
        return AppError(
            status=409,
            code="final_owner_required",
            title="Organization must keep an owner",
            detail="Transfer ownership before removing or changing the owner account.",
        )
