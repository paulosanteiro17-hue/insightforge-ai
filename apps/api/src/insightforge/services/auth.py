from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.core.config import Settings
from insightforge.core.problems import AppError
from insightforge.core.security import (
    SessionSecrets,
    create_session_secrets,
    hash_password,
    hash_token,
    password_needs_rehash,
    random_token,
    verify_password,
)
from insightforge.core.time import utc_now
from insightforge.models import (
    AccountActionToken,
    IdempotencyRecord,
    Organization,
    OrganizationMember,
    Subscription,
    User,
    UserPreference,
    UserSession,
)
from insightforge.models.enums import (
    DemoStatus,
    OnboardingState,
    OrganizationRole,
    UserStatus,
)
from insightforge.repositories.auth import AuthRepository
from insightforge.services.seed import DemoSeedService


def _demo_idempotency_key_error() -> AppError:
    return AppError(
        status=400,
        code="idempotency_key_required",
        title="Idempotency key required",
        detail="Provide a UUID version 4 Idempotency-Key header.",
    )


def validate_demo_idempotency_key(value: str | None) -> str:
    if value is None:
        raise _demo_idempotency_key_error()
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise _demo_idempotency_key_error() from exc
    if parsed.version != 4 or str(parsed) != value.casefold():
        raise _demo_idempotency_key_error()
    return str(parsed)


@dataclass(slots=True)
class AuthResult:
    user: User
    session: UserSession
    secrets: SessionSecrets
    idempotency_replayed: bool = False


@lru_cache
def dummy_password_hash() -> str:
    return hash_password("TimingOnlyPassword-Not-A-Credential")


class AuthService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.repository = AuthRepository(db)

    async def register(self, *, email: str, password: str, display_name: str) -> AuthResult:
        normalized_email = email.strip().casefold()
        if await self.repository.user_by_email(normalized_email) is not None:
            raise AppError(
                status=409,
                code="duplicate_resource",
                title="Account could not be created",
                detail="An account with these details cannot be created.",
            )

        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email=normalized_email,
            password_hash=hash_password(password),
            display_name=display_name,
            status=UserStatus.ACTIVE.value,
        )
        preference = UserPreference(user_id=user_id)
        self.repository.add_user(user, preference)
        session, secrets = self._new_session(user_id=user_id, is_demo=False)
        self.repository.add_session(session)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise AppError(
                status=409,
                code="duplicate_resource",
                title="Account could not be created",
                detail="An account with these details cannot be created.",
            ) from exc
        return AuthResult(user=user, session=session, secrets=secrets)

    async def login(self, *, email: str, password: str) -> AuthResult:
        normalized_email = email.strip().casefold()
        user = await self.repository.user_by_email(normalized_email)
        encoded_hash = user.password_hash if user is not None else dummy_password_hash()
        password_is_valid = verify_password(password, encoded_hash)
        if user is None or not password_is_valid or user.status != UserStatus.ACTIVE.value:
            raise AppError(
                status=401,
                code="invalid_credentials",
                title="Authentication failed",
                detail="Invalid email or password.",
            )

        if password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
        user.last_login_at = utc_now()
        session, secrets = self._new_session(user_id=user.id, is_demo=False)
        self.repository.add_session(session)
        await self.db.commit()
        return AuthResult(user=user, session=session, secrets=secrets)

    async def logout(self, user_session: UserSession) -> None:
        if user_session.revoked_at is None:
            user_session.revoked_at = utc_now()
            await self.db.commit()

    async def request_password_reset(self, *, email: str) -> str | None:
        normalized_email = email.strip().casefold()
        user = await self.repository.user_by_email(normalized_email)
        if user is None or user.status != UserStatus.ACTIVE.value:
            return None

        now = utc_now()
        await self.db.execute(
            update(AccountActionToken)
            .where(
                AccountActionToken.user_id == user.id,
                AccountActionToken.purpose == "password_reset",
                AccountActionToken.consumed_at.is_(None),
            )
            .values(consumed_at=now)
        )
        token = random_token()
        self.db.add(
            AccountActionToken(
                id=uuid.uuid4(),
                user_id=user.id,
                purpose="password_reset",
                token_hash=hash_token(token),
                expires_at=now + timedelta(minutes=self.settings.password_reset_expiry_minutes),
                attempts=0,
                created_at=now,
            )
        )
        await self.db.commit()
        return token

    async def confirm_password_reset(self, *, token: str, password: str) -> None:
        now = utc_now()
        action = await self.db.scalar(
            select(AccountActionToken)
            .where(AccountActionToken.token_hash == hash_token(token))
            .with_for_update()
        )
        if (
            action is None
            or not action.is_password_reset
            or action.consumed_at is not None
            or action.expires_at <= now
            or action.attempts >= 10
        ):
            raise AppError(
                status=400,
                code="invalid_recovery_token",
                title="Reset link is invalid",
                detail="Request a new password reset link and try again.",
            )
        user = await self.db.get(User, action.user_id)
        if user is None or user.status != UserStatus.ACTIVE.value:
            raise AppError(
                status=400,
                code="invalid_recovery_token",
                title="Reset link is invalid",
                detail="Request a new password reset link and try again.",
            )

        action.attempts += 1
        action.consumed_at = now
        user.password_hash = hash_password(password)
        await self.db.execute(
            update(UserSession)
            .where(
                UserSession.user_id == user.id,
                UserSession.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        await self.db.execute(
            update(AccountActionToken)
            .where(
                AccountActionToken.user_id == user.id,
                AccountActionToken.purpose == "password_reset",
                AccountActionToken.id != action.id,
                AccountActionToken.consumed_at.is_(None),
            )
            .values(consumed_at=now)
        )
        await self.db.commit()

    async def create_demo_session(
        self,
        *,
        idempotency_key: str,
        browser_scope: str,
    ) -> AuthResult:
        if not self.settings.demo_mode:
            raise AppError(
                status=404,
                code="resource_not_found",
                title="Resource not found",
                detail="The requested resource was not found.",
            )
        key = validate_demo_idempotency_key(idempotency_key)
        if len(browser_scope) != 64 or any(
            character not in "0123456789abcdef" for character in browser_scope
        ):
            raise AppError(
                status=400,
                code="invalid_browser_scope",
                title="Browser scope is invalid",
                detail="Refresh the page and try again.",
            )
        scope_key = f"public:demo:{browser_scope}"
        operation = "create_demo_session"
        existing = await self.db.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.scope_key == scope_key,
                IdempotencyRecord.operation == operation,
                IdempotencyRecord.idempotency_key == key,
            )
        )
        if existing is not None:
            if existing.state != "completed" or not existing.response_body:
                raise AppError(
                    status=409,
                    code="idempotency_in_progress",
                    title="Request is already in progress",
                    detail="A request with this idempotency key is still in progress.",
                    headers={"Retry-After": "1"},
                )
            return await self._replay_demo(existing)

        now = utc_now()
        user_id = uuid.uuid4()
        organization_id = uuid.uuid4()
        user = User(
            id=user_id,
            email=f"demo-{user_id.hex}@example.com",
            password_hash=hash_password(random_token()),
            display_name="Demo Owner",
            status=UserStatus.ACTIVE.value,
            email_verified_at=now,
        )
        organization = Organization(
            id=organization_id,
            name="Northstar Demo",
            slug=f"northstar-demo-{organization_id.hex[:12]}",
            reporting_currency="USD",
            timezone="America/New_York",
            industry="Software",
            onboarding_state=OnboardingState.COMPLETE.value,
            data_revision=1,
            created_by_user_id=user_id,
            is_demo=True,
            demo_expires_at=now + timedelta(hours=self.settings.demo_session_hours),
            demo_status=DemoStatus.READY.value,
        )
        membership = OrganizationMember(
            id=uuid.uuid4(),
            organization_id=organization_id,
            user_id=user_id,
            role=OrganizationRole.OWNER.value,
        )
        subscription = Subscription(
            id=uuid.uuid4(),
            organization_id=organization_id,
            plan="pro",
            status="active",
            provider="demo",
        )
        session, secrets = self._new_session(user_id=user_id, is_demo=True)
        record = IdempotencyRecord(
            id=uuid.uuid4(),
            scope_key=scope_key,
            actor_user_id=user_id,
            operation=operation,
            idempotency_key=key,
            request_hash=hash_token("{}"),
            state="completed",
            response_status=201,
            response_body={"user_id": str(user_id), "organization_id": str(organization_id)},
            resource_type="organization",
            resource_id=organization_id,
            expires_at=now + timedelta(hours=24),
            created_at=now,
            updated_at=now,
        )
        self.db.add(user)
        await self.db.flush()
        self.db.add_all(
            [
                UserPreference(user_id=user_id),
                organization,
                session,
            ]
        )
        await self.db.flush()
        self.db.add_all([membership, subscription])
        await self.db.flush()
        await DemoSeedService(self.db).seed(
            organization_id=organization_id,
            actor_user_id=user_id,
            anchor=now,
        )
        self.db.add(record)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            competing_record = await self.db.scalar(
                select(IdempotencyRecord.id).where(
                    IdempotencyRecord.scope_key == scope_key,
                    IdempotencyRecord.operation == operation,
                    IdempotencyRecord.idempotency_key == key,
                )
            )
            if competing_record is None:
                raise
            raise AppError(
                status=409,
                code="idempotency_in_progress",
                title="Request is already in progress",
                detail="A request with this idempotency key is being completed.",
                headers={"Retry-After": "1"},
            ) from exc
        return AuthResult(user=user, session=session, secrets=secrets)

    async def _replay_demo(self, record: IdempotencyRecord) -> AuthResult:
        body = record.response_body or {}
        try:
            user_id = uuid.UUID(str(body["user_id"]))
            organization_id = uuid.UUID(str(body["organization_id"]))
        except (KeyError, ValueError) as exc:
            raise AppError(
                status=409,
                code="idempotency_conflict",
                title="Idempotency record is not reusable",
                detail="Use a new idempotency key for this request.",
            ) from exc
        user = await self.db.get(User, user_id)
        organization = await self.db.get(Organization, organization_id)
        now = utc_now()
        if (
            user is None
            or organization is None
            or not organization.is_demo
            or organization.demo_expires_at is None
            or organization.demo_expires_at <= now
        ):
            raise AppError(
                status=410,
                code="resource_expired",
                title="Demo workspace expired",
                detail=(
                    "This demo workspace has expired. Use a new idempotency key to create another."
                ),
            )
        session, secrets = self._new_session(user_id=user_id, is_demo=True)
        self.db.add(session)
        await self.db.commit()
        return AuthResult(
            user=user,
            session=session,
            secrets=secrets,
            idempotency_replayed=True,
        )

    def _new_session(
        self,
        *,
        user_id: uuid.UUID,
        is_demo: bool,
    ) -> tuple[UserSession, SessionSecrets]:
        now = utc_now()
        secrets = create_session_secrets()
        absolute_hours = (
            min(self.settings.session_absolute_hours, self.settings.demo_session_hours)
            if is_demo
            else self.settings.session_absolute_hours
        )
        absolute_expires_at = now + timedelta(hours=absolute_hours)
        idle_expires_at = min(
            now + timedelta(minutes=self.settings.session_idle_minutes),
            absolute_expires_at,
        )
        return (
            UserSession(
                id=uuid.uuid4(),
                user_id=user_id,
                token_hash=secrets.token_hash,
                csrf_token_hash=secrets.csrf_token_hash,
                idle_expires_at=idle_expires_at,
                absolute_expires_at=absolute_expires_at,
                last_seen_at=now,
                is_demo=is_demo,
            ),
            secrets,
        )
