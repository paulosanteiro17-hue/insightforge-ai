from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Query, Response, status

from insightforge.api.dependencies import (
    CurrentIdentityDependency,
    RequestIdDependency,
    TenantContext,
    get_invitation_service,
    get_team_member_service,
    require_csrf,
    require_permission,
)
from insightforge.api.rate_limits import (
    INVITATION_ACCOUNT,
    INVITATION_RESEND,
    RequestRateLimitsDependency,
)
from insightforge.core.policies import Permission
from insightforge.schemas.common import (
    CollectionEnvelope,
    CollectionMeta,
    DataEnvelope,
    PaginationView,
)
from insightforge.schemas.team import (
    InvitationAcceptedView,
    InvitationCreateRequest,
    InvitationDeliveryView,
    InvitationPreviewView,
    InvitationView,
    TeamMemberView,
    TeamRoleUpdateRequest,
)
from insightforge.services.invitations import InvitationService
from insightforge.services.team_members import TeamMemberService

router = APIRouter(prefix="/team", tags=["Team"])
InvitationServiceDependency = Annotated[InvitationService, Depends(get_invitation_service)]
TeamMemberServiceDependency = Annotated[TeamMemberService, Depends(get_team_member_service)]
TeamReadContext = Annotated[TenantContext, require_permission(Permission.VIEW_TEAM)]
InvitationContext = Annotated[TenantContext, require_permission(Permission.INVITE_MEMBERS)]
RoleContext = Annotated[TenantContext, require_permission(Permission.CHANGE_ROLES)]
InvitationToken = Annotated[str, Path(min_length=32, max_length=512)]


@router.get("/members", response_model=CollectionEnvelope[TeamMemberView])
async def list_members(
    context: TeamReadContext,
    service: TeamMemberServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> CollectionEnvelope[TeamMemberView]:
    result = await service.list_members(
        context.organization.id,
        page=page,
        page_size=page_size,
    )
    return CollectionEnvelope(
        data=result.items,
        meta=CollectionMeta(
            pagination=PaginationView.from_values(
                page=result.page,
                page_size=result.page_size,
                total=result.total,
            ),
            filters={},
        ),
    )


@router.patch(
    "/members/{member_id}",
    response_model=DataEnvelope[TeamMemberView],
    dependencies=[Depends(require_csrf)],
)
async def change_member_role(
    member_id: uuid.UUID,
    payload: TeamRoleUpdateRequest,
    context: RoleContext,
    service: TeamMemberServiceDependency,
    request_id: RequestIdDependency,
) -> DataEnvelope[TeamMemberView]:
    member = await service.change_role(
        organization_id=context.organization.id,
        actor_user_id=context.identity.user.id,
        actor_is_demo=context.identity.session.is_demo,
        member_id=member_id,
        role=payload.role,
        request_id=request_id,
    )
    return DataEnvelope(data=member)


@router.delete(
    "/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def remove_member(
    member_id: uuid.UUID,
    context: InvitationContext,
    service: TeamMemberServiceDependency,
    request_id: RequestIdDependency,
) -> Response:
    await service.remove_member(
        organization_id=context.organization.id,
        actor_user_id=context.identity.user.id,
        actor_is_demo=context.identity.session.is_demo,
        member_id=member_id,
        request_id=request_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/invitations", response_model=CollectionEnvelope[InvitationView])
async def list_invitations(
    context: InvitationContext,
    service: InvitationServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> CollectionEnvelope[InvitationView]:
    result = await service.list_invitations(
        context.organization.id,
        page=page,
        page_size=page_size,
    )
    return CollectionEnvelope(
        data=result.items,
        meta=CollectionMeta(
            pagination=PaginationView.from_values(
                page=result.page,
                page_size=result.page_size,
                total=result.total,
            ),
            filters={},
        ),
    )


@router.post(
    "/invitations",
    response_model=DataEnvelope[InvitationDeliveryView],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def invite_member(
    payload: InvitationCreateRequest,
    response: Response,
    context: InvitationContext,
    service: InvitationServiceDependency,
    rate_limits: RequestRateLimitsDependency,
    request_id: RequestIdDependency,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> DataEnvelope[InvitationDeliveryView]:
    await rate_limits.enforce(
        scope=INVITATION_ACCOUNT,
        subject=f"{context.organization.id}:{str(payload.email).casefold()}",
    )
    invitation, replayed = await service.invite(
        organization_id=context.organization.id,
        actor_user_id=context.identity.user.id,
        actor_is_demo=context.identity.session.is_demo,
        email=str(payload.email),
        role=payload.role,
        request_id=request_id,
        idempotency_key=idempotency_key,
    )
    response.headers["Location"] = f"/api/v1/team/invitations/{invitation.id}"
    response.headers["Idempotency-Replayed"] = "true" if replayed else "false"
    return DataEnvelope(data=invitation)


@router.post(
    "/invitations/{invitation_id}/resend",
    response_model=DataEnvelope[InvitationDeliveryView],
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_csrf)],
)
async def resend_invitation(
    invitation_id: uuid.UUID,
    context: InvitationContext,
    service: InvitationServiceDependency,
    rate_limits: RequestRateLimitsDependency,
    request_id: RequestIdDependency,
) -> DataEnvelope[InvitationDeliveryView]:
    await rate_limits.enforce(
        scope=INVITATION_RESEND,
        subject=f"{context.organization.id}:{invitation_id}",
    )
    invitation = await service.resend(
        organization_id=context.organization.id,
        actor_user_id=context.identity.user.id,
        actor_is_demo=context.identity.session.is_demo,
        invitation_id=invitation_id,
        request_id=request_id,
    )
    return DataEnvelope(data=invitation)


@router.delete(
    "/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def revoke_invitation(
    invitation_id: uuid.UUID,
    context: InvitationContext,
    service: InvitationServiceDependency,
    request_id: RequestIdDependency,
) -> Response:
    await service.revoke(
        organization_id=context.organization.id,
        actor_user_id=context.identity.user.id,
        actor_is_demo=context.identity.session.is_demo,
        invitation_id=invitation_id,
        request_id=request_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/invitations/accept/{token}",
    response_model=DataEnvelope[InvitationPreviewView],
)
async def preview_invitation(
    token: InvitationToken,
    service: InvitationServiceDependency,
) -> DataEnvelope[InvitationPreviewView]:
    return DataEnvelope(data=await service.preview(token))


@router.post(
    "/invitations/accept/{token}",
    response_model=DataEnvelope[InvitationAcceptedView],
    dependencies=[Depends(require_csrf)],
)
async def accept_invitation(
    token: InvitationToken,
    identity: CurrentIdentityDependency,
    service: InvitationServiceDependency,
    request_id: RequestIdDependency,
) -> DataEnvelope[InvitationAcceptedView]:
    result = await service.accept(
        token=token,
        user_id=identity.user.id,
        user_email=identity.user.email,
        actor_is_demo=identity.session.is_demo,
        request_id=request_id,
    )
    return DataEnvelope(data=result)


@router.post(
    "/leave",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def leave_team(
    context: TeamReadContext,
    service: TeamMemberServiceDependency,
    request_id: RequestIdDependency,
) -> Response:
    await service.leave(
        organization_id=context.organization.id,
        actor_user_id=context.identity.user.id,
        actor_is_demo=context.identity.session.is_demo,
        request_id=request_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
