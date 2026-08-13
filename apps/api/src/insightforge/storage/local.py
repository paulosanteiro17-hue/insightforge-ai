from __future__ import annotations

import hashlib
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from insightforge.core.problems import AppError

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class StoredUpload:
    storage_key: str
    content_sha256: str
    size_bytes: int
    original_filename: str


def validate_content_sha256(value: str | None) -> str:
    normalized = value.strip().casefold() if value else ""
    if _SHA256_PATTERN.fullmatch(normalized) is None:
        raise AppError(
            status=400,
            code="content_digest_required",
            title="Content digest required",
            detail="Provide the lowercase SHA-256 digest in X-Content-SHA256.",
        )
    return normalized


def safe_display_filename(value: str | None) -> str:
    candidate = (value or "upload.csv").replace("\\", "/").split("/")[-1]
    candidate = "".join(
        character
        for character in candidate
        if ord(character) >= 32 and not 127 <= ord(character) <= 159
    )
    candidate = candidate.strip()[:255]
    return candidate if candidate not in {"", ".", ".."} else "upload.csv"


class LocalPrivateStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _resolve(self, storage_key: str) -> Path:
        candidate = (self.root / storage_key).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise AppError(
                status=500,
                code="invalid_storage_key",
                title="Stored file is unavailable",
                detail="The retained import file could not be resolved safely.",
            ) from exc
        return candidate

    async def store_upload(
        self,
        *,
        organization_id: uuid.UUID,
        import_id: uuid.UUID,
        upload: UploadFile,
        expected_sha256: str,
        max_bytes: int,
    ) -> StoredUpload:
        directory = self._resolve(f"imports/{organization_id.hex}")
        directory.mkdir(parents=True, exist_ok=True)
        final_path = self._resolve(f"imports/{organization_id.hex}/{import_id.hex}.csv")
        temporary_path = self._resolve(
            f"imports/{organization_id.hex}/{import_id.hex}.{uuid.uuid4().hex}.uploading"
        )
        digest = hashlib.sha256()
        size_bytes = 0
        try:
            with temporary_path.open("xb") as destination:
                while True:
                    chunk = await upload.read(64 * 1024)
                    if not chunk:
                        break
                    size_bytes += len(chunk)
                    if size_bytes > max_bytes:
                        raise AppError(
                            status=413,
                            code="file_too_large",
                            title="File is too large",
                            detail="The CSV file exceeds the configured upload limit.",
                        )
                    digest.update(chunk)
                    destination.write(chunk)
                destination.flush()
                os.fsync(destination.fileno())
            actual_sha256 = digest.hexdigest()
            if actual_sha256 != expected_sha256:
                raise AppError(
                    status=422,
                    code="content_digest_mismatch",
                    title="Content digest does not match",
                    detail="The uploaded bytes do not match X-Content-SHA256.",
                )
            os.replace(temporary_path, final_path)
            return StoredUpload(
                storage_key=final_path.relative_to(self.root).as_posix(),
                content_sha256=actual_sha256,
                size_bytes=size_bytes,
                original_filename=safe_display_filename(upload.filename),
            )
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

    def store_bytes(self, storage_key: str, payload: bytes, *, max_bytes: int) -> StoredUpload:
        if len(payload) > max_bytes:
            raise AppError(
                status=413,
                code="export_too_large",
                title="Export is too large",
                detail="Narrow the data set before requesting another export.",
            )
        final_path = self._resolve(storage_key)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self._resolve(f"{storage_key}.{uuid.uuid4().hex}.exporting")
        try:
            with temporary_path.open("xb") as destination:
                destination.write(payload)
                destination.flush()
                os.fsync(destination.fileno())
            os.replace(temporary_path, final_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
        return StoredUpload(
            storage_key=final_path.relative_to(self.root).as_posix(),
            content_sha256=hashlib.sha256(payload).hexdigest(),
            size_bytes=len(payload),
            original_filename=final_path.name,
        )

    def read_export_bytes(self, storage_key: str, *, max_bytes: int) -> bytes:
        path = self._resolve(storage_key)
        try:
            with path.open("rb") as source:
                payload = source.read(max_bytes + 1)
        except FileNotFoundError as exc:
            raise AppError(
                status=410,
                code="export_file_missing",
                title="Export is unavailable",
                detail="Request a new data export.",
            ) from exc
        if len(payload) > max_bytes:
            raise AppError(
                status=413,
                code="export_too_large",
                title="Export is too large",
                detail="The generated export exceeds the configured download limit.",
            )
        return payload

    def read_bytes(self, storage_key: str, *, max_bytes: int) -> bytes:
        path = self._resolve(storage_key)
        try:
            with path.open("rb") as source:
                payload = source.read(max_bytes + 1)
        except FileNotFoundError as exc:
            raise AppError(
                status=410,
                code="retained_file_missing",
                title="Retained file is unavailable",
                detail="Upload the CSV file again.",
            ) from exc
        if len(payload) > max_bytes:
            raise AppError(
                status=413,
                code="file_too_large",
                title="File is too large",
                detail="The retained CSV exceeds the configured upload limit.",
            )
        return payload

    def delete(self, storage_key: str | None) -> None:
        if storage_key:
            self._resolve(storage_key).unlink(missing_ok=True)

    def cleanup_orphans(
        self,
        *,
        known_storage_keys: set[str],
        temporary_before_epoch: float,
        retained_before_epoch: float,
    ) -> int:
        import_root = self._resolve("imports")
        if not import_root.exists():
            return 0
        removed = 0
        for path in import_root.rglob("*"):
            if not path.is_file():
                continue
            safe_path = self._resolve(path.relative_to(self.root).as_posix())
            relative_key = safe_path.relative_to(self.root).as_posix()
            modified_at = safe_path.stat().st_mtime
            is_stale_temporary = (
                safe_path.name.endswith(".uploading") and modified_at < temporary_before_epoch
            )
            is_orphaned_retained = (
                safe_path.suffix == ".csv"
                and relative_key not in known_storage_keys
                and modified_at < retained_before_epoch
            )
            if is_stale_temporary or is_orphaned_retained:
                safe_path.unlink(missing_ok=True)
                removed += 1
        return removed
