from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from insightforge.core.config import Settings
from insightforge.core.problems import AppError
from insightforge.core.rate_limiting import RateLimitKey, SlidingWindowRateLimiter

LOGIN_ACCOUNT = "auth.login.account"
AUTH_GLOBAL = "auth.global"
REGISTER_BROWSER = "auth.register.browser"
DEMO_BROWSER = "auth.demo.browser"
DEMO_GLOBAL = "auth.demo.global"
INVITATION_ACCOUNT = "team.invitation.account"
INVITATION_RESEND = "team.invitation.resend"
PASSWORD_CHANGE = "users.password.change"  # noqa: S105 - rate-limit scope, not a credential
PASSWORD_RESET = "auth.password.reset"  # noqa: S105 - rate-limit scope, not a credential
ASK_DATA = "analytics.ask_data"
INTELLIGENCE_GENERATION = "analytics.intelligence_generation"
REPORT_GENERATION = "reports.generation"


@dataclass(frozen=True, slots=True)
class RateLimitRule:
    limit: int
    window_seconds: int


def rate_limit_subject_digest(settings: Settings, *, scope: str, subject: str) -> str:
    """HMAC a low-entropy subject before it reaches the in-process limiter."""

    message = f"rate-limit:v1:{scope}:{subject}".encode()
    return hmac.new(
        settings.csrf_signing_key.get_secret_value().encode(),
        message,
        hashlib.sha256,
    ).hexdigest()


class RequestRateLimits:
    """Application-owned auth limits; public deployments also require trusted edge limits."""

    def __init__(self, settings: Settings) -> None:
        rules = {
            LOGIN_ACCOUNT: RateLimitRule(
                settings.login_account_limit,
                settings.login_account_window_seconds,
            ),
            AUTH_GLOBAL: RateLimitRule(
                settings.auth_global_limit,
                settings.auth_global_window_seconds,
            ),
            REGISTER_BROWSER: RateLimitRule(
                settings.register_browser_limit,
                settings.register_browser_window_seconds,
            ),
            DEMO_BROWSER: RateLimitRule(
                settings.demo_browser_limit,
                settings.demo_browser_window_seconds,
            ),
            DEMO_GLOBAL: RateLimitRule(
                settings.demo_global_limit,
                settings.demo_global_window_seconds,
            ),
            INVITATION_ACCOUNT: RateLimitRule(
                settings.invitation_account_limit,
                settings.invitation_account_window_seconds,
            ),
            INVITATION_RESEND: RateLimitRule(
                settings.invitation_resend_limit,
                settings.invitation_resend_window_seconds,
            ),
            PASSWORD_CHANGE: RateLimitRule(
                settings.password_change_limit,
                settings.password_change_window_seconds,
            ),
            PASSWORD_RESET: RateLimitRule(
                settings.password_reset_limit,
                settings.password_reset_window_seconds,
            ),
            ASK_DATA: RateLimitRule(
                settings.ask_data_limit,
                settings.ask_data_window_seconds,
            ),
            INTELLIGENCE_GENERATION: RateLimitRule(
                settings.intelligence_generation_limit,
                settings.intelligence_generation_window_seconds,
            ),
            REPORT_GENERATION: RateLimitRule(
                settings.report_generation_limit,
                settings.report_generation_window_seconds,
            ),
        }
        self._limiters = {
            scope: SlidingWindowRateLimiter(
                limit=rule.limit,
                window_seconds=rule.window_seconds,
                max_keys=settings.rate_limit_max_keys,
            )
            for scope, rule in rules.items()
        }
        self._settings = settings

    async def enforce(self, *, scope: str, subject: str) -> None:
        try:
            limiter = self._limiters[scope]
        except KeyError as exc:
            raise RuntimeError("An unknown rate-limit scope was requested.") from exc
        digest = rate_limit_subject_digest(self._settings, scope=scope, subject=subject)
        decision = await limiter.acquire(RateLimitKey(scope=scope, subject_digest=digest))
        if decision.allowed:
            return
        retry_after = decision.retry_after or 1
        raise AppError(
            status=429,
            code="rate_limit_exceeded",
            title="Too many requests",
            detail="Wait before trying again.",
            headers={"Retry-After": str(retry_after)},
        )


def get_request_rate_limits(request: Request) -> RequestRateLimits:
    limits = getattr(request.app.state, "request_rate_limits", None)
    if not isinstance(limits, RequestRateLimits):
        raise RuntimeError("Request rate limits were not initialized.")
    return limits


RequestRateLimitsDependency = Annotated[RequestRateLimits, Depends(get_request_rate_limits)]
