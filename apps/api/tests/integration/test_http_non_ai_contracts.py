from __future__ import annotations

import hashlib
import os
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from insightforge.core.config import Settings
from insightforge.main import create_app

pytestmark = pytest.mark.postgres

ORIGIN = "http://testserver"
PASSWORD = "PortfolioContractPassword-2026"
UPDATED_PASSWORD = "UpdatedContractPassword-2026"


@dataclass(slots=True)
class HttpApi:
    client: TestClient
    settings: Settings

    def csrf_headers(self) -> dict[str, str]:
        response = self.client.get("/api/v1/auth/csrf-token")
        assert response.status_code == 200, response.text
        return {
            "Origin": ORIGIN,
            "X-CSRF-Token": response.json()["data"]["csrf_token"],
        }

    def write_headers(
        self,
        organization_id: str | None = None,
        *,
        idempotency_key: str | None = None,
        if_match: str | None = None,
    ) -> dict[str, str]:
        headers = {
            "Origin": ORIGIN,
            "X-CSRF-Token": self.client.cookies[self.settings.csrf_cookie_name],
        }
        if organization_id is not None:
            headers["X-Organization-ID"] = organization_id
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        if if_match is not None:
            headers["If-Match"] = if_match
        return headers

    def tenant_headers(self, organization_id: str) -> dict[str, str]:
        return {"X-Organization-ID": organization_id}

    def register(
        self,
        *,
        email: str,
        display_name: str,
        password: str = PASSWORD,
    ) -> dict[str, Any]:
        response = self.client.post(
            "/api/v1/auth/register",
            headers=self.csrf_headers(),
            json={
                "email": email,
                "password": password,
                "display_name": display_name,
            },
        )
        assert response.status_code == 201, response.text
        return response.json()["data"]

    def login(self, *, email: str, password: str = PASSWORD) -> dict[str, Any]:
        response = self.client.post(
            "/api/v1/auth/login",
            headers=self.csrf_headers(),
            json={"email": email, "password": password},
        )
        assert response.status_code == 200, response.text
        return response.json()["data"]

    def create_organization(self, *, name: str) -> str:
        response = self.client.post(
            "/api/v1/organizations",
            headers=self.write_headers(),
            json={
                "name": name,
                "reporting_currency": "USD",
                "timezone": "UTC",
                "industry": "Professional Services",
            },
        )
        assert response.status_code == 201, response.text
        return str(response.json()["data"]["id"])

    def save_cookies(self) -> dict[str, str]:
        return {cookie.name: cookie.value for cookie in self.client.cookies.jar}

    def restore_cookies(self, cookies: dict[str, str]) -> None:
        self.client.cookies.clear()
        for name, value in cookies.items():
            self.client.cookies.set(name, value)


@pytest.fixture
def http_api(tmp_path: Path) -> Iterator[HttpApi]:
    database_url = os.environ.get("INSIGHTFORGE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("INSIGHTFORGE_TEST_DATABASE_URL is not configured.")
    settings = Settings(
        _env_file=None,
        environment="testing",
        database_url=database_url,
        private_storage_path=tmp_path / "private",
        allowed_origins=[ORIGIN],
        csrf_allowed_origins=[ORIGIN],
        allowed_hosts=["testserver"],
        csrf_signing_key="http-contract-signing-key-that-is-long-enough-for-testing",
        auth_global_limit=1_000,
        register_browser_limit=100,
        login_account_limit=100,
        demo_browser_limit=100,
        demo_global_limit=100,
        invitation_account_limit=100,
        invitation_resend_limit=100,
        password_change_limit=100,
    )
    application = create_app(settings)
    with TestClient(application) as client:
        yield HttpApi(client=client, settings=settings)


def _data(response: Response, expected_status: int) -> dict[str, Any]:
    assert response.status_code == expected_status, response.text
    return response.json()["data"]


def _assert_problem(response: Response, expected_status: int, expected_code: str) -> None:
    assert response.status_code == expected_status, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == expected_code


def _create_customer(
    api: HttpApi,
    organization_id: str,
    *,
    name: str,
    email: str,
) -> tuple[dict[str, Any], str]:
    response = api.client.post(
        "/api/v1/customers",
        headers=api.write_headers(organization_id),
        json={"name": name, "email": email, "company": "Northstar Recruiting"},
    )
    data = _data(response, 201)
    assert response.headers["Location"] == f"/api/v1/customers/{data['id']}"
    return data, response.headers["ETag"]


def _create_product(
    api: HttpApi,
    organization_id: str,
    *,
    sku: str,
    name: str,
    unit_price_minor: int,
) -> tuple[dict[str, Any], str]:
    response = api.client.post(
        "/api/v1/products",
        headers=api.write_headers(organization_id),
        json={
            "sku": sku,
            "name": name,
            "category": "Recruiting Services",
            "unit_price_minor": unit_price_minor,
        },
    )
    data = _data(response, 201)
    assert response.headers["Location"] == f"/api/v1/products/{data['id']}"
    return data, response.headers["ETag"]


def _create_order(
    api: HttpApi,
    organization_id: str,
    *,
    customer_id: str,
    product_id: str,
    number: str,
    status: str,
    quantity: int,
    ordered_at: datetime,
) -> tuple[dict[str, Any], str, str, dict[str, Any]]:
    key = str(uuid.uuid4())
    payload = {
        "customer_id": customer_id,
        "order_number": number,
        "ordered_at": ordered_at.isoformat(),
        "status": status,
        "items": [{"product_id": product_id, "quantity": quantity}],
    }
    response = api.client.post(
        "/api/v1/orders",
        headers=api.write_headers(organization_id, idempotency_key=key),
        json=payload,
    )
    data = _data(response, 201)
    assert response.headers["Idempotency-Replayed"] == "false"
    assert response.headers["Location"] == f"/api/v1/orders/{data['id']}"
    return data, response.headers["ETag"], key, payload


def test_password_recovery_is_generic_single_use_and_revokes_sessions(
    http_api: HttpApi,
) -> None:
    api = http_api
    email = f"recovery-{uuid.uuid4().hex}@example.com"
    api.register(email=email, display_name="Recovery Owner")
    original_cookies = api.save_cookies()

    unknown = api.client.post(
        "/api/v1/auth/password-reset-requests",
        headers=api.csrf_headers(),
        json={"email": "unknown@example.com"},
    )
    assert unknown.status_code == 202, unknown.text
    assert unknown.json()["data"]["recovery_path"] is None

    requested = api.client.post(
        "/api/v1/auth/password-reset-requests",
        headers=api.csrf_headers(),
        json={"email": email},
    )
    assert requested.status_code == 202, requested.text
    assert requested.json()["data"]["message"] == unknown.json()["data"]["message"]
    recovery_path = requested.json()["data"]["recovery_path"]
    assert isinstance(recovery_path, str)
    token = recovery_path.partition("token=")[2]
    assert token and email not in recovery_path

    confirmed = api.client.post(
        "/api/v1/auth/password-resets",
        headers=api.csrf_headers(),
        json={"token": token, "password": UPDATED_PASSWORD},
    )
    assert confirmed.status_code == 204, confirmed.text

    replayed = api.client.post(
        "/api/v1/auth/password-resets",
        headers=api.csrf_headers(),
        json={"token": token, "password": PASSWORD},
    )
    _assert_problem(replayed, 400, "invalid_recovery_token")

    api.restore_cookies(original_cookies)
    revoked = api.client.get("/api/v1/auth/session")
    _assert_problem(revoked, 401, "session_expired")

    old_password = api.client.post(
        "/api/v1/auth/login",
        headers=api.csrf_headers(),
        json={"email": email, "password": PASSWORD},
    )
    _assert_problem(old_password, 401, "invalid_credentials")
    api.login(email=email, password=UPDATED_PASSWORD)


def _assert_two_page_collection(api: HttpApi, path: str, organization_id: str) -> None:
    first = api.client.get(
        path,
        headers=api.tenant_headers(organization_id),
        params={"page": 1, "page_size": 1},
    )
    second = api.client.get(
        path,
        headers=api.tenant_headers(organization_id),
        params={"page": 2, "page_size": 1},
    )
    first_data = _data(first, 200)
    second_data = _data(second, 200)
    first_pagination = first.json()["meta"]["pagination"]
    second_pagination = second.json()["meta"]["pagination"]
    assert first_pagination["page"] == 1
    assert first_pagination["page_size"] == 1
    assert first_pagination["total"] == 2
    assert first_pagination["total_pages"] == 2
    assert first_pagination["has_next"] is True
    assert first_pagination["has_previous"] is False
    assert second_pagination["page"] == 2
    assert second_pagination["has_next"] is False
    assert second_pagination["has_previous"] is True
    assert first_data[0]["id"] != second_data[0]["id"]


def test_recruiter_commerce_http_contract_is_tenant_safe_and_concurrent(
    http_api: HttpApi,
) -> None:
    api = http_api
    suffix = uuid.uuid4().hex[:12]
    api.register(
        email=f"recruiter-{suffix}@example.com",
        display_name="Morgan Recruiter",
    )
    organization_id = api.create_organization(name=f"Northstar Recruiting {suffix}")

    customer, customer_etag = _create_customer(
        api,
        organization_id,
        name="Acme Talent Group",
        email=f"acme-{suffix}@example.com",
    )
    _create_customer(
        api,
        organization_id,
        name="Beacon Hiring Partners",
        email=f"beacon-{suffix}@example.com",
    )
    _assert_two_page_collection(api, "/api/v1/customers", organization_id)

    fetched_customer = api.client.get(
        f"/api/v1/customers/{customer['id']}",
        headers=api.tenant_headers(organization_id),
    )
    assert _data(fetched_customer, 200)["name"] == "Acme Talent Group"
    assert fetched_customer.headers["ETag"] == customer_etag
    missing_customer_precondition = api.client.patch(
        f"/api/v1/customers/{customer['id']}",
        headers=api.write_headers(organization_id),
        json={"company": "Northstar Executive Search"},
    )
    _assert_problem(missing_customer_precondition, 428, "precondition_required")
    updated_customer = api.client.patch(
        f"/api/v1/customers/{customer['id']}",
        headers=api.write_headers(organization_id, if_match=customer_etag),
        json={"company": "Northstar Executive Search"},
    )
    assert _data(updated_customer, 200)["company"] == "Northstar Executive Search"
    assert updated_customer.headers["ETag"] != customer_etag
    stale_customer_update = api.client.patch(
        f"/api/v1/customers/{customer['id']}",
        headers=api.write_headers(organization_id, if_match=customer_etag),
        json={"company": "Stale Recruiting Update"},
    )
    _assert_problem(stale_customer_update, 412, "version_conflict")

    product, product_etag = _create_product(
        api,
        organization_id,
        sku=f"SEARCH-{suffix}",
        name="Executive Search Engagement",
        unit_price_minor=12_000,
    )
    _create_product(
        api,
        organization_id,
        sku=f"SCREEN-{suffix}",
        name="Candidate Screening Package",
        unit_price_minor=4_500,
    )
    _assert_two_page_collection(api, "/api/v1/products", organization_id)
    fetched_product = api.client.get(
        f"/api/v1/products/{product['id']}",
        headers=api.tenant_headers(organization_id),
    )
    assert _data(fetched_product, 200)["sku"] == f"SEARCH-{suffix.upper()}"
    assert fetched_product.headers["ETag"] == product_etag
    updated_product = api.client.patch(
        f"/api/v1/products/{product['id']}",
        headers=api.write_headers(organization_id, if_match=product_etag),
        json={"name": "Executive Search Retainer", "unit_price_minor": 12_500},
    )
    updated_product_data = _data(updated_product, 200)
    assert updated_product_data["name"] == "Executive Search Retainer"
    assert updated_product_data["unit_price_minor"] == 12_500

    now = datetime.now(UTC)
    first_order, first_order_etag, create_key, first_order_payload = _create_order(
        api,
        organization_id,
        customer_id=str(customer["id"]),
        product_id=str(product["id"]),
        number=f"PLACEMENT-{suffix}-1",
        status="pending",
        quantity=2,
        ordered_at=now - timedelta(minutes=2),
    )
    replayed_create = api.client.post(
        "/api/v1/orders",
        headers=api.write_headers(organization_id, idempotency_key=create_key),
        json=first_order_payload,
    )
    assert _data(replayed_create, 201) == first_order
    assert replayed_create.headers["Idempotency-Replayed"] == "true"

    fetched_order = api.client.get(
        f"/api/v1/orders/{first_order['id']}",
        headers=api.tenant_headers(organization_id),
    )
    fetched_order_data = _data(fetched_order, 200)
    assert fetched_order_data["items"][0]["product_id"] == product["id"]
    assert fetched_order_data["status_history"][0]["to_status"] == "pending"
    assert fetched_order.headers["ETag"] == first_order_etag
    missing_order_precondition = api.client.patch(
        f"/api/v1/orders/{first_order['id']}",
        headers=api.write_headers(organization_id),
        json={"status": "paid"},
    )
    _assert_problem(missing_order_precondition, 428, "precondition_required")
    paid_order = api.client.patch(
        f"/api/v1/orders/{first_order['id']}",
        headers=api.write_headers(organization_id, if_match=first_order_etag),
        json={"status": "paid"},
    )
    assert _data(paid_order, 200)["status"] == "paid"

    refund_key = str(uuid.uuid4())
    refund_payload = {"reason": "The retained search engagement was cancelled."}
    refunded = api.client.post(
        f"/api/v1/orders/{first_order['id']}/refund",
        headers=api.write_headers(organization_id, idempotency_key=refund_key),
        json=refund_payload,
    )
    refunded_data = _data(refunded, 200)
    assert refunded_data["status"] == "refunded"
    assert refunded.headers["Idempotency-Replayed"] == "false"
    replayed_refund = api.client.post(
        f"/api/v1/orders/{first_order['id']}/refund",
        headers=api.write_headers(organization_id, idempotency_key=refund_key),
        json=refund_payload,
    )
    assert _data(replayed_refund, 200) == refunded_data
    assert replayed_refund.headers["Idempotency-Replayed"] == "true"

    second_order, _second_etag, _second_key, _second_payload = _create_order(
        api,
        organization_id,
        customer_id=str(customer["id"]),
        product_id=str(product["id"]),
        number=f"PLACEMENT-{suffix}-2",
        status="paid",
        quantity=3,
        ordered_at=now - timedelta(minutes=1),
    )
    assert second_order["total_minor"] == 37_500
    _assert_two_page_collection(api, "/api/v1/orders", organization_id)

    overview = api.client.get(
        "/api/v1/analytics/overview",
        headers=api.tenant_headers(organization_id),
        params={"range": "30d", "compare": "previous_period"},
    )
    overview_data = _data(overview, 200)
    assert overview_data["data_availability"] == "available"
    assert overview_data["currency"] == "USD"
    assert overview_data["metrics"]["revenue_minor"]["value"] == 37_500
    assert overview_data["metrics"]["order_count"]["value"] == 1
    assert overview_data["recent_transactions"][0]["id"] == second_order["id"]

    product_metrics = api.client.get(
        f"/api/v1/products/{product['id']}/metrics",
        headers=api.tenant_headers(organization_id),
        params={"range": "30d"},
    )
    metrics_data = _data(product_metrics, 200)
    assert metrics_data["product_id"] == product["id"]
    assert metrics_data["current"] == {
        "units_sold": 3,
        "eligible_revenue_minor": 37_500,
        "average_selling_price_minor": 12_500,
        "order_count": 1,
    }
    assert sum(point["units_sold"] for point in metrics_data["trend"]) == 3

    other_organization_id = api.create_organization(name=f"Isolated Agency {suffix}")
    for resource_path in (
        f"/api/v1/customers/{customer['id']}",
        f"/api/v1/products/{product['id']}",
        f"/api/v1/orders/{second_order['id']}",
    ):
        cross_tenant = api.client.get(
            resource_path,
            headers=api.tenant_headers(other_organization_id),
        )
        _assert_problem(cross_tenant, 404, "resource_not_found")


def test_administration_http_contract_covers_sessions_permissions_billing_and_export(
    http_api: HttpApi,
) -> None:
    api = http_api
    suffix = uuid.uuid4().hex[:12]
    owner_email = f"admin-owner-{suffix}@example.com"
    member_email = f"admin-member-{suffix}@example.com"

    api.register(email=owner_email, display_name="Administration Owner")
    organization_id = api.create_organization(name=f"Administration Studio {suffix}")
    primary_cookies = api.save_cookies()
    api.client.cookies.clear()
    api.login(email=owner_email)
    secondary_cookies = api.save_cookies()
    api.restore_cookies(primary_cookies)

    profile = api.client.patch(
        "/api/v1/users/me",
        headers=api.write_headers(),
        json={
            "display_name": "Morgan Administrator",
            "locale": "en-GB",
            "time_zone": "Europe/London",
        },
    )
    profile_data = _data(profile, 200)
    assert profile_data["display_name"] == "Morgan Administrator"
    assert profile_data["locale"] == "en-GB"
    preferences = api.client.patch(
        "/api/v1/users/me/preferences",
        headers=api.write_headers(),
        json={"weekly_summary_email": False, "compact_tables": True},
    )
    preferences_data = _data(preferences, 200)
    assert preferences_data["weekly_summary_email"] is False
    assert preferences_data["compact_tables"] is True
    assert _data(api.client.get("/api/v1/users/me/preferences"), 200) == preferences_data

    current_organization = api.client.get(
        "/api/v1/organizations/current",
        headers=api.tenant_headers(organization_id),
    )
    current_data = _data(current_organization, 200)
    assert current_data["onboarding_state"] == "data"
    renamed_organization = f"Administration Intelligence {suffix}"
    updated_organization = api.client.patch(
        "/api/v1/organizations/current",
        headers=api.write_headers(
            organization_id,
            if_match=current_organization.headers["ETag"],
        ),
        json={
            "name": renamed_organization,
            "timezone": "America/New_York",
            "industry": "Recruiting",
        },
    )
    updated_organization_data = _data(updated_organization, 200)
    assert updated_organization_data["name"] == renamed_organization
    assert updated_organization_data["timezone"] == "America/New_York"
    assert updated_organization.headers["ETag"] != current_organization.headers["ETag"]
    onboarding = api.client.post(
        "/api/v1/organizations/current/onboarding/complete",
        headers=api.write_headers(organization_id),
        json={"empty_workspace": True},
    )
    assert _data(onboarding, 200)["onboarding_state"] == "complete"

    invitation_key = str(uuid.uuid4())
    invitation = api.client.post(
        "/api/v1/team/invitations",
        headers=api.write_headers(organization_id, idempotency_key=invitation_key),
        json={"email": member_email, "role": "member"},
    )
    invitation_data = _data(invitation, 201)
    assert invitation.headers["Idempotency-Replayed"] == "false"
    invitation_replay = api.client.post(
        "/api/v1/team/invitations",
        headers=api.write_headers(organization_id, idempotency_key=invitation_key),
        json={"email": member_email, "role": "member"},
    )
    assert _data(invitation_replay, 201) == invitation_data
    assert invitation_replay.headers["Idempotency-Replayed"] == "true"

    api.client.cookies.clear()
    api.register(email=member_email, display_name="Administration Member")
    accepted = api.client.post(
        f"/api/v1/team/invitations/accept/{invitation_data['acceptance_token']}",
        headers=api.write_headers(),
    )
    assert _data(accepted, 200)["organization_id"] == organization_id
    denied_invitation = api.client.post(
        "/api/v1/team/invitations",
        headers=api.write_headers(organization_id, idempotency_key=str(uuid.uuid4())),
        json={"email": f"blocked-{suffix}@example.com", "role": "member"},
    )
    _assert_problem(denied_invitation, 403, "permission_denied")

    api.restore_cookies(primary_cookies)
    export_key = str(uuid.uuid4())
    export_response = api.client.post(
        "/api/v1/organizations/current/data-exports",
        headers=api.write_headers(organization_id, idempotency_key=export_key),
        json={"format": "json"},
    )
    export_data = _data(export_response, 202)
    assert export_response.headers["Idempotency-Replayed"] == "false"
    download = api.client.get(
        export_data["download_url"],
        headers=api.tenant_headers(organization_id),
    )
    assert download.status_code == 200, download.text
    digest = hashlib.sha256(download.content).hexdigest()
    assert digest == export_data["content_sha256"]
    assert digest == download.headers["X-Content-SHA256"]
    export_document = download.json()
    assert export_document["organization"]["id"] == organization_id
    assert export_document["organization"]["name"] == renamed_organization
    assert "password_hash" not in download.text

    password_change = api.client.patch(
        "/api/v1/users/me/password",
        headers=api.write_headers(),
        json={"current_password": PASSWORD, "new_password": UPDATED_PASSWORD},
    )
    assert password_change.status_code == 204, password_change.text
    assert api.client.get("/api/v1/auth/session").status_code == 200
    api.restore_cookies(secondary_cookies)
    revoked_session = api.client.get("/api/v1/auth/session")
    _assert_problem(revoked_session, 401, "session_expired")

    api.client.cookies.clear()
    demo_session = api.client.post(
        "/api/v1/auth/demo-session",
        headers={**api.csrf_headers(), "Idempotency-Key": str(uuid.uuid4())},
        json={},
    )
    demo_data = _data(demo_session, 201)
    demo_organization_id = str(demo_data["organizations"][0]["id"])
    billing_key = str(uuid.uuid4())
    upgrade = api.client.post(
        "/api/v1/billing/upgrade-intents",
        headers=api.write_headers(demo_organization_id, idempotency_key=billing_key),
        json={"plan": "business"},
    )
    upgrade_data = _data(upgrade, 201)
    assert upgrade_data["mode"] == "demo"
    assert upgrade_data["status"] == "completed"
    assert upgrade_data["destination"] is None
    assert upgrade_data["message"] == (
        "The simulated plan change was applied. No payment was collected."
    )
    assert upgrade.headers["Idempotency-Replayed"] == "false"
    replayed_upgrade = api.client.post(
        "/api/v1/billing/upgrade-intents",
        headers=api.write_headers(demo_organization_id, idempotency_key=billing_key),
        json={"plan": "business"},
    )
    assert _data(replayed_upgrade, 201) == upgrade_data
    assert replayed_upgrade.headers["Idempotency-Replayed"] == "true"
    subscription = api.client.get(
        "/api/v1/billing/subscription",
        headers=api.tenant_headers(demo_organization_id),
    )
    subscription_data = _data(subscription, 200)
    assert subscription_data["plan"] == "business"
    assert subscription_data["provider"] == "demo"
    invoices = api.client.get(
        "/api/v1/billing/invoices",
        headers=api.tenant_headers(demo_organization_id),
    )
    assert invoices.status_code == 200, invoices.text
    assert invoices.json()["meta"]["pagination"]["total"] == 6
    assert all(invoice["hosted_url"] is None for invoice in invoices.json()["data"])
