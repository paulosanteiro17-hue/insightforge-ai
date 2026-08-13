from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

pytestmark = pytest.mark.postgres


@pytest.mark.asyncio
async def test_configured_postgres_database_supports_basic_readiness_query() -> None:
    database_url = os.environ.get("INSIGHTFORGE_TEST_DATABASE_URL")
    if not database_url:
        if os.environ.get("CI", "").casefold() == "true":
            pytest.fail("CI must configure INSIGHTFORGE_TEST_DATABASE_URL.")
        pytest.skip("INSIGHTFORGE_TEST_DATABASE_URL is not configured.")
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            assert await connection.scalar(text("SELECT 1")) == 1
    finally:
        await engine.dispose()
