from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update

from insightforge.core.config import Settings
from insightforge.db.session import get_session_factory
from insightforge.main import create_app
from insightforge.models import OrganizationMember
from insightforge.worker.runner import run_worker_once

pytestmark = pytest.mark.postgres


def _settings(database_url: str, private_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        environment="testing",
        database_url=database_url,
        private_storage_path=private_path,
        allowed_origins=["http://testserver"],
        csrf_allowed_origins=["http://testserver"],
        allowed_hosts=["testserver"],
        csrf_signing_key="import-integration-csrf-signing-key-that-is-long-enough",
        demo_browser_limit=20,
        demo_global_limit=100,
    )


def _demo_client(client: TestClient, settings: Settings) -> tuple[str, dict[str, str]]:
    csrf = client.get("/api/v1/auth/csrf-token").json()["data"]["csrf_token"]
    demo = client.post(
        "/api/v1/auth/demo-session",
        headers={
            "Origin": "http://testserver",
            "X-CSRF-Token": csrf,
            "Idempotency-Key": str(uuid.uuid4()),
        },
        json={},
    )
    assert demo.status_code == 201, demo.text
    organization_id = demo.json()["data"]["organizations"][0]["id"]
    headers = {
        "Origin": "http://testserver",
        "X-CSRF-Token": client.cookies[settings.csrf_cookie_name],
        "X-Organization-ID": organization_id,
    }
    return organization_id, headers


def _run_worker(client: TestClient, settings: Settings) -> None:
    assert client.portal is not None
    assert client.portal.call(run_worker_once, settings)


def _upload_and_validate(
    client: TestClient,
    settings: Settings,
    headers: dict[str, str],
    *,
    kind: str,
    payload: bytes,
) -> tuple[str, str]:
    digest = hashlib.sha256(payload).hexdigest()
    response = client.post(
        "/api/v1/imports",
        headers={
            **headers,
            "Idempotency-Key": str(uuid.uuid4()),
            "X-Content-SHA256": digest,
        },
        data={"kind": kind},
        files={"file": (f"{kind}.csv", payload, "text/csv")},
    )
    assert response.status_code == 202, response.text
    import_id = response.json()["data"]["id"]
    _run_worker(client, settings)
    detail = client.get(f"/api/v1/imports/{import_id}", headers=headers)
    assert detail.json()["data"]["status"] == "ready", detail.text
    return import_id, digest


def _commit_and_apply(
    client: TestClient,
    settings: Settings,
    headers: dict[str, str],
    *,
    import_id: str,
    digest: str,
) -> dict:
    queued = client.post(
        f"/api/v1/imports/{import_id}/commit",
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
        json={"content_sha256": digest},
    )
    assert queued.status_code == 202, queued.text
    _run_worker(client, settings)
    detail = client.get(f"/api/v1/imports/{import_id}", headers=headers)
    return detail.json()["data"]


async def _demote_import_owner(settings: Settings, organization_id: str) -> None:
    async with get_session_factory(settings.database_url)() as db:
        await db.execute(
            update(OrganizationMember)
            .where(OrganizationMember.organization_id == uuid.UUID(organization_id))
            .values(role="member")
        )
        await db.commit()


def test_upload_validate_commit_replay_and_tenant_isolation(
    tmp_path: Path,
) -> None:
    database_url = os.environ.get("INSIGHTFORGE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("INSIGHTFORGE_TEST_DATABASE_URL is not configured.")
    settings = _settings(database_url, tmp_path / "private")
    application = create_app(settings)
    suffix = uuid.uuid4().hex[:12]
    payload = (
        "external_id,name,email,company,status,acquired_at\n"
        f"IMP-{suffix},Imported Customer,import-{suffix}@example.com,Import Studio,"
        "active,2026-08-01T10:00:00Z\n"
    ).encode()
    digest = hashlib.sha256(payload).hexdigest()
    upload_key = str(uuid.uuid4())

    with TestClient(application) as client:
        organization_id, headers = _demo_client(client, settings)
        uploaded = client.post(
            "/api/v1/imports",
            headers={
                **headers,
                "Idempotency-Key": upload_key,
                "X-Content-SHA256": digest,
            },
            data={"kind": "customers"},
            files={"file": ("../../untrusted.html", payload, "text/html")},
        )
        assert uploaded.status_code == 202, uploaded.text
        assert uploaded.json()["data"]["status"] == "validating"
        assert uploaded.json()["data"]["original_filename"] == "untrusted.html"
        import_id = uploaded.json()["data"]["id"]
        assert not (tmp_path / "untrusted.html").exists()

        _run_worker(client, settings)
        ready = client.get(f"/api/v1/imports/{import_id}", headers=headers)
        assert ready.status_code == 200, ready.text
        assert ready.json()["data"]["status"] == "ready"
        preview = client.get(f"/api/v1/imports/{import_id}/preview", headers=headers)
        assert preview.json()["data"]["rows"][0]["name"] == "Imported Customer"

        upload_replay = client.post(
            "/api/v1/imports",
            headers={
                **headers,
                "Idempotency-Key": upload_key,
                "X-Content-SHA256": digest,
            },
            data={"kind": "customers"},
            files={"file": ("different-name.csv", payload, "application/octet-stream")},
        )
        assert upload_replay.headers["Idempotency-Replayed"] == "true"
        assert upload_replay.json() == uploaded.json()

        commit_key = str(uuid.uuid4())
        committed = client.post(
            f"/api/v1/imports/{import_id}/commit",
            headers={**headers, "Idempotency-Key": commit_key},
            json={"content_sha256": digest, "duplicate_policy": "create_only"},
        )
        assert committed.status_code == 202, committed.text
        assert committed.json()["data"]["status"] == "importing"
        _run_worker(client, settings)

        completed = client.get(f"/api/v1/imports/{import_id}", headers=headers)
        assert completed.json()["data"]["status"] == "completed"
        assert completed.json()["data"]["imported_rows"] == 1
        customers = client.get(
            "/api/v1/customers",
            headers=headers,
            params={"q": f"import-{suffix}"},
        )
        assert customers.json()["meta"]["pagination"]["total"] == 1

        commit_replay = client.post(
            f"/api/v1/imports/{import_id}/commit",
            headers={**headers, "Idempotency-Key": commit_key},
            json={"content_sha256": digest, "duplicate_policy": "create_only"},
        )
        assert commit_replay.headers["Idempotency-Replayed"] == "true"
        assert commit_replay.json() == committed.json()

        assert client.portal is not None
        client.portal.call(_demote_import_owner, settings, organization_id)
        member_denied = client.get("/api/v1/imports", headers=headers)
        assert member_denied.status_code == 403
        assert member_denied.json()["code"] == "permission_denied"

        _second_org, second_headers = _demo_client(client, settings)
        cross_tenant = client.get(
            f"/api/v1/imports/{import_id}",
            headers={**second_headers, "X-Organization-ID": organization_id},
        )
        assert cross_tenant.status_code == 404


def test_commit_revalidates_references_and_rolls_back_cleanly(tmp_path: Path) -> None:
    database_url = os.environ.get("INSIGHTFORGE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("INSIGHTFORGE_TEST_DATABASE_URL is not configured.")
    settings = _settings(database_url, tmp_path / "private")
    application = create_app(settings)
    suffix = uuid.uuid4().hex[:12]
    payload = (
        "external_id,order_number,customer_external_id,status,ordered_at,currency,"
        "product_sku,quantity,unit_price,discount,tax\n"
        f"IMP-ORD-{suffix},IF-{suffix},MISSING-CUSTOMER,paid,2026-08-02T12:00:00Z,"
        "USD,MISSING-SKU,1,10.00,0.00,0.00\n"
    ).encode()
    digest = hashlib.sha256(payload).hexdigest()

    with TestClient(application) as client:
        _organization_id, headers = _demo_client(client, settings)
        uploaded = client.post(
            "/api/v1/imports",
            headers={
                **headers,
                "Idempotency-Key": str(uuid.uuid4()),
                "X-Content-SHA256": digest,
            },
            data={"kind": "orders"},
            files={"file": ("orders.csv", payload, "text/csv")},
        )
        import_id = uploaded.json()["data"]["id"]
        _run_worker(client, settings)
        ready = client.get(f"/api/v1/imports/{import_id}", headers=headers)
        assert ready.json()["data"]["status"] == "ready"

        queued = client.post(
            f"/api/v1/imports/{import_id}/commit",
            headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
            json={"content_sha256": digest},
        )
        assert queued.status_code == 202
        _run_worker(client, settings)

        failed = client.get(f"/api/v1/imports/{import_id}", headers=headers)
        assert failed.json()["data"]["status"] == "import_failed"
        errors = client.get(f"/api/v1/imports/{import_id}/errors", headers=headers)
        assert {item["code"] for item in errors.json()["data"]} == {"unknown_reference"}
        orders = client.get(
            "/api/v1/orders",
            headers=headers,
            params={"q": f"IF-{suffix}"},
        )
        assert orders.json()["meta"]["pagination"]["total"] == 0


def test_product_and_order_imports_preserve_prices_and_totals(tmp_path: Path) -> None:
    database_url = os.environ.get("INSIGHTFORGE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("INSIGHTFORGE_TEST_DATABASE_URL is not configured.")
    settings = _settings(database_url, tmp_path / "private")
    application = create_app(settings)
    suffix = uuid.uuid4().hex[:12]
    sku = f"IMP-SKU-{suffix}"
    product_payload = (
        "external_id,sku,name,category,unit_price,status\n"
        f"IMP-PRD-{suffix},{sku},Imported Plan,Software,123.45,active\n"
    ).encode()

    with TestClient(application) as client:
        _organization_id, headers = _demo_client(client, settings)
        product_import_id, product_digest = _upload_and_validate(
            client,
            settings,
            headers,
            kind="products",
            payload=product_payload,
        )
        product_result = _commit_and_apply(
            client,
            settings,
            headers,
            import_id=product_import_id,
            digest=product_digest,
        )
        assert product_result["status"] == "completed"

        order_number = f"IF-IMP-{suffix}"
        order_payload = (
            "external_id,order_number,customer_external_id,status,ordered_at,currency,"
            "product_sku,quantity,unit_price,discount,tax\n"
            f"IMP-ORD-{suffix},{order_number},DEMO-CUSTOMER-001,paid,"
            f"2026-08-03T12:00:00Z,USD,{sku},2,100.00,5.00,8.00\n"
        ).encode()
        order_import_id, order_digest = _upload_and_validate(
            client,
            settings,
            headers,
            kind="orders",
            payload=order_payload,
        )
        order_result = _commit_and_apply(
            client,
            settings,
            headers,
            import_id=order_import_id,
            digest=order_digest,
        )
        assert order_result["status"] == "completed"
        orders = client.get(
            "/api/v1/orders",
            headers=headers,
            params={"q": order_number},
        )
        assert orders.json()["meta"]["pagination"]["total"] == 1
        assert orders.json()["data"][0]["subtotal_minor"] == 20_000
        assert orders.json()["data"][0]["discount_minor"] == 500
        assert orders.json()["data"][0]["tax_minor"] == 800
        assert orders.json()["data"][0]["total_minor"] == 20_300

        duplicate_import_id, duplicate_digest = _upload_and_validate(
            client,
            settings,
            headers,
            kind="products",
            payload=product_payload,
        )
        duplicate_result = _commit_and_apply(
            client,
            settings,
            headers,
            import_id=duplicate_import_id,
            digest=duplicate_digest,
        )
        assert duplicate_result["status"] == "import_failed"


def test_file_level_validation_error_is_persisted_without_raw_bytes(tmp_path: Path) -> None:
    database_url = os.environ.get("INSIGHTFORGE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("INSIGHTFORGE_TEST_DATABASE_URL is not configured.")
    settings = _settings(database_url, tmp_path / "private")
    application = create_app(settings)
    payload = (
        b"external_id,name,email,company,status,acquired_at\n"
        b"CUS-1,Invalid \xff,email@example.com,Studio,active,2026-08-01T10:00:00Z\n"
    )
    digest = hashlib.sha256(payload).hexdigest()

    with TestClient(application) as client:
        _organization_id, headers = _demo_client(client, settings)
        uploaded = client.post(
            "/api/v1/imports",
            headers={
                **headers,
                "Idempotency-Key": str(uuid.uuid4()),
                "X-Content-SHA256": digest,
            },
            data={"kind": "customers"},
            files={"file": ("customers.csv", payload, "text/plain")},
        )
        assert uploaded.status_code == 202
        import_id = uploaded.json()["data"]["id"]
        _run_worker(client, settings)

        failed = client.get(f"/api/v1/imports/{import_id}", headers=headers)
        assert failed.json()["data"]["status"] == "validation_failed"
        errors = client.get(f"/api/v1/imports/{import_id}/errors", headers=headers)
        assert errors.json()["data"][0]["code"] == "invalid_utf8"
        assert "Invalid" not in errors.text
