from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.models import AuditLog


def add_audit_event(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID | None,
    actor_user_id: uuid.UUID,
    actor_is_demo: bool,
    action: str,
    request_id: uuid.UUID,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    metadata: dict[str, object] | None = None,
) -> AuditLog:
    """Stage a redacted audit entry in the caller's transaction."""

    event = AuditLog(
        id=uuid.uuid4(),
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        actor_type="demo" if actor_is_demo else "user",
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        request_id=request_id,
        safe_metadata=metadata or {},
    )
    db.add(event)
    return event
