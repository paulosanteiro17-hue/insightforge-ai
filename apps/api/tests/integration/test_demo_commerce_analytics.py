from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from insightforge.core.config import Settings
from insightforge.main import create_app

pytestmark = pytest.mark.postgres


def test_demo_seed_drives_tenant_commerce_and_analytics() -> None:
    database_url = os.environ.get("INSIGHTFORGE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("INSIGHTFORGE_TEST_DATABASE_URL is not configured.")
    settings = Settings(
        _env_file=None,
        environment="testing",
        database_url=database_url,
        allowed_origins=["http://testserver"],
        csrf_allowed_origins=["http://testserver"],
        allowed_hosts=["testserver"],
        csrf_signing_key="integration-test-csrf-signing-key-that-is-long-enough",
    )
    application = create_app(settings)
    idempotency_key = str(uuid.uuid4())

    with TestClient(application) as client:
        csrf = client.get("/api/v1/auth/csrf-token").json()["data"]["csrf_token"]
        demo = client.post(
            "/api/v1/auth/demo-session",
            headers={
                "Origin": "http://testserver",
                "X-CSRF-Token": csrf,
                "Idempotency-Key": idempotency_key,
            },
            json={},
        )
        assert demo.status_code == 201, demo.text
        organization_id = demo.json()["data"]["organizations"][0]["id"]
        tenant_headers = {"X-Organization-ID": organization_id}
        session_csrf = client.cookies[settings.csrf_cookie_name]
        repeated_csrf = client.get("/api/v1/auth/csrf-token")
        assert repeated_csrf.json()["data"]["csrf_token"] == session_csrf

        customers = client.get("/api/v1/customers", headers=tenant_headers)
        assert customers.status_code == 200, customers.text
        assert customers.json()["meta"]["pagination"]["total"] == 60

        overview = client.get("/api/v1/analytics/overview", headers=tenant_headers)
        assert overview.status_code == 200, overview.text
        assert overview.json()["data"]["data_availability"] == "available"
        assert overview.json()["data"]["currency"] == "USD"

        write_headers = {
            **tenant_headers,
            "Origin": "http://testserver",
            "X-CSRF-Token": client.cookies[settings.csrf_cookie_name],
        }
        customer = client.post(
            "/api/v1/customers",
            headers=write_headers,
            json={
                "name": "Integration Customer",
                "email": f"integration-{uuid.uuid4().hex}@example.com",
                "company": "Integration Studio",
            },
        )
        assert customer.status_code == 201, customer.text
        product = client.post(
            "/api/v1/products",
            headers=write_headers,
            json={
                "sku": f"INTEGRATION-{uuid.uuid4().hex[:10]}",
                "name": "Integration Product",
                "category": "Software",
                "unit_price_minor": 9_900,
            },
        )
        assert product.status_code == 201, product.text
        order_key = str(uuid.uuid4())
        order_payload = {
            "customer_id": customer.json()["data"]["id"],
            "order_number": f"INT-{uuid.uuid4().hex[:12]}",
            "items": [
                {
                    "product_id": product.json()["data"]["id"],
                    "quantity": 2,
                    "discount_minor": 500,
                }
            ],
        }
        created_order = client.post(
            "/api/v1/orders",
            headers={**write_headers, "Idempotency-Key": order_key},
            json=order_payload,
        )
        assert created_order.status_code == 201, created_order.text
        assert created_order.json()["data"]["total_minor"] == 19_300
        assert created_order.json()["data"]["status"] == "pending"

        advanced_order = client.patch(
            f"/api/v1/orders/{created_order.json()['data']['id']}",
            headers={**write_headers, "If-Match": created_order.headers["ETag"]},
            json={"status": "paid"},
        )
        assert advanced_order.status_code == 200, advanced_order.text
        assert advanced_order.json()["data"]["status"] == "paid"

        original_replay = client.post(
            "/api/v1/orders",
            headers={**write_headers, "Idempotency-Key": order_key},
            json=order_payload,
        )
        assert original_replay.status_code == 201, original_replay.text
        assert original_replay.headers["Idempotency-Replayed"] == "true"
        assert original_replay.json() == created_order.json()

        replay = client.post(
            "/api/v1/auth/demo-session",
            headers={
                "Origin": "http://testserver",
                "X-CSRF-Token": client.cookies[settings.csrf_cookie_name],
                "Idempotency-Key": idempotency_key,
            },
            json={},
        )
        assert replay.status_code == 201, replay.text
        assert replay.headers["Idempotency-Replayed"] == "true"
        assert replay.json()["data"]["organizations"][0]["id"] == organization_id
