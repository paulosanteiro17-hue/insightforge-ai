from __future__ import annotations

import uuid
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.models import Organization, OrganizationMember, Subscription


class OrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def slug_exists(self, slug: str) -> bool:
        return (
            await self.session.scalar(select(Organization.id).where(Organization.slug == slug))
        ) is not None

    async def memberships_for_user(
        self, user_id: uuid.UUID
    ) -> list[tuple[Organization, OrganizationMember]]:
        rows = await self.session.execute(
            select(Organization, OrganizationMember)
            .join(
                OrganizationMember,
                OrganizationMember.organization_id == Organization.id,
            )
            .where(
                OrganizationMember.user_id == user_id,
                OrganizationMember.removed_at.is_(None),
            )
            .order_by(Organization.created_at.asc(), Organization.id.asc())
        )
        return [(row[0], row[1]) for row in rows.all()]

    async def subscription_for(self, organization_id: uuid.UUID) -> Subscription | None:
        return cast(
            Subscription | None,
            await self.session.scalar(
                select(Subscription).where(Subscription.organization_id == organization_id)
            ),
        )

    def add_organization(
        self,
        organization: Organization,
        membership: OrganizationMember,
        subscription: Subscription,
    ) -> None:
        self.session.add_all([organization, membership, subscription])
