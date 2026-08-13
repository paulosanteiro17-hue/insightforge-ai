from __future__ import annotations

import os
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from insightforge.core.config import Settings
from insightforge.core.time import utc_now
from insightforge.main import create_app

pytestmark = pytest.mark.postgres


def test_product_metrics_are_period_aware_and_tenant_scoped() -> None:
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
        csrf_signing_key="product-metrics-integration-signing-key-that-is-long-enough",
    )
    application = create_app(settings)
    suffix = uuid.uuid4().hex[:12]

    with TestClient(application) as client:
        csrf = client.get("/api/v1/auth/csrf-token").json()["data"]["csrf_token"]
        registered = client.post(
            "/api/v1/auth/register",
            headers={"Origin": "http://testserver", "X-CSRF-Token": csrf},
            json={
                "email": f"metrics-{suffix}@example.com",
                "password": "ProductMetricsPassword-2026",
                "display_name": "Metrics Owner",
            },
        )
        assert registered.status_code == 201, registered.text
        write_headers = {
            "Origin": "http://testserver",
            "X-CSRF-Token": client.cookies[settings.csrf_cookie_name],
        }
        organization = client.post(
            "/api/v1/organizations",
            headers=write_headers,
            json={
                "name": f"Metrics Studio {suffix}",
                "reporting_currency": "USD",
                "timezone": "UTC",
            },
        )
        assert organization.status_code == 201, organization.text
        organization_id = organization.json()["data"]["id"]
        headers = {**write_headers, "X-Organization-ID": organization_id}
        customer = client.post(
            "/api/v1/customers",
            headers=headers,
            json={
                "name": "Metrics Customer",
                "email": f"customer-{suffix}@example.com",
            },
        )
        assert customer.status_code == 201, customer.text
        product = client.post(
            "/api/v1/products",
            headers=headers,
            json={
                "sku": f"METRICS-{suffix}",
                "name": "Performance Package",
                "category": "Services",
                "unit_price_minor": 10_000,
            },
        )
        assert product.status_code == 201, product.text
        product_id = product.json()["data"]["id"]

        now = utc_now()

        def create_order(*, age_days: int, quantity: int, initial_status: str) -> object:
            return client.post(
                "/api/v1/orders",
                headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
                json={
                    "customer_id": customer.json()["data"]["id"],
                    "order_number": f"PM-{uuid.uuid4().hex[:12]}",
                    "ordered_at": (now - timedelta(days=age_days)).isoformat(),
                    "status": initial_status,
                    "items": [{"product_id": product_id, "quantity": quantity}],
                },
            )

        current_order = create_order(age_days=5, quantity=2, initial_status="paid")
        assert current_order.status_code == 201, current_order.text
        previous_order = create_order(age_days=35, quantity=1, initial_status="paid")
        assert previous_order.status_code == 201, previous_order.text
        cancelled_order = create_order(age_days=4, quantity=5, initial_status="pending")
        assert cancelled_order.status_code == 201, cancelled_order.text
        cancelled = client.post(
            f"/api/v1/orders/{cancelled_order.json()['data']['id']}/cancel",
            headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
            json={"reason": "Cancelled for product metrics verification."},
        )
        assert cancelled.status_code == 200, cancelled.text

        metrics = client.get(
            f"/api/v1/products/{product_id}/metrics",
            headers=headers,
            params={"range": "30d"},
        )
        assert metrics.status_code == 200, metrics.text
        data = metrics.json()["data"]
        assert data["product_id"] == product_id
        assert data["currency"] == "USD"
        assert data["current"] == {
            "units_sold": 2,
            "eligible_revenue_minor": 20_000,
            "average_selling_price_minor": 10_000,
            "order_count": 1,
        }
        assert data["previous"] == {
            "units_sold": 1,
            "eligible_revenue_minor": 10_000,
            "average_selling_price_minor": 10_000,
            "order_count": 1,
        }
        assert data["units_change_percent"] == 100.0
        assert data["revenue_change_percent"] == 100.0
        assert sum(point["units_sold"] for point in data["trend"]) == 2

        invalid_range = client.get(
            f"/api/v1/products/{product_id}/metrics",
            headers=headers,
            params={"range": "all_time"},
        )
        assert invalid_range.status_code == 422

        other_organization = client.post(
            "/api/v1/organizations",
            headers=write_headers,
            json={
                "name": f"Other Metrics Studio {suffix}",
                "reporting_currency": "USD",
                "timezone": "UTC",
            },
        )
        assert other_organization.status_code == 201
        cross_tenant = client.get(
            f"/api/v1/products/{product_id}/metrics",
            headers={
                **headers,
                "X-Organization-ID": other_organization.json()["data"]["id"],
            },
        )
        assert cross_tenant.status_code == 404
