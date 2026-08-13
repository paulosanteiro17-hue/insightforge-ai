from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.core.pagination import PageResult
from insightforge.core.time import utc_now
from insightforge.models import OrganizationMember, User
from insightforge.models.enums import OrganizationRole
from insightforge.schemas.team import TeamMemberView
from insightforge.services.auditing import add_audit_event
from insightforge.services.team_access import TeamAccessService


class TeamMemberService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.access = TeamAccessService(db)

    async def list_members(
        self,
        organization_id: uuid.UUID,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[TeamMemberView]:
        filters = (
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.removed_at.is_(None),
        )
        total = int(
            await self.db.scalar(
                select(func.count()).select_from(OrganizationMember).where(*filters)
            )
            or 0
        )
        rows = (
            await self.db.execute(
                select(OrganizationMember, User)
                .join(User, User.id == OrganizationMember.user_id)
                .where(*filters)
                .order_by(OrganizationMember.joined_at.asc(), OrganizationMember.id.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return PageResult(
            items=[self.access.member_view(row[0], row[1]) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def change_role(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_is_demo: bool,
        member_id: uuid.UUID,
        role: str,
        request_id: uuid.UUID,
    ) -> TeamMemberView:
        organization, _actor = await self.access.lock_organization_and_actor(
            organization_id,
            actor_user_id,
            allowed_roles={OrganizationRole.OWNER.value},
        )
        self.access.reject_demo(organization, actor_is_demo)
        member = await self.access.member(organization_id, member_id, for_update=True)
        if member is None:
            raise self.access.not_found()
        if member.role == OrganizationRole.OWNER.value:
            raise self.access.final_owner_error()
        member.role = role
        user = await self.db.get(User, member.user_id)
        if user is None:
            raise self.access.not_found()
        add_audit_event(
            self.db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            actor_is_demo=actor_is_demo,
            action="team.member.role_changed",
            request_id=request_id,
            resource_type="organization_member",
            resource_id=member.id,
            metadata={"new_role": role},
        )
        await self.db.commit()
        return self.access.member_view(member, user)

    async def remove_member(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_is_demo: bool,
        member_id: uuid.UUID,
        request_id: uuid.UUID,
    ) -> None:
        organization, actor = await self.access.lock_organization_and_actor(
            organization_id,
            actor_user_id,
            allowed_roles={OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value},
        )
        self.access.reject_demo(organization, actor_is_demo)
        member = await self.access.member(organization_id, member_id, for_update=True)
        if member is None:
            raise self.access.not_found()
        if member.role == OrganizationRole.OWNER.value:
            raise self.access.final_owner_error()
        if (
            actor.role == OrganizationRole.ADMIN.value
            and member.role != OrganizationRole.MEMBER.value
        ):
            raise self.access.permission_denied()
        member.removed_at = utc_now()
        add_audit_event(
            self.db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            actor_is_demo=actor_is_demo,
            action="team.member.removed",
            request_id=request_id,
            resource_type="organization_member",
            resource_id=member.id,
            metadata={"removed_role": member.role},
        )
        await self.db.commit()

    async def leave(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_is_demo: bool,
        request_id: uuid.UUID,
    ) -> None:
        organization, actor = await self.access.lock_organization_and_actor(
            organization_id,
            actor_user_id,
            allowed_roles={
                OrganizationRole.OWNER.value,
                OrganizationRole.ADMIN.value,
                OrganizationRole.MEMBER.value,
            },
        )
        self.access.reject_demo(organization, actor_is_demo)
        if actor.role == OrganizationRole.OWNER.value:
            raise self.access.final_owner_error()
        actor.removed_at = utc_now()
        add_audit_event(
            self.db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            actor_is_demo=actor_is_demo,
            action="team.member.left",
            request_id=request_id,
            resource_type="organization_member",
            resource_id=actor.id,
            metadata={"role": actor.role},
        )
        await self.db.commit()
