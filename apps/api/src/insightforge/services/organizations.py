from __future__ import annotations

import re
import unicodedata
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.core.problems import AppError
from insightforge.models import Organization, OrganizationMember, Subscription, User
from insightforge.models.enums import OnboardingState, OrganizationRole
from insightforge.repositories.organizations import OrganizationRepository


def slugify(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.casefold()).strip("-")
    return slug[:80] or "organization"


class OrganizationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = OrganizationRepository(db)

    async def create(
        self,
        *,
        user: User,
        name: str,
        slug: str | None,
        reporting_currency: str,
        timezone: str,
        industry: str | None,
    ) -> tuple[Organization, OrganizationMember]:
        candidate = slug or slugify(name)
        if await self.repository.slug_exists(candidate):
            if slug is not None:
                raise self._slug_conflict()
            candidate = f"{candidate[:67]}-{uuid.uuid4().hex[:12]}"

        organization_id = uuid.uuid4()
        organization = Organization(
            id=organization_id,
            name=name,
            slug=candidate,
            reporting_currency=reporting_currency,
            timezone=timezone,
            industry=industry,
            onboarding_state=OnboardingState.DATA.value,
            created_by_user_id=user.id,
        )
        membership = OrganizationMember(
            id=uuid.uuid4(),
            organization_id=organization_id,
            user_id=user.id,
            role=OrganizationRole.OWNER.value,
        )
        subscription = Subscription(
            id=uuid.uuid4(),
            organization_id=organization_id,
            plan="free",
            status="active",
            provider="demo",
        )
        self.repository.add_organization(organization, membership, subscription)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise self._slug_conflict() from exc
        return organization, membership

    async def list_for_user(
        self, user_id: uuid.UUID
    ) -> list[tuple[Organization, OrganizationMember]]:
        return await self.repository.memberships_for_user(user_id)

    @staticmethod
    def _slug_conflict() -> AppError:
        return AppError(
            status=409,
            code="duplicate_resource",
            title="Organization slug is unavailable",
            detail="Choose a different organization slug.",
        )
