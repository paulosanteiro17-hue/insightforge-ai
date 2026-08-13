from __future__ import annotations

import pytest
from pydantic import ValidationError

from insightforge.core.config import Settings


def test_local_environment_uses_an_explicit_non_secure_cookie_name() -> None:
    settings = Settings(_env_file=None, environment="development", session_cookie_secure=False)

    assert settings.session_cookie_name == "insightforge_session_local"


def test_secure_environment_uses_host_prefixed_cookie_name() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        session_cookie_secure=True,
        csrf_signing_key="deployment-specific-signing-key-with-sufficient-entropy",
    )

    assert settings.session_cookie_name == "__Host-insightforge_session"
    assert settings.docs_url is None


def test_production_rejects_insecure_cookie_configuration() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            session_cookie_secure=False,
            csrf_signing_key="deployment-specific-signing-key-with-sufficient-entropy",
        )


def test_credentialed_cors_rejects_wildcards() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, allowed_origins=["*"])


def test_csrf_signing_key_requires_minimum_length() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, csrf_signing_key="too-short")


def test_production_rejects_documented_placeholder_signing_key() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            session_cookie_secure=True,
            csrf_signing_key="replace-with-at-least-32-random-characters",
        )


def test_deterministic_intelligence_needs_no_openai_configuration(monkeypatch) -> None:
    for name in (
        "INSIGHTFORGE_AI_PROVIDER",
        "INSIGHTFORGE_OPENAI_API_KEY",
        "OPENAI_API_KEY",
        "INSIGHTFORGE_OPENAI_MODEL",
        "OPENAI_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.ai_provider == "deterministic"
    assert settings.openai_api_key is None
    assert settings.openai_model == "gpt-5.6-sol"


def test_openai_intelligence_requires_a_key_and_bounds_timeout() -> None:
    with pytest.raises(ValidationError, match="OPENAI_API_KEY"):
        Settings(_env_file=None, ai_provider="openai")
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            ai_provider="openai",
            openai_api_key="test-key",
            openai_timeout_seconds=121,
        )

    settings = Settings(
        _env_file=None,
        ai_provider="openai",
        openai_api_key="test-key",
        openai_model="gpt-5.6-sol",
        openai_timeout_seconds=15,
    )
    assert settings.openai_api_key is not None
    assert settings.openai_api_key.get_secret_value() == "test-key"
