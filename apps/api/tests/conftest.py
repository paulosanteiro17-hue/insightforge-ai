from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from insightforge.core.config import Settings  # noqa: E402
from insightforge.main import create_app  # noqa: E402


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="testing",
        allowed_origins=["http://testserver"],
        csrf_allowed_origins=["http://testserver"],
        allowed_hosts=["testserver"],
        csrf_signing_key="unit-test-csrf-signing-key-that-is-long-enough",
        build_version="test-version",
        build_commit="test-commit",
        build_timestamp="2026-08-10T00:00:00Z",
    )


@pytest.fixture
def application(test_settings: Settings):
    return create_app(test_settings)
