from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response, status

from insightforge.api.dependencies import (
    CurrentIdentityDependency,
    RequestIdDependency,
    TenantContext,
    TenantContextDependency,
    get_billing_service,
    get_data_management_service,
    get_organization_service,
    get_organization_settings_service,
    require_csrf,
    require_permission,
)
from insightforge.core.concurrency import require_if_match, version_etag
from insightforge.core.policies import Permission
from insightforge.core.problems import AppError
from insightforge.models import Organization, OrganizationMember
from insightforge.schemas.billing import UsageView
from insightforge.schemas.common import DataEnvelope
from insightforge.schemas.organizations import (
    CurrentOrganizationView,
    DataExportRequest,
    DataExportView,
    OnboardingCompleteRequest,
    OrganizationCreateRequest,
    OrganizationDeletionRequest,
    OrganizationDeletionView,
    OrganizationJobView,
    OrganizationSummaryView,
    OrganizationUpdateRequest,
)
from insightforge.services.billing import BillingService
from insightforge.services.data_management import DataManagementService
from insightforge.services.organization_settings import OrganizationSettingsService
from insightforge.services.organizations import OrganizationService

router = APIRouter(prefix="/organizations", tags=["Organizations"])
OrganizationServiceDependency = Annotated[OrganizationService, Depends(get_organization_service)]
OrganizationSettingsDependency = Annotated[
    OrganizationSettingsService, Depends(get_organization_settings_service)
]
DataManagementDependency = Annotated[DataManagementService, Depends(get_data_management_service)]
BillingServiceDependency = Annotated[BillingService, Depends(get_billing_service)]
OrganizationEditContext = Annotated[TenantContext, require_permission(Permission.EDIT_ORGANIZATION)]
OrganizationDeleteContext = Annotated[
    TenantContext, require_permission(Permission.DELETE_ORGANIZATION)
]
OrganizationOwnerContext = Annotated[TenantContext, require_permission(Permission.MANAGE_BILLING)]


def summary_view(
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


async def current_view(
    context: TenantContext,
    service: OrganizationService,
) -> CurrentOrganizationView:
    subscription = await service.repository.subscription_for(context.organization.id)
    return CurrentOrganizationView(
        id=context.organization.id,
        name=context.organization.name,
        slug=context.organization.slug,
        reporting_currency=context.organization.reporting_currency,
        timezone=context.organization.timezone,
        industry=context.organization.industry,
        status=context.organization.status,
        onboarding_state=context.organization.onboarding_state,
        data_revision=context.organization.data_revision,
        version=context.organization.version,
        role=context.membership.role,
        permissions=sorted(permission.value for permission in context.permissions.values),
        is_demo=context.organization.is_demo,
        demo_expires_at=context.organization.demo_expires_at,
        demo_status=context.organization.demo_status,
        plan=subscription.plan if subscription is not None else "free",
    )


@router.get("", response_model=DataEnvelope[list[OrganizationSummaryView]])
async def list_organizations(
    identity: CurrentIdentityDependency,
    service: OrganizationServiceDependency,
) -> DataEnvelope[list[OrganizationSummaryView]]:
    memberships = await service.list_for_user(identity.user.id)
    return DataEnvelope(data=[summary_view(org, member) for org, member in memberships])


@router.post(
    "",
    response_model=DataEnvelope[OrganizationSummaryView],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_organization(
    payload: OrganizationCreateRequest,
    response: Response,
    identity: CurrentIdentityDependency,
    service: OrganizationServiceDependency,
) -> DataEnvelope[OrganizationSummaryView]:
    if identity.session.is_demo:
        raise AppError(
            status=403,
            code="demo_policy_denied",
            title="Action unavailable in demo mode",
            detail="Demo sessions cannot create additional organizations.",
        )
    organization, membership = await service.create(
        user=identity.user,
        name=payload.name,
        slug=payload.slug,
        reporting_currency=payload.reporting_currency,
        timezone=payload.timezone,
        industry=payload.industry,
    )
    response.headers["Location"] = "/api/v1/organizations/current"
    return DataEnvelope(data=summary_view(organization, membership))


@router.get("/current", response_model=DataEnvelope[CurrentOrganizationView])
async def current_organization(
    response: Response,
    context: TenantContextDependency,
    service: OrganizationServiceDependency,
) -> DataEnvelope[CurrentOrganizationView]:
    response.headers["ETag"] = version_etag(context.organization.version)
    return DataEnvelope(data=await current_view(context, service))


@router.patch(
    "/current",
    response_model=DataEnvelope[CurrentOrganizationView],
    dependencies=[Depends(require_csrf)],
)
async def update_current_organization(
    payload: OrganizationUpdateRequest,
    response: Response,
    context: OrganizationEditContext,
    settings_service: OrganizationSettingsDependency,
    organization_service: OrganizationServiceDependency,
    request_id: RequestIdDependency,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> DataEnvelope[CurrentOrganizationView]:
    context.organization = await settings_service.update(
        organization_id=context.organization.id,
        actor_user_id=context.identity.user.id,
        actor_is_demo=context.identity.session.is_demo,
        changes=payload.model_dump(exclude_unset=True),
        expected_version=require_if_match(if_match),
        request_id=request_id,
    )
    response.headers["ETag"] = version_etag(context.organization.version)
    return DataEnvelope(data=await current_view(context, organization_service))


@router.post(
    "/current/onboarding/complete",
    response_model=DataEnvelope[CurrentOrganizationView],
    dependencies=[Depends(require_csrf)],
)
async def complete_onboarding(
    payload: OnboardingCompleteRequest,
    context: OrganizationEditContext,
    settings_service: OrganizationSettingsDependency,
    organization_service: OrganizationServiceDependency,
    request_id: RequestIdDependency,
) -> DataEnvelope[CurrentOrganizationView]:
    context.organization = await settings_service.complete_onboarding(
        organization_id=context.organization.id,
        actor_user_id=context.identity.user.id,
        actor_is_demo=context.identity.session.is_demo,
        source_job_id=payload.source_job_id,
        empty_workspace=payload.empty_workspace,
        request_id=request_id,
    )
    return DataEnvelope(data=await current_view(context, organization_service))


@router.post(
    "/current/demo-data-jobs",
    response_model=DataEnvelope[OrganizationJobView],
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_csrf)],
)
async def create_demo_data_job(
    response: Response,
    context: OrganizationEditContext,
    service: OrganizationSettingsDependency,
    request_id: RequestIdDependency,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> DataEnvelope[OrganizationJobView]:
    job, replayed = await service.provision_demo_data(
        organization_id=context.organization.id,
        actor_user_id=context.identity.user.id,
        actor_is_demo=context.identity.session.is_demo,
        request_id=request_id,
        idempotency_key=idempotency_key,
    )
    response.headers["Location"] = f"/api/v1/organizations/current/demo-data-jobs/{job.id}"
    response.headers["Idempotency-Replayed"] = "true" if replayed else "false"
    return DataEnvelope(data=job)


@router.get(
    "/current/demo-data-jobs/{job_id}",
    response_model=DataEnvelope[OrganizationJobView],
)
async def get_demo_data_job(
    job_id: uuid.UUID,
    context: OrganizationEditContext,
    service: OrganizationSettingsDependency,
) -> DataEnvelope[OrganizationJobView]:
    return DataEnvelope(data=await service.demo_data_job(context.organization.id, job_id))


@router.get("/current/usage", response_model=DataEnvelope[UsageView])
async def get_organization_usage(
    context: OrganizationEditContext,
    service: BillingServiceDependency,
) -> DataEnvelope[UsageView]:
    return DataEnvelope(data=await service.usage(context.organization.id))


@router.delete(
    "/current",
    response_model=DataEnvelope[OrganizationDeletionView],
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_csrf)],
)
async def request_organization_deletion(
    payload: OrganizationDeletionRequest,
    context: OrganizationDeleteContext,
    service: DataManagementDependency,
    request_id: RequestIdDependency,
) -> DataEnvelope[OrganizationDeletionView]:
    result = await service.request_deletion(
        organization_id=context.organization.id,
        actor_user_id=context.identity.user.id,
        actor_is_demo=context.identity.session.is_demo,
        confirmation_name=payload.organization_name,
        request_id=request_id,
    )
    return DataEnvelope(data=result)


@router.get(
    "/current/deletion",
    response_model=DataEnvelope[OrganizationDeletionView],
)
async def get_organization_deletion(
    context: OrganizationDeleteContext,
    service: DataManagementDependency,
) -> DataEnvelope[OrganizationDeletionView]:
    return DataEnvelope(data=await service.deletion_status(context.organization.id))


@router.delete(
    "/current/deletion",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def cancel_organization_deletion(
    context: OrganizationDeleteContext,
    service: DataManagementDependency,
    request_id: RequestIdDependency,
) -> Response:
    await service.cancel_deletion(
        organization_id=context.organization.id,
        actor_user_id=context.identity.user.id,
        actor_is_demo=context.identity.session.is_demo,
        request_id=request_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/current/data-exports",
    response_model=DataEnvelope[DataExportView],
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_csrf)],
)
async def request_data_export(
    _payload: DataExportRequest,
    response: Response,
    context: OrganizationOwnerContext,
    service: DataManagementDependency,
    request_id: RequestIdDependency,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> DataEnvelope[DataExportView]:
    export, replayed = await service.request_export(
        organization_id=context.organization.id,
        actor_user_id=context.identity.user.id,
        actor_is_demo=context.identity.session.is_demo,
        request_id=request_id,
        idempotency_key=idempotency_key,
    )
    response.headers["Location"] = f"/api/v1/organizations/current/data-exports/{export.id}"
    response.headers["Idempotency-Replayed"] = "true" if replayed else "false"
    return DataEnvelope(data=export)


@router.get(
    "/current/data-exports/{export_id}",
    response_model=DataEnvelope[DataExportView],
)
async def get_data_export(
    export_id: uuid.UUID,
    context: OrganizationOwnerContext,
    service: DataManagementDependency,
) -> DataEnvelope[DataExportView]:
    return DataEnvelope(data=await service.export_status(context.organization.id, export_id))


@router.get("/current/data-exports/{export_id}/download")
async def download_data_export(
    export_id: uuid.UUID,
    context: OrganizationOwnerContext,
    service: DataManagementDependency,
) -> Response:
    payload, filename, content_type, content_sha256 = await service.download_export(
        context.organization.id, export_id
    )
    return Response(
        content=payload,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-SHA256": content_sha256,
        },
    )
