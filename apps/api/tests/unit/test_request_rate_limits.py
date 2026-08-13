from __future__ import annotations

import pytest

from insightforge.api.rate_limits import (
    AUTH_GLOBAL,
    LOGIN_ACCOUNT,
    RequestRateLimits,
    rate_limit_subject_digest,
)
from insightforge.core.config import Settings
from insightforge.core.problems import AppError


def rate_limit_settings() -> Settings:
    return Settings(
        _env_file=None,
        csrf_signing_key="rate-limit-test-signing-key-with-enough-entropy",
        auth_global_limit=1,
        login_account_limit=1,
    )


def test_subject_digest_is_scoped_stable_and_does_not_expose_input() -> None:
    settings = rate_limit_settings()

    first = rate_limit_subject_digest(
        settings,
        scope=LOGIN_ACCOUNT,
        subject="owner@example.invalid",
    )
    repeated = rate_limit_subject_digest(
        settings,
        scope=LOGIN_ACCOUNT,
        subject="owner@example.invalid",
    )
    other_scope = rate_limit_subject_digest(
        settings,
        scope=AUTH_GLOBAL,
        subject="owner@example.invalid",
    )

    assert first == repeated
    assert first != other_scope
    assert "owner" not in first
    assert len(first) == 64


@pytest.mark.asyncio
async def test_request_limit_returns_safe_problem_and_retry_after() -> None:
    limits = RequestRateLimits(rate_limit_settings())

    await limits.enforce(scope=LOGIN_ACCOUNT, subject="owner@example.invalid")
    with pytest.raises(AppError) as captured:
        await limits.enforce(scope=LOGIN_ACCOUNT, subject="owner@example.invalid")

    assert captured.value.status == 429
    assert captured.value.code == "rate_limit_exceeded"
    assert captured.value.headers["Retry-After"] == "300"


@pytest.mark.asyncio
async def test_request_limits_reject_unknown_internal_scope() -> None:
    limits = RequestRateLimits(rate_limit_settings())

    with pytest.raises(RuntimeError, match="unknown rate-limit scope"):
        await limits.enforce(scope="auth.unknown", subject="subject")
