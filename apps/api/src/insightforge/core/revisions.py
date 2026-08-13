from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.models import Organization


async def increment_data_revision(
    db: AsyncSession,
    organization: Organization,
) -> int:
    """Atomically advance the tenant revision and keep the request context coherent."""
    revision = await db.scalar(
        update(Organization)
        .where(Organization.id == organization.id)
        .values(data_revision=Organization.data_revision + 1)
        .returning(Organization.data_revision)
        .execution_options(synchronize_session=False)
    )
    if revision is None:
        raise RuntimeError("The tenant disappeared while its data revision was advancing.")
    organization.data_revision = int(revision)
    return organization.data_revision
