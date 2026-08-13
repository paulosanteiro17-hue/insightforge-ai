from __future__ import annotations

import hashlib
import io
import uuid
from pathlib import Path

import pytest
from fastapi import UploadFile

from insightforge.core.problems import AppError
from insightforge.storage import LocalPrivateStorage


def _retained_files(path: Path) -> list[Path]:
    return list(path.rglob("*.*"))


@pytest.mark.asyncio
async def test_private_storage_uses_server_generated_tenant_path(tmp_path: Path) -> None:
    payload = b"external_id,name\nCUS-1,Avery\n"
    storage = LocalPrivateStorage(tmp_path)
    organization_id = uuid.uuid4()
    import_id = uuid.uuid4()
    upload = UploadFile(filename="../../private/secret.csv", file=io.BytesIO(payload))

    stored = await storage.store_upload(
        organization_id=organization_id,
        import_id=import_id,
        upload=upload,
        expected_sha256=hashlib.sha256(payload).hexdigest(),
        max_bytes=1_024,
    )

    assert stored.original_filename == "secret.csv"
    assert stored.storage_key == f"imports/{organization_id.hex}/{import_id.hex}.csv"
    assert storage.read_bytes(stored.storage_key, max_bytes=1_024) == payload
    assert "secret" not in stored.storage_key


@pytest.mark.asyncio
async def test_private_storage_removes_partial_files_on_digest_mismatch(tmp_path: Path) -> None:
    storage = LocalPrivateStorage(tmp_path)
    upload = UploadFile(filename="ignored.html", file=io.BytesIO(b"submitted bytes"))

    with pytest.raises(AppError) as caught:
        await storage.store_upload(
            organization_id=uuid.uuid4(),
            import_id=uuid.uuid4(),
            upload=upload,
            expected_sha256="0" * 64,
            max_bytes=1_024,
        )

    assert caught.value.code == "content_digest_mismatch"
    assert _retained_files(tmp_path) == []


@pytest.mark.asyncio
async def test_private_storage_enforces_stream_limit_and_blocks_traversal(tmp_path: Path) -> None:
    storage = LocalPrivateStorage(tmp_path)
    upload = UploadFile(filename="large.csv", file=io.BytesIO(b"12345"))

    with pytest.raises(AppError) as too_large:
        await storage.store_upload(
            organization_id=uuid.uuid4(),
            import_id=uuid.uuid4(),
            upload=upload,
            expected_sha256=hashlib.sha256(b"12345").hexdigest(),
            max_bytes=4,
        )
    with pytest.raises(AppError) as traversal:
        storage.read_bytes("../../outside.csv", max_bytes=10)

    assert too_large.value.status == 413
    assert traversal.value.code == "invalid_storage_key"
