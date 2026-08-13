from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

import insightforge.services.auth as auth_module
from insightforge.core.config import Settings
from insightforge.models import IdempotencyRecord
from insightforge.services.auth import AuthService


class FakeSession:
    def __init__(self, *, fail_commit: bool = False) -> None:
        self.events: list[str] = []
        self.added: list[object] = []
        self.fail_commit = fail_commit
        self.scalar_calls = 0

    async def scalar(self, _statement):
        self.scalar_calls += 1
        return None

    def add_all(self, values: list[object]) -> None:
        self.events.append("identity-added")
        self.added.extend(values)

    def add(self, value: object) -> None:
        self.events.append("record-added")
        self.added.append(value)

    async def flush(self) -> None:
        self.events.append("identity-flushed")

    async def commit(self) -> None:
        self.events.append("commit")
        if self.fail_commit:
            raise IntegrityError("INSERT", {}, RuntimeError("unexpected constraint"))

    async def rollback(self) -> None:
        self.events.append("rollback")


class FakeSeedService:
    def __init__(self, db: FakeSession) -> None:
        self.db = db

    async def seed(self, **_kwargs: object) -> None:
        assert "identity-flushed" in self.db.events
        self.db.events.append("seeded")


@pytest.mark.asyncio
async def test_demo_session_flushes_identity_before_tenant_seed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeSession()
    monkeypatch.setattr(auth_module, "DemoSeedService", FakeSeedService)
    monkeypatch.setattr(auth_module, "hash_password", lambda _value: "test-hash")
    service = AuthService(db, Settings(_env_file=None))  # type: ignore[arg-type]
    key = str(uuid.uuid4())

    await service.create_demo_session(idempotency_key=key, browser_scope="a" * 64)

    assert db.events.index("identity-flushed") < db.events.index("seeded")
    record = next(value for value in db.added if isinstance(value, IdempotencyRecord))
    assert record.scope_key == f"public:demo:{'a' * 64}"
    assert record.idempotency_key == key


@pytest.mark.asyncio
async def test_unexpected_demo_integrity_error_is_not_mislabeled_as_idempotency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeSession(fail_commit=True)
    monkeypatch.setattr(auth_module, "DemoSeedService", FakeSeedService)
    monkeypatch.setattr(auth_module, "hash_password", lambda _value: "test-hash")
    service = AuthService(db, Settings(_env_file=None))  # type: ignore[arg-type]

    with pytest.raises(IntegrityError):
        await service.create_demo_session(
            idempotency_key=str(uuid.uuid4()),
            browser_scope="b" * 64,
        )
