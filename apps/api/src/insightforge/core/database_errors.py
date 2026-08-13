from __future__ import annotations

from sqlalchemy.exc import IntegrityError


def integrity_constraint_name(exc: IntegrityError) -> str | None:
    """Extract a PostgreSQL constraint name without depending on one DBAPI wrapper."""

    current: object | None = exc.orig
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        name = getattr(current, "constraint_name", None)
        if isinstance(name, str):
            return name
        diagnostic = getattr(current, "diag", None)
        diagnostic_name = getattr(diagnostic, "constraint_name", None)
        if isinstance(diagnostic_name, str):
            return diagnostic_name
        current = getattr(current, "__cause__", None) or getattr(current, "__context__", None)
    return None
