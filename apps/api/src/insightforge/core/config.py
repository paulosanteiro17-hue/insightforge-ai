from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_prefix="INSIGHTFORGE_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "InsightForge AI API"
    environment: Literal["development", "testing", "staging", "production"] = "development"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    database_url: str = Field(
        default=(
            "postgresql+asyncpg://insightforge:local-development-only@localhost:5432/insightforge"
        ),
        validation_alias=AliasChoices("INSIGHTFORGE_DATABASE_URL", "DATABASE_URL"),
    )
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    csrf_allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    allowed_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )

    session_cookie_secure: bool = False
    session_idle_minutes: int = Field(default=10_080, ge=5, le=43_200)
    session_absolute_hours: int = Field(default=720, ge=1, le=2_160)
    demo_session_hours: int = Field(default=8, ge=1, le=24)
    session_activity_write_interval_seconds: int = Field(default=300, ge=30, le=3_600)
    csrf_signing_key: SecretStr = Field(
        default=SecretStr("development-only-change-this-csrf-signing-key-before-production"),
        min_length=32,
    )
    csrf_token_ttl_seconds: int = Field(default=3_600, ge=300, le=86_400)

    rate_limit_max_keys: int = Field(default=10_000, ge=100, le=1_000_000)
    login_account_limit: int = Field(default=10, ge=1, le=10_000)
    login_account_window_seconds: int = Field(default=300, ge=1, le=86_400)
    auth_global_limit: int = Field(default=120, ge=1, le=100_000)
    auth_global_window_seconds: int = Field(default=60, ge=1, le=86_400)
    register_browser_limit: int = Field(default=5, ge=1, le=10_000)
    register_browser_window_seconds: int = Field(default=3_600, ge=1, le=86_400)
    demo_browser_limit: int = Field(default=3, ge=1, le=10_000)
    demo_browser_window_seconds: int = Field(default=3_600, ge=1, le=86_400)
    demo_global_limit: int = Field(default=30, ge=1, le=100_000)
    demo_global_window_seconds: int = Field(default=60, ge=1, le=86_400)
    invitation_account_limit: int = Field(default=20, ge=1, le=10_000)
    invitation_account_window_seconds: int = Field(default=3_600, ge=1, le=86_400)
    invitation_resend_limit: int = Field(default=5, ge=1, le=10_000)
    invitation_resend_window_seconds: int = Field(default=3_600, ge=1, le=86_400)
    invitation_expiry_hours: int = Field(default=168, ge=1, le=720)
    password_change_limit: int = Field(default=5, ge=1, le=10_000)
    password_change_window_seconds: int = Field(default=3_600, ge=1, le=86_400)
    password_reset_limit: int = Field(default=5, ge=1, le=10_000)
    password_reset_window_seconds: int = Field(default=3_600, ge=1, le=86_400)
    password_reset_expiry_minutes: int = Field(default=30, ge=5, le=1_440)
    ask_data_limit: int = Field(default=30, ge=1, le=10_000)
    ask_data_window_seconds: int = Field(default=60, ge=1, le=86_400)
    intelligence_generation_limit: int = Field(default=10, ge=1, le=10_000)
    intelligence_generation_window_seconds: int = Field(default=300, ge=1, le=86_400)
    report_generation_limit: int = Field(default=10, ge=1, le=10_000)
    report_generation_window_seconds: int = Field(default=300, ge=1, le=86_400)

    private_storage_path: Path = Path(".data/private")
    upload_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1, le=100 * 1024 * 1024)
    upload_max_rows: int = Field(default=50_000, ge=1, le=500_000)
    import_max_errors: int = Field(default=100, ge=1, le=1_000)
    import_preview_rows: int = Field(default=20, ge=0, le=100)
    import_retention_hours: int = Field(default=168, ge=24, le=2_160)
    export_max_bytes: int = Field(default=20 * 1024 * 1024, ge=1, le=100 * 1024 * 1024)
    export_max_rows: int = Field(default=50_000, ge=1, le=500_000)
    export_retention_hours: int = Field(default=24, ge=1, le=168)
    organization_deletion_grace_hours: int = Field(default=168, ge=1, le=720)
    worker_poll_seconds: float = Field(default=1.0, ge=0.1, le=60)
    worker_lease_seconds: int = Field(default=120, ge=30, le=3_600)
    worker_id: str = Field(default="insightforge-worker", min_length=3, max_length=120)

    ai_provider: Literal["deterministic", "openai"] = "deterministic"
    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("INSIGHTFORGE_OPENAI_API_KEY", "OPENAI_API_KEY"),
    )
    openai_model: str = Field(
        default="gpt-5.6-sol",
        min_length=1,
        max_length=120,
        validation_alias=AliasChoices("INSIGHTFORGE_OPENAI_MODEL", "OPENAI_MODEL"),
    )
    openai_timeout_seconds: float = Field(default=20.0, gt=0, le=120)

    demo_mode: bool = True
    readiness_timeout_seconds: float = Field(default=2.0, gt=0, le=10)
    build_version: str = "0.1.0"
    build_commit: str = "development"
    build_timestamp: str = "unknown"

    @field_validator("allowed_origins", "csrf_allowed_origins")
    @classmethod
    def reject_wildcard_origins(cls, values: list[str]) -> list[str]:
        normalized = [value.rstrip("/") for value in values]
        if "*" in normalized:
            raise ValueError("Wildcard origins are not allowed with credentialed requests.")
        return normalized

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("Log level is not supported.")
        return normalized

    @model_validator(mode="after")
    def validate_security_configuration(self) -> Settings:
        if self.ai_provider == "openai" and (
            self.openai_api_key is None or not self.openai_api_key.get_secret_value().strip()
        ):
            raise ValueError("OPENAI_API_KEY is required when the OpenAI provider is enabled.")
        if self.environment in {"staging", "production"}:
            if not self.session_cookie_secure:
                raise ValueError("Secure session cookies are required outside local environments.")
            signing_key = self.csrf_signing_key.get_secret_value().casefold()
            unsafe_key_prefixes = (
                "development-only",
                "replace-with",
                "local-compose",
                "change-me",
            )
            if signing_key.startswith(unsafe_key_prefixes):
                raise ValueError("A deployment-specific CSRF signing key is required.")
        return self

    @property
    def session_cookie_name(self) -> str:
        if self.session_cookie_secure:
            return "__Host-insightforge_session"
        return "insightforge_session_local"

    @property
    def csrf_cookie_name(self) -> str:
        return "insightforge_csrf"

    @property
    def docs_url(self) -> str | None:
        return "/api/docs" if self.environment in {"development", "testing"} else None


@lru_cache
def get_settings() -> Settings:
    return Settings()
