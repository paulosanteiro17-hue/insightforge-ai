from __future__ import annotations

import re

from insightforge.core.problems import AppError

_ETAG_PATTERN = re.compile(r'^"(?P<version>[1-9][0-9]*)"$')


def version_etag(version: int) -> str:
    return f'"{version}"'


def require_if_match(value: str | None) -> int:
    if value is None:
        raise AppError(
            status=428,
            code="precondition_required",
            title="Version precondition required",
            detail="Send the current ETag in the If-Match header.",
        )
    match = _ETAG_PATTERN.fullmatch(value.strip())
    if match is None:
        raise AppError(
            status=400,
            code="invalid_if_match",
            title="Version precondition is invalid",
            detail="The If-Match header must contain one strong resource ETag.",
        )
    return int(match.group("version"))


def ensure_version(current_version: int, expected_version: int) -> None:
    if current_version != expected_version:
        raise AppError(
            status=412,
            code="version_conflict",
            title="Resource version changed",
            detail="Refresh the resource and try again with its current ETag.",
        )
