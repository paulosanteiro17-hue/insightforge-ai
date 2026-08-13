from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, Header, Request, Security
from fastapi.security import APIKeyCookie
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.core.config import Settings, get_settings
from insightforge.core.policies import Permission, PermissionSet, permissions_for
from insightforge.core.problems import AppError
from insightforge.core.security import (
    constant_time_equal,
    hash_token,
    origin_is_allowed,
    verify_pre_auth_csrf_token,
)
from insightforge.core.time import utc_now
from insightforge.db.session import get_db_session
from insightforge.models import Organization, OrganizationMember, User, UserSession
from insightforge.models.enums import DemoStatus, OrganizationStatus, UserStatus
from insightforge.repositories.auth import AuthRepository
from insightforge.services.accounts import AccountService
from insightforge.services.analytics import AnalyticsService
from insightforge.services.auth import AuthService
from insightforge.services.billing import BillingService
from insightforge.services.commerce import CustomerService, OrderService, ProductService
from insightforge.services.data_management import DataManagementService
from insightforge.services.generation_jobs import GenerationJobService
from insightforge.services.imports import ImportService
from insightforge.services.intelligence import IntelligenceService
from insightforge.services.invitations import InvitationService
from insightforge.services.organization_settings import OrganizationSettingsService
from insightforge.services.organizations import OrganizationService
from insightforge.services.reports import ReportService
from insightforge.services.team_members import TeamMemberService
from insightforge.storage.local import LocalPrivateStorage

SettingsDependency = Annotated[Settings, Depends(get_settings)]
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
session_cookie_scheme = APIKeyCookie(name="__Host-insightforge_session", auto_error=False)


@dataclass(slots=True)
class CurrentIdentity:
    user: User
    session: UserSession


@dataclass(slots=True)
class TenantContext:
    identity: CurrentIdentity
    organization: Organization
    membership: OrganizationMember
    permissions: PermissionSet
    organization_id: uuid.UUID = field(init=False)
    user_id: uuid.UUID = field(init=False)
    is_demo: bool = field(init=False)
    data_revision: int = field(init=False)
    time_zone: str = field(init=False)

    def __post_init__(self) -> None:
        # AsyncSession.rollback() expires ORM instances. Keep immutable request-scope
        # authorization identifiers available without triggering implicit async I/O.
        self.organization_id = self.organization.id
        self.user_id = self.identity.user.id
        self.is_demo = self.identity.session.is_demo
        self.data_revision = self.organization.data_revision
        self.time_zone = self.organization.timezone


def get_auth_service(db: DatabaseSession, settings: SettingsDependency) -> AuthService:
    return AuthService(db, settings)


def get_organization_service(db: DatabaseSession) -> OrganizationService:
    return OrganizationService(db)


def get_customer_service(db: DatabaseSession) -> CustomerService:
    return CustomerService(db)


def get_product_service(db: DatabaseSession) -> ProductService:
    return ProductService(db)


def get_order_service(db: DatabaseSession) -> OrderService:
    return OrderService(db)


def get_analytics_service(db: DatabaseSession) -> AnalyticsService:
    return AnalyticsService(db)


def get_import_service(db: DatabaseSession, settings: SettingsDependency) -> ImportService:
    return ImportService(db, settings)


def get_account_service(db: DatabaseSession) -> AccountService:
    return AccountService(db)


def get_invitation_service(db: DatabaseSession, settings: SettingsDependency) -> InvitationService:
    return InvitationService(db, settings)


def get_team_member_service(db: DatabaseSession) -> TeamMemberService:
    return TeamMemberService(db)


def get_billing_service(db: DatabaseSession) -> BillingService:
    return BillingService(db)


def get_organization_settings_service(db: DatabaseSession) -> OrganizationSettingsService:
    return OrganizationSettingsService(db)


def get_data_management_service(
    db: DatabaseSession, settings: SettingsDependency
) -> DataManagementService:
    return DataManagementService(db, settings)


def get_intelligence_service(db: DatabaseSession) -> IntelligenceService:
    return IntelligenceService(db)


def get_generation_job_service(db: DatabaseSession) -> GenerationJobService:
    return GenerationJobService(db)


def get_report_service(
    db: DatabaseSession,
    settings: SettingsDependency,
) -> ReportService:
    return ReportService(
        db,
        LocalPrivateStorage(settings.private_storage_path),
        max_export_bytes=settings.export_max_bytes,
        max_export_rows=settings.export_max_rows,
        retention=timedelta(hours=settings.export_retention_hours),
    )


def current_request_id(request: Request) -> uuid.UUID:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, uuid.UUID) else uuid.uuid4()


RequestIdDependency = Annotated[uuid.UUID, Depends(current_request_id)]


async def optional_current_identity(
    request: Request,
    db: DatabaseSession,
    settings: SettingsDependency,
) -> CurrentIdentity | None:
    if hasattr(request.state, "identity"):
        cached = request.state.identity
        return cached if isinstance(cached, CurrentIdentity) else None
    raw_token = request.cookies.get(settings.session_cookie_name)
    if not raw_token:
        request.state.identity = None
        return None
    row = await AuthRepository(db).session_by_token_hash(hash_token(raw_token))
    if row is None:
        request.state.identity = None
        request.state.invalid_session = True
        return None
    user_session, user = row
    now = utc_now()
    if (
        user_session.revoked_at is not None
        or user_session.idle_expires_at <= now
        or user_session.absolute_expires_at <= now
        or user.status != UserStatus.ACTIVE.value
    ):
        request.state.identity = None
        request.state.invalid_session = True
        return None
    if now - user_session.last_seen_at >= timedelta(
        seconds=settings.session_activity_write_interval_seconds
    ):
        user_session.last_seen_at = now
        user_session.idle_expires_at = min(
            now + timedelta(minutes=settings.session_idle_minutes),
            user_session.absolute_expires_at,
        )
        await db.commit()
    identity = CurrentIdentity(user=user, session=user_session)
    request.state.identity = identity
    return identity


async def current_identity(
    request: Request,
    identity: Annotated[CurrentIdentity | None, Depends(optional_current_identity)],
    _documented_session: Annotated[str | None, Security(session_cookie_scheme)] = None,
) -> CurrentIdentity:
    if identity is None:
        expired = bool(getattr(request.state, "invalid_session", False))
        raise AppError(
            status=401,
            code="session_expired" if expired else "authentication_required",
            title="Authentication required",
            detail=(
                "Your session has expired. Sign in again." if expired else "Sign in to continue."
            ),
        )
    return identity


CurrentIdentityDependency = Annotated[CurrentIdentity, Depends(current_identity)]


def _request_origin(request: Request) -> str | None:
    origin = request.headers.get("Origin")
    if origin:
        return origin.rstrip("/")
    referer = request.headers.get("Referer")
    if not referer:
        return None
    parsed = urlsplit(referer)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


async def require_csrf(
    request: Request,
    db: DatabaseSession,
    settings: SettingsDependency,
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    csrf_cookie = request.cookies.get(settings.csrf_cookie_name)
    origin = _request_origin(request)
    if (
        not csrf_cookie
        or not csrf_header
        or not constant_time_equal(csrf_cookie, csrf_header)
        or origin is None
        or not origin_is_allowed(origin, settings)
    ):
        raise _csrf_error()
    identity = await optional_current_identity(request, db, settings)
    if identity is not None:
        if not constant_time_equal(hash_token(csrf_header), identity.session.csrf_token_hash):
            raise _csrf_error()
    elif not verify_pre_auth_csrf_token(csrf_header, settings):
        raise _csrf_error()


def _csrf_error() -> AppError:
    return AppError(
        status=403,
        code="csrf_failed",
        title="Request verification failed",
        detail="Refresh the page and try again.",
    )


async def tenant_context(
    identity: CurrentIdentityDependency,
    db: DatabaseSession,
    organization_header: Annotated[str | None, Header(alias="X-Organization-ID")] = None,
) -> TenantContext:
    if organization_header is None:
        raise AppError(
            status=400,
            code="organization_context_required",
            title="Organization context required",
            detail="Select an organization and try again.",
        )
    try:
        organization_id = uuid.UUID(organization_header)
    except ValueError as exc:
        raise AppError(
            status=400,
            code="invalid_organization_context",
            title="Organization context is invalid",
            detail="Select a valid organization and try again.",
        ) from exc
    row = (
        await db.execute(
            select(Organization, OrganizationMember)
            .join(
                OrganizationMember,
                OrganizationMember.organization_id == Organization.id,
            )
            .where(
                Organization.id == organization_id,
                OrganizationMember.user_id == identity.user.id,
                OrganizationMember.removed_at.is_(None),
            )
        )
    ).one_or_none()
    if row is None:
        raise AppError(
            status=404,
            code="resource_not_found",
            title="Resource not found",
            detail="The requested resource was not found.",
        )
    organization, membership = row[0], row[1]
    if organization.is_demo != identity.session.is_demo:
        raise AppError(
            status=404,
            code="resource_not_found",
            title="Resource not found",
            detail="The requested resource was not found.",
        )
    now = utc_now()
    if organization.is_demo and (
        organization.demo_status == DemoStatus.EXPIRED.value
        or organization.demo_expires_at is None
        or organization.demo_expires_at <= now
    ):
        raise AppError(
            status=410,
            code="resource_expired",
            title="Demo workspace expired",
            detail="This demo workspace has expired.",
        )
    if organization.status == OrganizationStatus.SUSPENDED.value:
        raise AppError(
            status=403,
            code="organization_suspended",
            title="Organization is suspended",
            detail="This organization is temporarily unavailable.",
        )
    return TenantContext(
        identity=identity,
        organization=organization,
        membership=membership,
        permissions=permissions_for(membership.role, is_demo=identity.session.is_demo),
    )


TenantContextDependency = Annotated[TenantContext, Depends(tenant_context)]


def require_permission(permission: Permission) -> object:
    async def dependency(context: TenantContextDependency) -> TenantContext:
        if not context.permissions.allows(permission):
            raise AppError(
                status=403,
                code="permission_denied",
                title="Permission denied",
                detail="You do not have permission to perform this action.",
            )
        return context

    return Depends(dependency)
