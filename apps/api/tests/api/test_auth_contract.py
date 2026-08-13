from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from insightforge.api.dependencies import get_auth_service
from insightforge.api.rate_limits import RequestRateLimits
from insightforge.core.problems import AppError


class RejectingAuthService:
    async def login(self, *, email: str, password: str) -> None:
        del email, password
        raise AppError(
            status=401,
            code="invalid_credentials",
            title="Authentication failed",
            detail="Invalid email or password.",
        )


def test_csrf_endpoint_issues_readable_signed_cookie_without_database_access(application) -> None:
    with TestClient(application) as client:
        response = client.get("/api/v1/auth/csrf-token")

    assert response.status_code == 200
    token = response.json()["data"]["csrf_token"]
    assert response.cookies["insightforge_csrf_local"] == token
    assert response.headers["Cache-Control"] == "no-store"
    csrf_cookie_header = next(
        value
        for value in response.headers.get_list("set-cookie")
        if value.startswith("insightforge_csrf_local=")
    )
    assert "HttpOnly" not in csrf_cookie_header


def test_csrf_endpoint_reuses_a_still_valid_pre_auth_token(application) -> None:
    with TestClient(application) as client:
        first = client.get("/api/v1/auth/csrf-token")
        second = client.get("/api/v1/auth/csrf-token")

    assert first.json()["data"]["csrf_token"] == second.json()["data"]["csrf_token"]


def test_demo_session_requires_uuid_v4_idempotency_key(application) -> None:
    with TestClient(application) as client:
        csrf = client.get("/api/v1/auth/csrf-token").json()["data"]["csrf_token"]
        response = client.post(
            "/api/v1/auth/demo-session",
            headers={
                "Origin": "http://testserver",
                "X-CSRF-Token": csrf,
                "Idempotency-Key": "predictable-demo-key",
            },
            json={},
        )

    assert response.status_code == 400
    assert response.json()["code"] == "idempotency_key_required"


def test_unsafe_auth_request_rejects_mismatched_csrf_as_problem_details(application) -> None:
    with TestClient(application) as client:
        client.get("/api/v1/auth/csrf-token")
        response = client.post(
            "/api/v1/auth/login",
            headers={"Origin": "http://testserver", "X-CSRF-Token": "wrong-token"},
            json={"email": "owner@example.com", "password": "incorrect-password"},
        )

    assert response.status_code == 403
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "csrf_failed"
    assert response.json()["detail"] == "Refresh the page and try again."


def test_login_account_rate_limit_stops_repeated_password_hash_work(
    application,
    test_settings,
) -> None:
    limited_settings = test_settings.model_copy(update={"login_account_limit": 1})
    application.state.request_rate_limits = RequestRateLimits(limited_settings)
    application.dependency_overrides[get_auth_service] = RejectingAuthService
    try:
        with TestClient(application) as client:
            csrf = client.get("/api/v1/auth/csrf-token").json()["data"]["csrf_token"]
            headers = {
                "Origin": "http://testserver",
                "X-CSRF-Token": csrf,
            }
            payload = {
                "email": "owner@example.com",
                "password": "incorrect-password",
            }
            first = client.post("/api/v1/auth/login", headers=headers, json=payload)
            limited = client.post("/api/v1/auth/login", headers=headers, json=payload)
    finally:
        application.dependency_overrides.pop(get_auth_service, None)

    assert first.status_code == 401
    assert limited.status_code == 429
    assert limited.json()["code"] == "rate_limit_exceeded"
    assert limited.headers["Retry-After"] == "300"


def test_protected_route_uses_rfc_9457_and_propagates_request_id(application) -> None:
    request_id = str(uuid.uuid4())
    with TestClient(application) as client:
        response = client.get(
            "/api/v1/organizations",
            headers={"X-Request-ID": request_id},
        )

    problem = response.json()
    assert response.status_code == 401
    assert response.headers["X-Request-ID"] == request_id
    assert problem["request_id"] == request_id
    assert problem["code"] == "authentication_required"
    assert problem["type"].endswith("/authentication-required")


def test_extra_request_fields_are_normalized_to_validation_problem(application) -> None:
    with TestClient(application) as client:
        csrf = client.get("/api/v1/auth/csrf-token").json()["data"]["csrf_token"]
        response = client.post(
            "/api/v1/auth/demo-session",
            headers={
                "Origin": "http://testserver",
                "X-CSRF-Token": csrf,
                "Idempotency-Key": str(uuid.uuid4()),
            },
            json={"unexpected": "field"},
        )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert response.json()["errors"][0]["field"] == "unexpected"
