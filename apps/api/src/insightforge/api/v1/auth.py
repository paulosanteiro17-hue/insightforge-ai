from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Header, Request, Response, status

from insightforge.api.dependencies import (
    CurrentIdentity,
    CurrentIdentityDependency,
    DatabaseSession,
    SettingsDependency,
    get_auth_service,
    get_organization_service,
    optional_current_identity,
    require_csrf,
)
from insightforge.api.rate_limits import (
    AUTH_GLOBAL,
    DEMO_BROWSER,
    DEMO_GLOBAL,
    LOGIN_ACCOUNT,
    PASSWORD_RESET,
    REGISTER_BROWSER,
    RequestRateLimitsDependency,
)
from insightforge.core.problems import AppError
from insightforge.core.security import (
    constant_time_equal,
    create_pre_auth_csrf_token,
    hash_token,
    random_token,
    verify_pre_auth_csrf_token,
)
from insightforge.core.time import utc_now
from insightforge.models import Organization, OrganizationMember
from insightforge.schemas.auth import (
    CsrfTokenView,
    DemoSessionRequest,
    LoginRequest,
    PasswordResetConfirmationRequest,
    PasswordResetRequest,
    PasswordResetRequestView,
    RegisterRequest,
    SessionMetadataView,
    SessionView,
    UserView,
)
from insightforge.schemas.common import DataEnvelope
from insightforge.schemas.organizations import OrganizationSummaryView
from insightforge.services.auth import (
    AuthResult,
    AuthService,
    validate_demo_idempotency_key,
)
from insightforge.services.organizations import OrganizationService

router = APIRouter(prefix="/auth", tags=["Authentication"])

AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
OrganizationServiceDependency = Annotated[OrganizationService, Depends(get_organization_service)]


def _set_csrf_cookie(
    response: Response,
    *,
    settings: SettingsDependency,
    token: str,
    expires_at: datetime | None = None,
) -> None:
    max_age = settings.csrf_token_ttl_seconds
    if expires_at is not None:
        max_age = max(0, min(max_age, int((expires_at - utc_now()).total_seconds())))
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=token,
        max_age=max_age,
        secure=settings.session_cookie_secure,
        httponly=False,
        samesite="lax",
        path="/",
    )


def _set_auth_cookies(
    response: Response,
    *,
    settings: SettingsDependency,
    result: AuthResult,
) -> None:
    max_age = max(0, int((result.session.absolute_expires_at - utc_now()).total_seconds()))
    response.set_cookie(
        key=settings.session_cookie_name,
        value=result.secrets.token,
        max_age=max_age,
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
        path="/",
    )
    _set_csrf_cookie(
        response,
        settings=settings,
        token=result.secrets.csrf_token,
        expires_at=result.session.absolute_expires_at,
    )


def _clear_auth_cookies(response: Response, settings: SettingsDependency) -> None:
    response.delete_cookie(
        settings.session_cookie_name,
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
        path="/",
    )
    response.delete_cookie(
        settings.csrf_cookie_name,
        secure=settings.session_cookie_secure,
        httponly=False,
        samesite="lax",
        path="/",
    )


def _organization_view(
    organization: Organization, membership: OrganizationMember
) -> OrganizationSummaryView:
    return OrganizationSummaryView(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        role=membership.role,
        status=organization.status,
        onboarding_state=organization.onboarding_state,
        reporting_currency=organization.reporting_currency,
        timezone=organization.timezone,
        is_demo=organization.is_demo,
        demo_expires_at=organization.demo_expires_at,
    )


async def build_session_view(
    identity: CurrentIdentity,
    organizations: OrganizationService,
) -> SessionView:
    memberships = await organizations.list_for_user(identity.user.id)
    return SessionView(
        user=UserView.model_validate(identity.user),
        session=SessionMetadataView.model_validate(identity.session),
        organizations=[_organization_view(org, member) for org, member in memberships],
    )


@router.get(
    "/csrf-token",
    response_model=DataEnvelope[CsrfTokenView],
    summary="Issue a CSRF token",
)
async def issue_csrf_token(
    request: Request,
    response: Response,
    db: DatabaseSession,
    settings: SettingsDependency,
    identity: Annotated[CurrentIdentity | None, Depends(optional_current_identity)],
) -> DataEnvelope[CsrfTokenView]:
    existing_token = request.cookies.get(settings.csrf_cookie_name)
    if identity is None:
        token = (
            existing_token
            if existing_token is not None and verify_pre_auth_csrf_token(existing_token, settings)
            else create_pre_auth_csrf_token(settings)
        )
        expires_at = None
    else:
        if existing_token is not None and constant_time_equal(
            hash_token(existing_token), identity.session.csrf_token_hash
        ):
            token = existing_token
        else:
            token = random_token()
            identity.session.csrf_token_hash = hash_token(token)
            await db.commit()
        expires_at = identity.session.absolute_expires_at
    _set_csrf_cookie(response, settings=settings, token=token, expires_at=expires_at)
    if identity is None:
        demo_scope = hash_token(token)
        if not constant_time_equal(
            request.cookies.get(settings.demo_scope_cookie_name, ""),
            demo_scope,
        ):
            response.set_cookie(
                key=settings.demo_scope_cookie_name,
                value=demo_scope,
                max_age=86_400,
                secure=settings.session_cookie_secure,
                httponly=True,
                samesite="lax",
                path="/",
            )
    response.headers["Cache-Control"] = "no-store"
    return DataEnvelope(data=CsrfTokenView(csrf_token=token))


@router.post(
    "/register",
    response_model=DataEnvelope[SessionView],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
    summary="Register an account",
)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    settings: SettingsDependency,
    rate_limits: RequestRateLimitsDependency,
    auth: AuthServiceDependency,
    organizations: OrganizationServiceDependency,
) -> DataEnvelope[SessionView]:
    browser_subject = request.cookies.get(settings.csrf_cookie_name, "missing")
    await rate_limits.enforce(scope=AUTH_GLOBAL, subject="all-public-auth")
    await rate_limits.enforce(scope=REGISTER_BROWSER, subject=browser_subject)
    result = await auth.register(
        email=str(payload.email),
        password=payload.password,
        display_name=payload.display_name,
    )
    _set_auth_cookies(response, settings=settings, result=result)
    response.headers["Location"] = "/api/v1/users/me"
    view = await build_session_view(
        CurrentIdentity(user=result.user, session=result.session), organizations
    )
    return DataEnvelope(data=view)


@router.post(
    "/login",
    response_model=DataEnvelope[SessionView],
    dependencies=[Depends(require_csrf)],
    summary="Create a session",
)
async def login(
    payload: LoginRequest,
    response: Response,
    settings: SettingsDependency,
    rate_limits: RequestRateLimitsDependency,
    auth: AuthServiceDependency,
    organizations: OrganizationServiceDependency,
) -> DataEnvelope[SessionView]:
    normalized_email = str(payload.email).strip().casefold()
    await rate_limits.enforce(scope=AUTH_GLOBAL, subject="all-public-auth")
    await rate_limits.enforce(scope=LOGIN_ACCOUNT, subject=normalized_email)
    result = await auth.login(email=str(payload.email), password=payload.password)
    _set_auth_cookies(response, settings=settings, result=result)
    view = await build_session_view(
        CurrentIdentity(user=result.user, session=result.session), organizations
    )
    return DataEnvelope(data=view)


@router.post(
    "/password-reset-requests",
    response_model=DataEnvelope[PasswordResetRequestView],
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_csrf)],
    summary="Request password recovery",
)
async def request_password_reset(
    payload: PasswordResetRequest,
    settings: SettingsDependency,
    rate_limits: RequestRateLimitsDependency,
    auth: AuthServiceDependency,
) -> DataEnvelope[PasswordResetRequestView]:
    normalized_email = str(payload.email).strip().casefold()
    await rate_limits.enforce(scope=AUTH_GLOBAL, subject="all-public-auth")
    await rate_limits.enforce(scope=PASSWORD_RESET, subject=normalized_email)
    token = await auth.request_password_reset(email=normalized_email)
    recovery_path = (
        f"/reset-password?token={token}"
        if token is not None and settings.environment in {"development", "testing"}
        else None
    )
    return DataEnvelope(
        data=PasswordResetRequestView(
            message=(
                "If an account exists for that address, password reset instructions are ready."
            ),
            recovery_path=recovery_path,
        )
    )


@router.post(
    "/password-resets",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
    summary="Set a recovered password",
)
async def confirm_password_reset(
    payload: PasswordResetConfirmationRequest,
    rate_limits: RequestRateLimitsDependency,
    auth: AuthServiceDependency,
) -> Response:
    await rate_limits.enforce(scope=AUTH_GLOBAL, subject="all-public-auth")
    await rate_limits.enforce(scope=PASSWORD_RESET, subject=hash_token(payload.token))
    await auth.confirm_password_reset(token=payload.token, password=payload.password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/demo-session",
    response_model=DataEnvelope[SessionView],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
    summary="Create an isolated demo session",
)
async def create_demo_session(
    _payload: Annotated[
        DemoSessionRequest,
        Body(default_factory=DemoSessionRequest),
    ],
    request: Request,
    response: Response,
    settings: SettingsDependency,
    rate_limits: RequestRateLimitsDependency,
    auth: AuthServiceDependency,
    organizations: OrganizationServiceDependency,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> DataEnvelope[SessionView]:
    key = validate_demo_idempotency_key(idempotency_key)
    scope_cookie = request.cookies.get(settings.demo_scope_cookie_name)
    if scope_cookie is None:
        raise AppError(
            status=400,
            code="browser_scope_required",
            title="Browser verification required",
            detail="Refresh the page and try again.",
        )
    await rate_limits.enforce(scope=DEMO_GLOBAL, subject="all-demo-sessions")
    await rate_limits.enforce(scope=DEMO_BROWSER, subject=scope_cookie)
    result = await auth.create_demo_session(
        idempotency_key=key,
        browser_scope=hash_token(scope_cookie),
    )
    _set_auth_cookies(response, settings=settings, result=result)
    response.headers["Location"] = "/api/v1/organizations/current"
    if result.idempotency_replayed:
        response.headers["Idempotency-Replayed"] = "true"
    view = await build_session_view(
        CurrentIdentity(user=result.user, session=result.session), organizations
    )
    return DataEnvelope(data=view)


@router.get(
    "/session",
    response_model=DataEnvelope[SessionView],
    summary="Get the current session",
)
@router.get(
    "/me",
    response_model=DataEnvelope[SessionView],
    include_in_schema=False,
)
async def get_current_session(
    identity: CurrentIdentityDependency,
    organizations: OrganizationServiceDependency,
) -> DataEnvelope[SessionView]:
    return DataEnvelope(data=await build_session_view(identity, organizations))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
    summary="Revoke the current session",
)
async def logout(
    identity: CurrentIdentityDependency,
    auth: AuthServiceDependency,
    settings: SettingsDependency,
) -> Response:
    await auth.logout(identity.session)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_auth_cookies(response, settings)
    return response
