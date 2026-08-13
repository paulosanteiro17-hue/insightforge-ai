from __future__ import annotations

from fastapi.testclient import TestClient


def test_openapi_exposes_foundation_contract_and_session_security(application) -> None:
    with TestClient(application) as client:
        response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    document = response.json()
    paths = document["paths"]
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/logout" in paths
    assert "/api/v1/auth/demo-session" in paths
    assert "/api/v1/auth/session" in paths
    assert "/api/v1/organizations" in paths
    assert "/api/v1/organizations/current" in paths
    assert "/api/v1/customers" in paths
    assert "/api/v1/customers/{customer_id}/orders" in paths
    assert "/api/v1/products" in paths
    assert "/api/v1/orders" in paths
    assert "/api/v1/orders/{order_id}/refund" in paths
    assert "/api/v1/analytics/overview" in paths
    assert "/api/v1/analytics/revenue" in paths
    assert "/api/v1/analytics/customers" in paths
    assert "/api/v1/analytics/products" in paths
    assert "/api/v1/analytics/orders" in paths
    assert "/api/v1/analytics/filter-options" in paths
    assert "/api/v1/insights" in paths
    assert "/api/v1/insights/generation-jobs" in paths
    assert "/api/v1/weekly-summary/current" in paths
    assert "/api/v1/ask-data/capabilities" in paths
    assert "/api/v1/ask-data/answers" in paths
    assert "/api/v1/ask-data/history" in paths
    assert "/api/v1/reports" in paths
    assert "/api/v1/reports/templates" in paths
    assert "/api/v1/reports/{report_id}/download" in paths
    assert "/api/v1/imports" in paths
    assert "/api/v1/imports/{import_id}" in paths
    assert "/api/v1/imports/{import_id}/preview" in paths
    assert "/api/v1/imports/{import_id}/errors" in paths
    assert "/api/v1/imports/{import_id}/commit" in paths
    assert "/api/v1/imports/{import_id}/cancel" in paths
    assert "/api/v1/imports/templates/{kind}" in paths
    schemes = document["components"]["securitySchemes"]
    assert any(
        scheme.get("in") == "cookie" and scheme.get("name") == "__Host-insightforge_session"
        for scheme in schemes.values()
    )
