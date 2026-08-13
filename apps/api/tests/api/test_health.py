from __future__ import annotations

from fastapi.testclient import TestClient

from insightforge.api.health import ReadinessChecker, get_readiness_checker


class HealthyReadinessChecker(ReadinessChecker):
    async def check(self, settings):
        return {"database": "ok", "migration": "ok"}


class UnhealthyReadinessChecker(ReadinessChecker):
    async def check(self, settings):
        return {"database": "unavailable", "migration": "unknown"}


def test_liveness_and_version_disclose_only_safe_metadata(application) -> None:
    with TestClient(application) as client:
        live = client.get("/health/live")
        version = client.get("/health/version")

    assert live.status_code == 200
    assert live.json() == {"status": "ok"}
    assert version.json() == {
        "version": "test-version",
        "commit": "test-commit",
        "deployed_at": "2026-08-10T00:00:00Z",
    }
    assert "database_url" not in version.text


def test_readiness_reports_migration_and_database_state(application) -> None:
    application.dependency_overrides[get_readiness_checker] = HealthyReadinessChecker
    with TestClient(application) as client:
        healthy = client.get("/health/ready")
    assert healthy.status_code == 200
    assert healthy.json()["status"] == "ok"

    application.dependency_overrides[get_readiness_checker] = UnhealthyReadinessChecker
    with TestClient(application) as client:
        unhealthy = client.get("/health/ready")
    assert unhealthy.status_code == 503
    assert unhealthy.json() == {
        "status": "unavailable",
        "checks": {"database": "unavailable", "migration": "unknown"},
    }
