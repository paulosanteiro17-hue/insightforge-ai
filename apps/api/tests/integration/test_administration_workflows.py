from __future__ import annotations

import asyncio
import hashlib
import os
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from insightforge.core.config import Settings
from insightforge.core.problems import AppError
from insightforge.core.time import utc_now
from insightforge.db.session import get_session_factory
from insightforge.main import create_app
from insightforge.models import (
    AuditLog,
    BackgroundJob,
    IdempotencyRecord,
    Organization,
    OrganizationInvitation,
    User,
)
from insightforge.services.invitations import InvitationService
from insightforge.worker.runner import (
    cleanup_expired_demo_organizations,
    cleanup_expired_exports,
    run_worker_once,
)

pytestmark = pytest.mark.postgres
PASSWORD = "PortfolioPassword-2026"
NEW_PASSWORD = "UpdatedPortfolioPassword-2026"


def _settings(database_url: str, private_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        environment="testing",
        database_url=database_url,
        private_storage_path=private_path,
        allowed_origins=["http://testserver"],
        csrf_allowed_origins=["http://testserver"],
        allowed_hosts=["testserver"],
        csrf_signing_key="administration-integration-signing-key-that-is-long-enough",
        invitation_account_limit=100,
        invitation_resend_limit=100,
        password_change_limit=100,
    )


def _csrf_headers(client: TestClient, settings: Settings) -> dict[str, str]:
    csrf = client.get("/api/v1/auth/csrf-token").json()["data"]["csrf_token"]
    return {"Origin": "http://testserver", "X-CSRF-Token": csrf}


def _write_headers(
    client: TestClient, settings: Settings, organization_id: str | None = None
) -> dict[str, str]:
    headers = {
        "Origin": "http://testserver",
        "X-CSRF-Token": client.cookies[settings.csrf_cookie_name],
    }
    if organization_id is not None:
        headers["X-Organization-ID"] = organization_id
    return headers


def _register(
    client: TestClient,
    settings: Settings,
    *,
    email: str,
    display_name: str,
    password: str = PASSWORD,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/auth/register",
        headers=_csrf_headers(client, settings),
        json={"email": email, "password": password, "display_name": display_name},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _login(client: TestClient, settings: Settings, *, email: str, password: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        headers=_csrf_headers(client, settings),
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text


def _create_organization(
    client: TestClient,
    settings: Settings,
    *,
    name: str,
) -> str:
    response = client.post(
        "/api/v1/organizations",
        headers=_write_headers(client, settings),
        json={"name": name, "reporting_currency": "USD", "timezone": "UTC"},
    )
    assert response.status_code == 201, response.text
    return str(response.json()["data"]["id"])


def _save_cookies(client: TestClient) -> dict[str, str]:
    return {cookie.name: cookie.value for cookie in client.cookies.jar}


def _restore_cookies(client: TestClient, cookies: dict[str, str]) -> None:
    client.cookies.clear()
    for name, value in cookies.items():
        client.cookies.set(name, value)


async def _stored_invitation_security(
    settings: Settings,
    invitation_id: str,
    raw_token: str,
    idempotency_key: str,
) -> tuple[bool, bool]:
    async with get_session_factory(settings.database_url)() as db:
        invitation = await db.get(OrganizationInvitation, uuid.UUID(invitation_id))
        record = await db.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.operation == "invite_team_member",
                IdempotencyRecord.idempotency_key == idempotency_key,
            )
        )
        assert invitation is not None
        assert record is not None
        digest_only = invitation.token_hash == hashlib.sha256(raw_token.encode()).hexdigest()
        response_does_not_store_token = raw_token not in str(record.response_body)
        return digest_only, response_does_not_store_token


async def _accept_invitation_race(
    settings: Settings,
    token: str,
    user_id: str,
    email: str,
) -> list[str]:
    start = asyncio.Event()

    async def attempt() -> str:
        async with get_session_factory(settings.database_url)() as db:
            service = InvitationService(db, settings)
            await start.wait()
            try:
                await service.accept(
                    token=token,
                    user_id=uuid.UUID(user_id),
                    user_email=email,
                    actor_is_demo=False,
                    request_id=uuid.uuid4(),
                )
            except AppError as exc:
                return exc.code
            return "accepted"

    tasks = [asyncio.create_task(attempt()), asyncio.create_task(attempt())]
    await asyncio.sleep(0)
    start.set()
    return list(await asyncio.gather(*tasks))


async def _expire_invitation(settings: Settings, invitation_id: str) -> None:
    async with get_session_factory(settings.database_url)() as db:
        invitation = await db.get(OrganizationInvitation, uuid.UUID(invitation_id))
        assert invitation is not None
        invitation.expires_at = utc_now() - timedelta(seconds=1)
        await db.commit()


async def _expire_export(settings: Settings, export_id: str) -> None:
    async with get_session_factory(settings.database_url)() as db:
        job = await db.get(BackgroundJob, uuid.UUID(export_id))
        assert job is not None
        job.payload = {
            **job.payload,
            "expires_at": (utc_now() - timedelta(seconds=1)).isoformat(),
        }
        await db.commit()


async def _make_deletion_due(settings: Settings, organization_id: str) -> str:
    async with get_session_factory(settings.database_url)() as db:
        job = await db.scalar(
            select(BackgroundJob)
            .where(
                BackgroundJob.organization_id == uuid.UUID(organization_id),
                BackgroundJob.job_type == "delete_organization",
                BackgroundJob.status == "queued",
            )
            .order_by(BackgroundJob.created_at.desc())
            .limit(1)
        )
        assert job is not None
        due_at = utc_now() - timedelta(seconds=1)
        job.run_after = due_at
        job.payload = {**job.payload, "effective_deletion_at": due_at.isoformat()}
        await db.commit()
        return str(job.id)


async def _deletion_persistence(
    settings: Settings,
    deleted_organization_id: str,
    retained_organization_ids: list[str],
) -> tuple[bool, list[bool], bool]:
    deleted_id = uuid.UUID(deleted_organization_id)
    async with get_session_factory(settings.database_url)() as db:
        deleted = await db.get(Organization, deleted_id)
        retained = [
            await db.get(Organization, uuid.UUID(organization_id)) is not None
            for organization_id in retained_organization_ids
        ]
        audit = await db.scalar(
            select(AuditLog.id).where(
                AuditLog.action == "organization.deletion.completed",
                AuditLog.resource_id == deleted_id,
            )
        )
        return deleted is None, retained, audit is not None


async def _expire_demo(settings: Settings, organization_id: str) -> None:
    async with get_session_factory(settings.database_url)() as db:
        organization = await db.get(Organization, uuid.UUID(organization_id))
        assert organization is not None and organization.is_demo
        organization.demo_status = "expired"
        organization.demo_expires_at = utc_now() - timedelta(seconds=1)
        await db.commit()


async def _demo_cleanup_persistence(
    settings: Settings,
    demo_organization_id: str,
    demo_user_id: str,
    retained_organization_id: str,
) -> tuple[bool, bool, bool, bool]:
    demo_org_id = uuid.UUID(demo_organization_id)
    async with get_session_factory(settings.database_url)() as db:
        demo_organization = await db.get(Organization, demo_org_id)
        demo_user = await db.get(User, uuid.UUID(demo_user_id))
        retained = await db.get(Organization, uuid.UUID(retained_organization_id))
        audit = await db.scalar(
            select(AuditLog.id).where(
                AuditLog.action == "demo.organization.expired",
                AuditLog.resource_id == demo_org_id,
            )
        )
        return (
            demo_organization is None,
            demo_user is None,
            retained is not None,
            audit is not None,
        )


def test_profile_preferences_and_password_revoke_other_sessions(tmp_path: Path) -> None:
    database_url = os.environ.get("INSIGHTFORGE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("INSIGHTFORGE_TEST_DATABASE_URL is not configured.")
    settings = _settings(database_url, tmp_path / "private")
    application = create_app(settings)
    suffix = uuid.uuid4().hex[:12]
    email = f"profile-{suffix}@example.com"

    with TestClient(application) as client:
        _register(client, settings, email=email, display_name="Profile Owner")
        primary_cookies = _save_cookies(client)
        client.cookies.clear()
        _login(client, settings, email=email, password=PASSWORD)
        secondary_cookies = _save_cookies(client)
        _restore_cookies(client, primary_cookies)

        profile = client.patch(
            "/api/v1/users/me",
            headers=_write_headers(client, settings),
            json={
                "display_name": "Morgan Profile",
                "locale": "en-GB",
                "time_zone": "Europe/London",
            },
        )
        assert profile.status_code == 200, profile.text
        assert profile.json()["data"]["display_name"] == "Morgan Profile"
        assert profile.json()["data"]["locale"] == "en-GB"

        preferences = client.patch(
            "/api/v1/users/me/preferences",
            headers=_write_headers(client, settings),
            json={"weekly_summary_email": False, "compact_tables": True},
        )
        assert preferences.status_code == 200, preferences.text
        assert preferences.json()["data"]["weekly_summary_email"] is False
        assert preferences.json()["data"]["compact_tables"] is True
        fetched = client.get("/api/v1/users/me")
        assert fetched.json()["data"]["preferences"]["compact_tables"] is True

        incorrect = client.patch(
            "/api/v1/users/me/password",
            headers=_write_headers(client, settings),
            json={"current_password": "IncorrectPassword", "new_password": NEW_PASSWORD},
        )
        assert incorrect.status_code == 400
        assert incorrect.json()["code"] == "invalid_current_password"

        changed = client.patch(
            "/api/v1/users/me/password",
            headers=_write_headers(client, settings),
            json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        )
        assert changed.status_code == 204, changed.text
        assert client.get("/api/v1/auth/session").status_code == 200
        _restore_cookies(client, secondary_cookies)
        revoked = client.get("/api/v1/auth/session")
        assert revoked.status_code == 401
        assert revoked.json()["code"] == "session_expired"

        old_login = client.post(
            "/api/v1/auth/login",
            headers=_csrf_headers(client, settings),
            json={"email": email, "password": PASSWORD},
        )
        assert old_login.status_code == 401
        _login(client, settings, email=email, password=NEW_PASSWORD)


def test_onboarding_billing_export_deletion_and_demo_policy(tmp_path: Path) -> None:
    database_url = os.environ.get("INSIGHTFORGE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("INSIGHTFORGE_TEST_DATABASE_URL is not configured.")
    settings = _settings(database_url, tmp_path / "private")
    application = create_app(settings)
    suffix = uuid.uuid4().hex[:12]

    with TestClient(application) as client:
        _register(
            client,
            settings,
            email=f"operations-{suffix}@example.com",
            display_name="Operations Owner",
        )
        organization_id = _create_organization(client, settings, name=f"Atlas Operations {suffix}")
        headers = _write_headers(client, settings, organization_id)
        current = client.get("/api/v1/organizations/current", headers=headers)
        original_etag = current.headers["ETag"]
        updated_name = f"Atlas Intelligence {suffix}"
        updated = client.patch(
            "/api/v1/organizations/current",
            headers={**headers, "If-Match": original_etag},
            json={"name": updated_name, "timezone": "America/New_York"},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["data"]["name"] == updated_name
        stale = client.patch(
            "/api/v1/organizations/current",
            headers={**headers, "If-Match": original_etag},
            json={"industry": "Software"},
        )
        assert stale.status_code == 412
        assert stale.json()["code"] == "version_conflict"

        seed_key = str(uuid.uuid4())
        seeded = client.post(
            "/api/v1/organizations/current/demo-data-jobs",
            headers={**headers, "Idempotency-Key": seed_key},
        )
        assert seeded.status_code == 202, seeded.text
        seed_data = seeded.json()["data"]
        assert seed_data["status"] == "succeeded"
        assert seed_data["result"]["customers"] == 60
        replayed_seed = client.post(
            "/api/v1/organizations/current/demo-data-jobs",
            headers={**headers, "Idempotency-Key": seed_key},
        )
        assert replayed_seed.status_code == 202, replayed_seed.text
        assert replayed_seed.headers["Idempotency-Replayed"] == "true"
        assert replayed_seed.json() == seeded.json()
        duplicate_seed = client.post(
            "/api/v1/organizations/current/demo-data-jobs",
            headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
        )
        assert duplicate_seed.status_code == 409

        completed = client.post(
            "/api/v1/organizations/current/onboarding/complete",
            headers=headers,
            json={"source_job_id": seed_data["id"]},
        )
        assert completed.status_code == 200, completed.text
        assert completed.json()["data"]["onboarding_state"] == "complete"
        seed_status = client.get(
            f"/api/v1/organizations/current/demo-data-jobs/{seed_data['id']}",
            headers=headers,
        )
        assert seed_status.status_code == 200

        usage = client.get("/api/v1/organizations/current/usage", headers=headers)
        assert usage.status_code == 200
        assert usage.json()["data"]["customers"]["used"] == 60

        billing_key = str(uuid.uuid4())
        upgraded = client.post(
            "/api/v1/billing/upgrade-intents",
            headers={**headers, "Idempotency-Key": billing_key},
            json={"plan": "business"},
        )
        assert upgraded.status_code == 201, upgraded.text
        assert upgraded.json()["data"]["mode"] == "demo"
        assert "No payment was collected" in upgraded.json()["data"]["message"]
        replayed_upgrade = client.post(
            "/api/v1/billing/upgrade-intents",
            headers={**headers, "Idempotency-Key": billing_key},
            json={"plan": "business"},
        )
        assert replayed_upgrade.headers["Idempotency-Replayed"] == "true"
        assert replayed_upgrade.json() == upgraded.json()
        subscription = client.get("/api/v1/billing/subscription", headers=headers)
        assert subscription.json()["data"]["plan"] == "business"
        invoices = client.get("/api/v1/billing/invoices", headers=headers)
        assert invoices.json()["meta"]["pagination"]["total"] == 6
        assert all(invoice["hosted_url"] is None for invoice in invoices.json()["data"])

        export_key = str(uuid.uuid4())
        exported = client.post(
            "/api/v1/organizations/current/data-exports",
            headers={**headers, "Idempotency-Key": export_key},
            json={"format": "json"},
        )
        assert exported.status_code == 202, exported.text
        export_data = exported.json()["data"]
        assert export_data["status"] == "succeeded"
        replayed_export = client.post(
            "/api/v1/organizations/current/data-exports",
            headers={**headers, "Idempotency-Key": export_key},
            json={"format": "json"},
        )
        assert replayed_export.headers["Idempotency-Replayed"] == "true"
        assert replayed_export.json() == exported.json()
        downloaded = client.get(export_data["download_url"], headers=headers)
        assert downloaded.status_code == 200, downloaded.text
        assert hashlib.sha256(downloaded.content).hexdigest() == export_data["content_sha256"]
        assert downloaded.json()["organization"]["id"] == organization_id
        assert "password_hash" not in downloaded.text
        retained_export = client.post(
            "/api/v1/organizations/current/data-exports",
            headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
            json={"format": "json"},
        )
        assert retained_export.status_code == 202, retained_export.text
        client.portal.call(_expire_export, settings, export_data["id"])
        assert client.portal.call(cleanup_expired_exports, settings) == 1
        expired_export = client.get(
            f"/api/v1/organizations/current/data-exports/{export_data['id']}",
            headers=headers,
        )
        assert expired_export.json()["data"]["status"] == "expired"
        assert client.get(export_data["download_url"], headers=headers).status_code == 410
        assert (
            client.get(retained_export.json()["data"]["download_url"], headers=headers).status_code
            == 200
        )

        second_organization_id = _create_organization(
            client, settings, name=f"Second Operations {suffix}"
        )
        second_headers = _write_headers(client, settings, second_organization_id)
        cross_tenant_export = client.get(
            f"/api/v1/organizations/current/data-exports/{export_data['id']}",
            headers=second_headers,
        )
        assert cross_tenant_export.status_code == 404
        cross_tenant_job = client.get(
            f"/api/v1/organizations/current/demo-data-jobs/{seed_data['id']}",
            headers=second_headers,
        )
        assert cross_tenant_job.status_code == 404

        mismatch = client.request(
            "DELETE",
            "/api/v1/organizations/current",
            headers=headers,
            json={"organization_name": "Wrong organization"},
        )
        assert mismatch.status_code == 422
        deletion = client.request(
            "DELETE",
            "/api/v1/organizations/current",
            headers=headers,
            json={"organization_name": updated_name},
        )
        assert deletion.status_code == 202, deletion.text
        assert deletion.json()["data"]["cancellable"] is True
        deletion_status = client.get("/api/v1/organizations/current/deletion", headers=headers)
        assert deletion_status.json()["data"]["job_id"] == deletion.json()["data"]["job_id"]
        cancelled = client.delete("/api/v1/organizations/current/deletion", headers=headers)
        assert cancelled.status_code == 204, cancelled.text
        assert (
            client.get("/api/v1/organizations/current/deletion", headers=headers).json()["data"][
                "status"
            ]
            == "cancelled"
        )

        client.cookies.clear()
        demo_csrf = _csrf_headers(client, settings)
        demo = client.post(
            "/api/v1/auth/demo-session",
            headers={**demo_csrf, "Idempotency-Key": str(uuid.uuid4())},
            json={},
        )
        assert demo.status_code == 201, demo.text
        demo_organization_id = demo.json()["data"]["organizations"][0]["id"]
        demo_headers = _write_headers(client, settings, demo_organization_id)
        denied_invite = client.post(
            "/api/v1/team/invitations",
            headers=demo_headers,
            json={"email": f"external-{suffix}@example.com", "role": "member"},
        )
        assert denied_invite.status_code == 403
        denied_password = client.patch(
            "/api/v1/users/me/password",
            headers=demo_headers,
            json={"current_password": "unknown-password", "new_password": NEW_PASSWORD},
        )
        assert denied_password.status_code == 403
        denied_deletion = client.request(
            "DELETE",
            "/api/v1/organizations/current",
            headers=demo_headers,
            json={"organization_name": "Northstar Demo"},
        )
        assert denied_deletion.status_code == 403
        demo_upgrade = client.post(
            "/api/v1/billing/upgrade-intents",
            headers={**demo_headers, "Idempotency-Key": str(uuid.uuid4())},
            json={"plan": "business"},
        )
        assert demo_upgrade.status_code == 201, demo_upgrade.text
        assert demo_upgrade.json()["data"]["mode"] == "demo"


def test_team_invitation_permissions_isolation_and_concurrency(tmp_path: Path) -> None:
    database_url = os.environ.get("INSIGHTFORGE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("INSIGHTFORGE_TEST_DATABASE_URL is not configured.")
    settings = _settings(database_url, tmp_path / "private")
    application = create_app(settings)
    suffix = uuid.uuid4().hex[:12]
    owner_email = f"owner-{suffix}@example.com"
    member_email = f"member-{suffix}@example.com"
    race_email = f"race-{suffix}@example.com"

    with TestClient(application) as client:
        _register(client, settings, email=owner_email, display_name="Team Owner")
        organization_id = _create_organization(client, settings, name=f"Team Studio {suffix}")
        owner_headers = _write_headers(client, settings, organization_id)
        owner_cookies = _save_cookies(client)

        invite_key = str(uuid.uuid4())
        invited = client.post(
            "/api/v1/team/invitations",
            headers={**owner_headers, "Idempotency-Key": invite_key},
            json={"email": member_email, "role": "member"},
        )
        assert invited.status_code == 201, invited.text
        invitation = invited.json()["data"]
        token = invitation["acceptance_token"]
        replayed = client.post(
            "/api/v1/team/invitations",
            headers={**owner_headers, "Idempotency-Key": invite_key},
            json={"email": member_email, "role": "member"},
        )
        assert replayed.headers["Idempotency-Replayed"] == "true"
        assert replayed.json() == invited.json()
        assert client.get(f"/api/v1/team/invitations/accept/{token}").status_code == 200
        assert client.portal is not None
        digest_only, no_plaintext = client.portal.call(
            _stored_invitation_security,
            settings,
            invitation["id"],
            token,
            invite_key,
        )
        assert digest_only and no_plaintext

        client.cookies.clear()
        _register(
            client,
            settings,
            email=f"wrong-{suffix}@example.com",
            display_name="Wrong Account",
        )
        wrong_accept = client.post(
            f"/api/v1/team/invitations/accept/{token}",
            headers=_write_headers(client, settings),
        )
        assert wrong_accept.status_code == 403
        assert wrong_accept.json()["code"] == "invitation_email_mismatch"

        client.cookies.clear()
        member_account = _register(
            client,
            settings,
            email=member_email,
            display_name="Team Member",
        )
        accepted = client.post(
            f"/api/v1/team/invitations/accept/{token}",
            headers=_write_headers(client, settings),
        )
        assert accepted.status_code == 200, accepted.text
        member_id = accepted.json()["data"]["member"]["id"]
        repeated_accept = client.post(
            f"/api/v1/team/invitations/accept/{token}",
            headers=_write_headers(client, settings),
        )
        assert repeated_accept.status_code == 409
        assert repeated_accept.json()["code"] == "invitation_already_accepted"
        member_cookies = _save_cookies(client)
        member_headers = _write_headers(client, settings, organization_id)
        assert client.get("/api/v1/team/members", headers=member_headers).status_code == 200
        assert (
            client.post(
                "/api/v1/team/invitations",
                headers=member_headers,
                json={"email": f"blocked-{suffix}@example.com", "role": "member"},
            ).status_code
            == 403
        )
        assert client.get("/api/v1/billing/subscription", headers=member_headers).status_code == 403

        _restore_cookies(client, owner_cookies)
        owner_headers = _write_headers(client, settings, organization_id)
        promoted = client.patch(
            f"/api/v1/team/members/{member_id}",
            headers=owner_headers,
            json={"role": "admin"},
        )
        assert promoted.status_code == 200, promoted.text
        assert promoted.json()["data"]["role"] == "admin"

        _restore_cookies(client, member_cookies)
        admin_headers = _write_headers(client, settings, organization_id)
        denied_admin_invite = client.post(
            "/api/v1/team/invitations",
            headers=admin_headers,
            json={"email": f"admin-{suffix}@example.com", "role": "admin"},
        )
        assert denied_admin_invite.status_code == 403
        pending = client.post(
            "/api/v1/team/invitations",
            headers=admin_headers,
            json={"email": f"pending-{suffix}@example.com", "role": "member"},
        )
        assert pending.status_code == 201, pending.text
        old_token = pending.json()["data"]["acceptance_token"]
        resent = client.post(
            f"/api/v1/team/invitations/{pending.json()['data']['id']}/resend",
            headers=admin_headers,
        )
        assert resent.status_code == 202, resent.text
        new_token = resent.json()["data"]["acceptance_token"]
        assert new_token != old_token
        assert client.get(f"/api/v1/team/invitations/accept/{old_token}").status_code == 404
        assert client.get(f"/api/v1/team/invitations/accept/{new_token}").status_code == 200
        revoked = client.delete(
            f"/api/v1/team/invitations/{pending.json()['data']['id']}",
            headers=admin_headers,
        )
        assert revoked.status_code == 204
        assert client.get(f"/api/v1/team/invitations/accept/{new_token}").status_code == 410

        _restore_cookies(client, owner_cookies)
        owner_headers = _write_headers(client, settings, organization_id)
        race_invitation = client.post(
            "/api/v1/team/invitations",
            headers=owner_headers,
            json={"email": race_email, "role": "member"},
        )
        assert race_invitation.status_code == 201, race_invitation.text
        race_token = race_invitation.json()["data"]["acceptance_token"]
        client.cookies.clear()
        race_account = _register(
            client,
            settings,
            email=race_email,
            display_name="Concurrent Member",
        )
        race_results = client.portal.call(
            _accept_invitation_race,
            settings,
            race_token,
            str(race_account["user"]["id"]),
            race_email,
        )
        assert sorted(race_results) == ["accepted", "invitation_already_accepted"]

        _restore_cookies(client, owner_cookies)
        owner_headers = _write_headers(client, settings, organization_id)
        expiring = client.post(
            "/api/v1/team/invitations",
            headers=owner_headers,
            json={"email": f"expired-{suffix}@example.com", "role": "member"},
        )
        assert expiring.status_code == 201
        client.portal.call(_expire_invitation, settings, expiring.json()["data"]["id"])
        expired_preview = client.get(
            f"/api/v1/team/invitations/accept/{expiring.json()['data']['acceptance_token']}"
        )
        assert expired_preview.status_code == 410
        assert expired_preview.json()["code"] == "invitation_expired"

        members = client.get("/api/v1/team/members", headers=owner_headers).json()["data"]
        owner_member_id = next(member["id"] for member in members if member["role"] == "owner")
        change_owner = client.patch(
            f"/api/v1/team/members/{owner_member_id}",
            headers=owner_headers,
            json={"role": "admin"},
        )
        assert change_owner.status_code == 409
        assert change_owner.json()["code"] == "final_owner_required"
        remove_owner = client.delete(
            f"/api/v1/team/members/{owner_member_id}", headers=owner_headers
        )
        assert remove_owner.status_code == 409
        leave_owner = client.post("/api/v1/team/leave", headers=owner_headers)
        assert leave_owner.status_code == 409

        second_organization_id = _create_organization(
            client, settings, name=f"Isolated Team {suffix}"
        )
        second_headers = _write_headers(client, settings, second_organization_id)
        cross_tenant = client.patch(
            f"/api/v1/team/members/{member_id}",
            headers=second_headers,
            json={"role": "member"},
        )
        assert cross_tenant.status_code == 404

        assert member_account["user"]["email"] == member_email


def test_worker_honors_deletion_grace_cancellation_and_exact_tenant(tmp_path: Path) -> None:
    database_url = os.environ.get("INSIGHTFORGE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("INSIGHTFORGE_TEST_DATABASE_URL is not configured.")
    settings = _settings(database_url, tmp_path / "private")
    application = create_app(settings)
    suffix = uuid.uuid4().hex[:12]

    with TestClient(application) as client:
        _register(
            client,
            settings,
            email=f"deletion-{suffix}@example.com",
            display_name="Deletion Owner",
        )
        victim_id = _create_organization(client, settings, name=f"Delete Target {suffix}")
        cancelled_id = _create_organization(client, settings, name=f"Cancelled Target {suffix}")
        survivor_id = _create_organization(client, settings, name=f"Surviving Tenant {suffix}")

        cancelled_headers = _write_headers(client, settings, cancelled_id)
        cancellation_request = client.request(
            "DELETE",
            "/api/v1/organizations/current",
            headers=cancelled_headers,
            json={"organization_name": f"Cancelled Target {suffix}"},
        )
        assert cancellation_request.status_code == 202
        assert (
            client.delete(
                "/api/v1/organizations/current/deletion", headers=cancelled_headers
            ).status_code
            == 204
        )

        victim_headers = _write_headers(client, settings, victim_id)
        deletion_request = client.request(
            "DELETE",
            "/api/v1/organizations/current",
            headers=victim_headers,
            json={"organization_name": f"Delete Target {suffix}"},
        )
        assert deletion_request.status_code == 202
        assert client.portal is not None
        # The future run_after protects the tenant until the grace period ends.
        client.portal.call(run_worker_once, settings)
        assert (
            client.get("/api/v1/organizations/current", headers=victim_headers).status_code == 200
        )

        client.portal.call(_make_deletion_due, settings, victim_id)
        assert client.portal.call(run_worker_once, settings)
        deleted, retained, audited = client.portal.call(
            _deletion_persistence,
            settings,
            victim_id,
            [cancelled_id, survivor_id],
        )
        assert deleted
        assert retained == [True, True]
        assert audited
        assert (
            client.get("/api/v1/organizations/current", headers=victim_headers).status_code == 404
        )
        assert (
            client.get(
                "/api/v1/organizations/current",
                headers=_write_headers(client, settings, survivor_id),
            ).status_code
            == 200
        )


def test_worker_purges_only_expired_demo_tenant_and_private_artifacts(tmp_path: Path) -> None:
    database_url = os.environ.get("INSIGHTFORGE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("INSIGHTFORGE_TEST_DATABASE_URL is not configured.")
    settings = _settings(database_url, tmp_path / "private")
    application = create_app(settings)
    suffix = uuid.uuid4().hex[:12]

    with TestClient(application) as client:
        demo = client.post(
            "/api/v1/auth/demo-session",
            headers={
                **_csrf_headers(client, settings),
                "Idempotency-Key": str(uuid.uuid4()),
            },
            json={},
        )
        assert demo.status_code == 201, demo.text
        demo_data = demo.json()["data"]
        demo_organization_id = demo_data["organizations"][0]["id"]
        demo_user_id = demo_data["user"]["id"]
        demo_headers = _write_headers(client, settings, demo_organization_id)
        exported = client.post(
            "/api/v1/organizations/current/data-exports",
            headers={**demo_headers, "Idempotency-Key": str(uuid.uuid4())},
            json={"format": "json"},
        )
        assert exported.status_code == 202, exported.text
        export_id = exported.json()["data"]["id"]
        export_path = (
            settings.private_storage_path
            / "exports"
            / uuid.UUID(demo_organization_id).hex
            / f"{uuid.UUID(export_id).hex}.json"
        )
        assert export_path.exists()

        client.cookies.clear()
        _register(
            client,
            settings,
            email=f"retained-{suffix}@example.com",
            display_name="Retained Owner",
        )
        retained_organization_id = _create_organization(
            client, settings, name=f"Retained Organization {suffix}"
        )
        retained_headers = _write_headers(client, settings, retained_organization_id)
        assert client.portal is not None
        client.portal.call(_expire_demo, settings, demo_organization_id)
        assert client.portal.call(cleanup_expired_demo_organizations, settings) >= 1
        assert not export_path.exists()
        cleaned = client.portal.call(
            _demo_cleanup_persistence,
            settings,
            demo_organization_id,
            demo_user_id,
            retained_organization_id,
        )
        assert cleaned == (True, True, True, True)
        assert (
            client.get("/api/v1/organizations/current", headers=retained_headers).status_code == 200
        )
