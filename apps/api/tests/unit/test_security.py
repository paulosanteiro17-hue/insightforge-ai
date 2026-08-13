from __future__ import annotations

from insightforge.core.security import (
    constant_time_equal,
    create_pre_auth_csrf_token,
    create_session_secrets,
    hash_password,
    hash_token,
    password_needs_rehash,
    verify_password,
    verify_pre_auth_csrf_token,
)


def test_passwords_use_argon2id_and_verify_without_exposing_plaintext() -> None:
    encoded = hash_password("Correct-Horse-Battery-Staple-2026")

    assert encoded.startswith("$argon2id$")
    assert "Correct-Horse" not in encoded
    assert verify_password("Correct-Horse-Battery-Staple-2026", encoded)
    assert not verify_password("incorrect-password", encoded)
    assert not password_needs_rehash(encoded)


def test_session_material_contains_distinct_256_bit_secrets_and_only_hashes_compare() -> None:
    secrets = create_session_secrets()

    assert secrets.token != secrets.csrf_token
    assert len(secrets.token_hash) == 64
    assert len(secrets.csrf_token_hash) == 64
    assert secrets.token_hash == hash_token(secrets.token)
    assert secrets.csrf_token_hash == hash_token(secrets.csrf_token)
    assert constant_time_equal(secrets.token_hash, hash_token(secrets.token))


def test_pre_auth_csrf_tokens_are_signed_expiring_and_tamper_evident(test_settings) -> None:
    token = create_pre_auth_csrf_token(test_settings, now=1_000)

    assert verify_pre_auth_csrf_token(token, test_settings, now=1_001)
    assert not verify_pre_auth_csrf_token(f"{token}x", test_settings, now=1_001)
    assert not verify_pre_auth_csrf_token(
        token,
        test_settings,
        now=1_000 + test_settings.csrf_token_ttl_seconds + 1,
    )
