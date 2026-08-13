from __future__ import annotations

import base64
import hashlib
import hmac
import uuid
from datetime import timedelta
from typing import Literal, cast

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from insightforge.core.config import Settings
from insightforge.core.pagination import PageResult
from insightforge.core.problems import AppError
from insightforge.core.security import hash_token, random_token
from insightforge.core.time import utc_now
from insightforge.models import (
    Organization,
    OrganizationInvitation,
    OrganizationMember,
    User,
)
from insightforge.models.enums import OrganizationRole, OrganizationStatus
from insightforge.schemas.team import (
    InvitationAcceptedView,
    InvitationDeliveryView,
    InvitationPreviewView,
    InvitationView,
)
from insightforge.services.auditing import add_audit_event
from insightforge.services.idempotency import (
    IdempotencyService,
    canonical_request_hash,
    validate_idempotency_key,
)
from insightforge.services.team_access import TeamAccessService


class InvitationService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.idempotency = IdempotencyService(db)
        self.access = TeamAccessService(db)

    async def list_invitations(
        self,
        organization_id: uuid.UUID,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[InvitationView]:
        total = int(
            await self.db.scalar(
                select(func.count())
                .select_from(OrganizationInvitation)
                .where(OrganizationInvitation.organization_id == organization_id)
            )
            or 0
        )
        invitations = list(
            (
                await self.db.scalars(
                    select(OrganizationInvitation)
                    .where(OrganizationInvitation.organization_id == organization_id)
                    .order_by(
                        OrganizationInvitation.created_at.desc(),
                        OrganizationInvitation.id.desc(),
                    )
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return PageResult(
            items=[self._invitation_view(invitation) for invitation in invitations],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def invite(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_is_demo: bool,
        email: str,
        role: str,
        request_id: uuid.UUID,
        idempotency_key: str | None,
    ) -> tuple[InvitationDeliveryView, bool]:
        normalized_email = email.strip().casefold()
        organization, actor = await self.access.lock_organization_and_actor(
            organization_id,
            actor_user_id,
            allowed_roles={OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value},
        )
        self.access.reject_demo(organization, actor_is_demo)
        if actor.role == OrganizationRole.ADMIN.value and role != OrganizationRole.MEMBER.value:
            raise self.access.permission_denied()

        key: str | None = None
        request_hash = canonical_request_hash({"email": normalized_email, "role": role})
        if idempotency_key is not None:
            key = validate_idempotency_key(idempotency_key)
            replayed_id = await self.idempotency.replay_resource_id(
                scope_key=f"organization:{organization_id}",
                operation="invite_team_member",
                key=key,
                request_hash=request_hash,
            )
            if replayed_id is not None:
                invitation = await self._invitation(organization_id, replayed_id)
                if invitation is None:
                    raise self.access.not_found()
                token = self._idempotent_token(
                    organization_id=organization_id,
                    email=normalized_email,
                    key=key,
                )
                return self._delivery_view(invitation, token), True

        existing_member = await self.db.scalar(
            select(OrganizationMember.id)
            .join(User, User.id == OrganizationMember.user_id)
            .where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.removed_at.is_(None),
                User.email == normalized_email,
            )
        )
        if existing_member is not None:
            raise AppError(
                status=409,
                code="member_already_exists",
                title="User is already a member",
                detail="This account already belongs to the organization.",
            )
        active_invitation = await self.db.scalar(
            select(OrganizationInvitation.id).where(
                OrganizationInvitation.organization_id == organization_id,
                OrganizationInvitation.email == normalized_email,
                OrganizationInvitation.accepted_at.is_(None),
                OrganizationInvitation.revoked_at.is_(None),
            )
        )
        if active_invitation is not None:
            raise AppError(
                status=409,
                code="invitation_already_exists",
                title="Invitation already exists",
                detail="Resend or revoke the existing invitation.",
            )

        token = (
            self._idempotent_token(
                organization_id=organization_id,
                email=normalized_email,
                key=key,
            )
            if key is not None
            else random_token()
        )
        now = utc_now()
        invitation = OrganizationInvitation(
            id=uuid.uuid4(),
            organization_id=organization_id,
            email=normalized_email,
            role=role,
            token_hash=hash_token(token),
            invited_by_user_id=actor_user_id,
            expires_at=now + timedelta(hours=self.settings.invitation_expiry_hours),
            created_at=now,
        )
        self.db.add(invitation)
        if key is not None:
            record = self.idempotency.start(
                scope_key=f"organization:{organization_id}",
                actor_user_id=actor_user_id,
                operation="invite_team_member",
                key=key,
                request_hash=request_hash,
            )
            self.idempotency.complete(
                record,
                status_code=201,
                resource_type="organization_invitation",
                resource_id=invitation.id,
            )
        add_audit_event(
            self.db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            actor_is_demo=actor_is_demo,
            action="team.invitation.created",
            request_id=request_id,
            resource_type="organization_invitation",
            resource_id=invitation.id,
            metadata={"role": role},
        )
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise AppError(
                status=409,
                code="invitation_already_exists",
                title="Invitation already exists",
                detail="Resend or revoke the existing invitation.",
            ) from exc
        return self._delivery_view(invitation, token), False

    async def resend(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_is_demo: bool,
        invitation_id: uuid.UUID,
        request_id: uuid.UUID,
    ) -> InvitationDeliveryView:
        organization, actor = await self.access.lock_organization_and_actor(
            organization_id,
            actor_user_id,
            allowed_roles={OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value},
        )
        self.access.reject_demo(organization, actor_is_demo)
        invitation = await self._invitation(organization_id, invitation_id, for_update=True)
        if invitation is None:
            raise self.access.not_found()
        if actor.role == OrganizationRole.ADMIN.value and invitation.role != "member":
            raise self.access.permission_denied()
        if invitation.accepted_at is not None or invitation.revoked_at is not None:
            raise AppError(
                status=409,
                code="invitation_not_pending",
                title="Invitation is not pending",
                detail="Only pending invitations can be resent.",
            )
        token = random_token()
        invitation.token_hash = hash_token(token)
        invitation.expires_at = utc_now() + timedelta(hours=self.settings.invitation_expiry_hours)
        add_audit_event(
            self.db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            actor_is_demo=actor_is_demo,
            action="team.invitation.resent",
            request_id=request_id,
            resource_type="organization_invitation",
            resource_id=invitation.id,
        )
        await self.db.commit()
        return self._delivery_view(invitation, token)

    async def revoke(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_is_demo: bool,
        invitation_id: uuid.UUID,
        request_id: uuid.UUID,
    ) -> None:
        organization, actor = await self.access.lock_organization_and_actor(
            organization_id,
            actor_user_id,
            allowed_roles={OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value},
        )
        self.access.reject_demo(organization, actor_is_demo)
        invitation = await self._invitation(organization_id, invitation_id, for_update=True)
        if invitation is None:
            raise self.access.not_found()
        if actor.role == OrganizationRole.ADMIN.value and invitation.role != "member":
            raise self.access.permission_denied()
        if invitation.accepted_at is not None:
            raise AppError(
                status=409,
                code="invitation_already_accepted",
                title="Invitation was already accepted",
                detail="Remove the member from the team instead.",
            )
        if invitation.revoked_at is None:
            invitation.revoked_at = utc_now()
            add_audit_event(
                self.db,
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                actor_is_demo=actor_is_demo,
                action="team.invitation.revoked",
                request_id=request_id,
                resource_type="organization_invitation",
                resource_id=invitation.id,
            )
            await self.db.commit()

    async def preview(self, token: str) -> InvitationPreviewView:
        invitation = await self.db.scalar(
            select(OrganizationInvitation).where(
                OrganizationInvitation.token_hash == hash_token(token)
            )
        )
        if invitation is None:
            raise self._invalid_invitation()
        self._ensure_pending(invitation)
        organization = await self.db.get(Organization, invitation.organization_id)
        if organization is None or organization.is_demo:
            raise self._invalid_invitation()
        return InvitationPreviewView(
            organization_name=organization.name,
            email_hint=self._email_hint(invitation.email),
            role=invitation.role,
            expires_at=invitation.expires_at,
        )

    async def accept(
        self,
        *,
        token: str,
        user_id: uuid.UUID,
        user_email: str,
        actor_is_demo: bool,
        request_id: uuid.UUID,
    ) -> InvitationAcceptedView:
        if actor_is_demo:
            raise AppError(
                status=403,
                code="demo_policy_denied",
                title="Action unavailable in demo mode",
                detail="Demo sessions cannot accept team invitations.",
            )
        invitation = await self.db.scalar(
            select(OrganizationInvitation)
            .where(OrganizationInvitation.token_hash == hash_token(token))
            .with_for_update()
        )
        if invitation is None:
            raise self._invalid_invitation()
        self._ensure_pending(invitation)
        if invitation.email.casefold() != user_email.strip().casefold():
            raise AppError(
                status=403,
                code="invitation_email_mismatch",
                title="Invitation belongs to another account",
                detail="Sign in with the email address that received this invitation.",
            )
        organization = await self.db.scalar(
            select(Organization)
            .where(Organization.id == invitation.organization_id)
            .with_for_update()
        )
        if (
            organization is None
            or organization.is_demo
            or organization.status != OrganizationStatus.ACTIVE.value
        ):
            raise self._invalid_invitation()
        membership = await self.db.scalar(
            select(OrganizationMember)
            .where(
                OrganizationMember.organization_id == organization.id,
                OrganizationMember.user_id == user_id,
            )
            .with_for_update()
        )
        now = utc_now()
        if membership is None:
            membership = OrganizationMember(
                id=uuid.uuid4(),
                organization_id=organization.id,
                user_id=user_id,
                role=invitation.role,
                joined_at=now,
            )
            self.db.add(membership)
        elif membership.removed_at is None:
            raise AppError(
                status=409,
                code="member_already_exists",
                title="User is already a member",
                detail="This account already belongs to the organization.",
            )
        else:
            membership.role = invitation.role
            membership.joined_at = now
            membership.removed_at = None
        invitation.accepted_at = now
        user = await self.db.get(User, user_id)
        if user is None:
            raise self.access.not_found()
        add_audit_event(
            self.db,
            organization_id=organization.id,
            actor_user_id=user_id,
            actor_is_demo=False,
            action="team.invitation.accepted",
            request_id=request_id,
            resource_type="organization_member",
            resource_id=membership.id,
            metadata={"role": membership.role},
        )
        await self.db.commit()
        return InvitationAcceptedView(
            organization_id=organization.id,
            organization_name=organization.name,
            member=self.access.member_view(membership, user),
        )

    async def _invitation(
        self,
        organization_id: uuid.UUID,
        invitation_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> OrganizationInvitation | None:
        statement = select(OrganizationInvitation).where(
            OrganizationInvitation.organization_id == organization_id,
            OrganizationInvitation.id == invitation_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(OrganizationInvitation | None, await self.db.scalar(statement))

    @staticmethod
    def _ensure_pending(invitation: OrganizationInvitation) -> None:
        if invitation.accepted_at is not None:
            raise AppError(
                status=409,
                code="invitation_already_accepted",
                title="Invitation was already accepted",
                detail="This invitation token can be used only once.",
            )
        if invitation.revoked_at is not None:
            raise AppError(
                status=410,
                code="invitation_revoked",
                title="Invitation was revoked",
                detail="Ask an organization administrator for a new invitation.",
            )
        if invitation.expires_at <= utc_now():
            raise AppError(
                status=410,
                code="invitation_expired",
                title="Invitation expired",
                detail="Ask an organization administrator to resend the invitation.",
            )

    def _idempotent_token(self, *, organization_id: uuid.UUID, email: str, key: str) -> str:
        message = f"invitation:v1:{organization_id}:{email}:{key}".encode()
        digest = hmac.new(
            self.settings.csrf_signing_key.get_secret_value().encode(),
            message,
            hashlib.sha256,
        ).digest()
        return base64.urlsafe_b64encode(digest).decode().rstrip("=")

    @classmethod
    def _delivery_view(
        cls, invitation: OrganizationInvitation, token: str
    ) -> InvitationDeliveryView:
        return InvitationDeliveryView(
            **cls._invitation_view(invitation).model_dump(),
            acceptance_token=token,
        )

    @staticmethod
    def _invitation_view(invitation: OrganizationInvitation) -> InvitationView:
        if invitation.accepted_at is not None:
            invitation_status = "accepted"
        elif invitation.revoked_at is not None:
            invitation_status = "revoked"
        elif invitation.expires_at <= utc_now():
            invitation_status = "expired"
        else:
            invitation_status = "pending"
        return InvitationView(
            id=invitation.id,
            email=invitation.email,
            role=invitation.role,
            status=cast(
                Literal["pending", "expired", "accepted", "revoked"],
                invitation_status,
            ),
            invited_by_user_id=invitation.invited_by_user_id,
            expires_at=invitation.expires_at,
            created_at=invitation.created_at,
        )

    @staticmethod
    def _email_hint(email: str) -> str:
        local, separator, domain = email.partition("@")
        if not separator:
            return "hidden"
        visible = local[:1]
        return f"{visible}{'*' * max(3, len(local) - 1)}@{domain}"

    @staticmethod
    def _invalid_invitation() -> AppError:
        return AppError(
            status=404,
            code="invitation_not_found",
            title="Invitation not found",
            detail="This invitation link is invalid.",
        )
