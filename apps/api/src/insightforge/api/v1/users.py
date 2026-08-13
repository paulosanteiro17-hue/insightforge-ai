from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from insightforge.api.dependencies import (
    CurrentIdentityDependency,
    RequestIdDependency,
    get_account_service,
    require_csrf,
)
from insightforge.api.rate_limits import PASSWORD_CHANGE, RequestRateLimitsDependency
from insightforge.schemas.auth import PreferenceView
from insightforge.schemas.common import DataEnvelope
from insightforge.schemas.users import (
    CurrentUserView,
    PasswordChangeRequest,
    PreferenceUpdateRequest,
    ProfileUpdateRequest,
)
from insightforge.services.accounts import AccountService

router = APIRouter(prefix="/users", tags=["Users"])
AccountServiceDependency = Annotated[AccountService, Depends(get_account_service)]


def current_user_view(
    identity: CurrentIdentityDependency, preference: PreferenceView
) -> CurrentUserView:
    return CurrentUserView(
        id=identity.user.id,
        email=identity.user.email,
        display_name=identity.user.display_name,
        status=identity.user.status,
        email_verified_at=identity.user.email_verified_at,
        locale=identity.user.locale,
        time_zone=identity.user.time_zone,
        created_at=identity.user.created_at,
        preferences=preference,
    )


@router.get("/me", response_model=DataEnvelope[CurrentUserView])
async def get_current_user(
    identity: CurrentIdentityDependency,
    service: AccountServiceDependency,
) -> DataEnvelope[CurrentUserView]:
    preference = PreferenceView.model_validate(await service.preference_for(identity.user.id))
    return DataEnvelope(data=current_user_view(identity, preference))


@router.patch(
    "/me",
    response_model=DataEnvelope[CurrentUserView],
    dependencies=[Depends(require_csrf)],
)
async def update_current_user(
    payload: ProfileUpdateRequest,
    identity: CurrentIdentityDependency,
    service: AccountServiceDependency,
    request_id: RequestIdDependency,
) -> DataEnvelope[CurrentUserView]:
    identity.user = await service.update_profile(
        user=identity.user,
        changes=payload.model_dump(exclude_unset=True),
        request_id=request_id,
        actor_is_demo=identity.session.is_demo,
    )
    preference = PreferenceView.model_validate(await service.preference_for(identity.user.id))
    return DataEnvelope(data=current_user_view(identity, preference))


@router.get("/me/preferences", response_model=DataEnvelope[PreferenceView])
async def get_preferences(
    identity: CurrentIdentityDependency,
    service: AccountServiceDependency,
) -> DataEnvelope[PreferenceView]:
    return DataEnvelope(
        data=PreferenceView.model_validate(await service.preference_for(identity.user.id))
    )


@router.patch(
    "/me/preferences",
    response_model=DataEnvelope[PreferenceView],
    dependencies=[Depends(require_csrf)],
)
async def update_preferences(
    payload: PreferenceUpdateRequest,
    identity: CurrentIdentityDependency,
    service: AccountServiceDependency,
    request_id: RequestIdDependency,
) -> DataEnvelope[PreferenceView]:
    preference = await service.update_preferences(
        user=identity.user,
        changes=payload.model_dump(exclude_unset=True),
        request_id=request_id,
        actor_is_demo=identity.session.is_demo,
    )
    return DataEnvelope(data=PreferenceView.model_validate(preference))


@router.patch(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def change_password(
    payload: PasswordChangeRequest,
    identity: CurrentIdentityDependency,
    service: AccountServiceDependency,
    rate_limits: RequestRateLimitsDependency,
    request_id: RequestIdDependency,
) -> Response:
    await rate_limits.enforce(scope=PASSWORD_CHANGE, subject=str(identity.user.id))
    await service.change_password(
        user=identity.user,
        current_session=identity.session,
        current_password=payload.current_password,
        new_password=payload.new_password,
        request_id=request_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
