from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type

from insightforge.core.config import Settings

_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65_536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


@dataclass(frozen=True, slots=True)
class SessionSecrets:
    token: str
    token_hash: str
    csrf_token: str
    csrf_token_hash: str


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        return _password_hasher.verify(encoded_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def password_needs_rehash(encoded_hash: str) -> bool:
    try:
        return _password_hasher.check_needs_rehash(encoded_hash)
    except InvalidHashError:
        return True


def random_token(byte_count: int = 32) -> str:
    if byte_count < 32:
        raise ValueError("Security tokens must contain at least 256 bits of entropy.")
    return secrets.token_urlsafe(byte_count)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def create_session_secrets() -> SessionSecrets:
    token = random_token()
    csrf_token = random_token()
    return SessionSecrets(
        token=token,
        token_hash=hash_token(token),
        csrf_token=csrf_token,
        csrf_token_hash=hash_token(csrf_token),
    )


def create_pre_auth_csrf_token(settings: Settings, *, now: int | None = None) -> str:
    issued_at = int(time.time() if now is None else now)
    nonce = random_token()
    payload = f"v1.{issued_at}.{nonce}"
    signature = hmac.new(
        settings.csrf_signing_key.get_secret_value().encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{payload}.{encoded_signature}"


def verify_pre_auth_csrf_token(
    token: str,
    settings: Settings,
    *,
    now: int | None = None,
) -> bool:
    parts = token.split(".")
    if len(parts) != 4 or parts[0] != "v1":
        return False
    try:
        issued_at = int(parts[1])
    except ValueError:
        return False
    current_time = int(time.time() if now is None else now)
    if issued_at > current_time + 30 or current_time - issued_at > settings.csrf_token_ttl_seconds:
        return False
    payload = ".".join(parts[:3])
    expected = hmac.new(
        settings.csrf_signing_key.get_secret_value().encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    try:
        supplied = base64.urlsafe_b64decode(parts[3] + "=" * (-len(parts[3]) % 4))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(expected, supplied)


def origin_is_allowed(origin: str, settings: Settings) -> bool:
    return origin.rstrip("/") in settings.csrf_allowed_origins
