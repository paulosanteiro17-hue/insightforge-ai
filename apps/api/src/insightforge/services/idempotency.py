from __future__ import annotations

import hashlib
import json
import uuid
from datetime import timedelta
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.core.problems import AppError
from insightforge.core.time import utc_now
from insightforge.models import IdempotencyRecord


def canonical_request_hash(payload: object) -> str:
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def validate_idempotency_key(value: str | None) -> str:
    if value is None or not 16 <= len(value) <= 255 or any(char.isspace() for char in value):
        raise AppError(
            status=400,
            code="idempotency_key_required",
            title="Idempotency key required",
            detail="Provide a valid Idempotency-Key header.",
        )
    return value


def validate_uuid_idempotency_key(value: str | None) -> str:
    key = validate_idempotency_key(value)
    try:
        parsed = uuid.UUID(key)
    except ValueError as exc:
        raise AppError(
            status=400,
            code="idempotency_key_required",
            title="Idempotency key required",
            detail="Provide a UUID v4 value in the Idempotency-Key header.",
        ) from exc
    if parsed.version != 4 or str(parsed) != key.casefold():
        raise AppError(
            status=400,
            code="idempotency_key_required",
            title="Idempotency key required",
            detail="Provide a UUID v4 value in the Idempotency-Key header.",
        )
    return key


class IdempotencyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def find(
        self,
        *,
        scope_key: str,
        operation: str,
        key: str,
    ) -> IdempotencyRecord | None:
        return cast(
            IdempotencyRecord | None,
            await self.db.scalar(
                select(IdempotencyRecord).where(
                    IdempotencyRecord.scope_key == scope_key,
                    IdempotencyRecord.operation == operation,
                    IdempotencyRecord.idempotency_key == key,
                )
            ),
        )

    async def replay_record(
        self,
        *,
        scope_key: str,
        operation: str,
        key: str,
        request_hash: str,
    ) -> IdempotencyRecord | None:
        record = await self.find(scope_key=scope_key, operation=operation, key=key)
        if record is None:
            return None
        if record.request_hash != request_hash:
            raise AppError(
                status=409,
                code="idempotency_conflict",
                title="Idempotency key conflict",
                detail="This idempotency key was already used for a different request.",
            )
        if record.state == "processing":
            raise AppError(
                status=409,
                code="idempotency_in_progress",
                title="Request is already in progress",
                detail="A request with this idempotency key is still in progress.",
                headers={"Retry-After": "1"},
            )
        if record.state == "failed":
            raise AppError(
                status=409,
                code="idempotency_conflict",
                title="Previous request failed",
                detail="Use a new idempotency key to retry this command.",
            )
        return record

    async def replay_resource_id(
        self,
        *,
        scope_key: str,
        operation: str,
        key: str,
        request_hash: str,
    ) -> uuid.UUID | None:
        record = await self.replay_record(
            scope_key=scope_key,
            operation=operation,
            key=key,
            request_hash=request_hash,
        )
        return record.resource_id if record is not None else None

    async def replay_response_body(
        self,
        *,
        scope_key: str,
        operation: str,
        key: str,
        request_hash: str,
    ) -> dict[str, object] | None:
        record = await self.replay_record(
            scope_key=scope_key,
            operation=operation,
            key=key,
            request_hash=request_hash,
        )
        if record is None:
            return None
        if record.response_body is None:
            raise AppError(
                status=409,
                code="idempotency_conflict",
                title="Idempotency record is not reusable",
                detail="Use a new idempotency key for this request.",
            )
        return record.response_body

    def start(
        self,
        *,
        scope_key: str,
        actor_user_id: uuid.UUID,
        operation: str,
        key: str,
        request_hash: str,
    ) -> IdempotencyRecord:
        now = utc_now()
        record = IdempotencyRecord(
            id=uuid.uuid4(),
            scope_key=scope_key,
            actor_user_id=actor_user_id,
            operation=operation,
            idempotency_key=key,
            request_hash=request_hash,
            state="processing",
            expires_at=now + timedelta(hours=24),
            created_at=now,
            updated_at=now,
        )
        self.db.add(record)
        return record

    @staticmethod
    def complete(
        record: IdempotencyRecord,
        *,
        status_code: int,
        resource_type: str,
        resource_id: uuid.UUID,
        response_body: dict[str, object] | None = None,
    ) -> None:
        record.state = "completed"
        record.response_status = status_code
        record.response_body = response_body or {"id": str(resource_id)}
        record.resource_type = resource_type
        record.resource_id = resource_id
