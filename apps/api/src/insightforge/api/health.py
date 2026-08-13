from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text

from insightforge.core.config import Settings, get_settings
from insightforge.db.migrations import INITIAL_REVISION
from insightforge.db.session import get_engine

router = APIRouter(prefix="/health", tags=["Health"])


class ReadinessChecker:
    async def check(self, settings: Settings) -> dict[str, str]:
        checks = {"database": "unavailable", "migration": "unknown"}
        try:
            async with asyncio.timeout(settings.readiness_timeout_seconds):
                async with get_engine(settings.database_url).connect() as connection:
                    await connection.execute(text("SELECT 1"))
                    checks["database"] = "ok"
                    revision = await connection.scalar(
                        text("SELECT version_num FROM alembic_version")
                    )
                    checks["migration"] = "ok" if revision == INITIAL_REVISION else "outdated"
        except Exception:
            return checks
        return checks


def get_readiness_checker() -> ReadinessChecker:
    return ReadinessChecker()


@router.get("/live", summary="Check process liveness")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", summary="Check database readiness")
async def ready(
    settings: Annotated[Settings, Depends(get_settings)],
    checker: Annotated[ReadinessChecker, Depends(get_readiness_checker)],
) -> JSONResponse:
    checks = await checker.check(settings)
    is_ready = all(value == "ok" for value in checks.values())
    return JSONResponse(
        status_code=200 if is_ready else 503,
        content={"status": "ok" if is_ready else "unavailable", "checks": checks},
    )


@router.get("/version", summary="Get safe build metadata")
async def version(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    return {
        "version": settings.build_version,
        "commit": settings.build_commit,
        "deployed_at": settings.build_timestamp,
    }
