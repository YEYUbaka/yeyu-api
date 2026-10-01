import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import settings

password_hash = PasswordHash(
    (
        Argon2Hasher(),
        BcryptHasher(),
    )
)


ALGORITHM = "HS256"
API_KEY_RANDOM_BYTES = 32
API_KEY_PREFIX = "yeyu_"


def generate_api_key() -> str:
    """Generate a key with at least 256 bits of CSPRNG entropy."""
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(API_KEY_RANDOM_BYTES)}"


def get_api_key_prefix(raw_key: str) -> str:
    """Return only the stable public lookup prefix for a raw key."""
    prefix_length = len(API_KEY_PREFIX) + 8
    return raw_key[:prefix_length]


def _current_api_key_pepper() -> str:
    if settings.API_KEY_PEPPER:
        return settings.API_KEY_PEPPER
    if settings.FASTAPI_ENV == "development":
        return settings.SECRET_KEY
    raise ValueError("API_KEY_PEPPER is required outside development")


def _api_key_pepper(version: int) -> str:
    current_version = settings.API_KEY_PEPPER_VERSION
    if current_version <= 0:
        raise ValueError("API_KEY_PEPPER_VERSION must be positive")
    if version == current_version:
        return _current_api_key_pepper()

    previous_pepper = settings.API_KEY_PREVIOUS_PEPPER
    previous_version = settings.API_KEY_PREVIOUS_PEPPER_VERSION
    if (previous_pepper is None) != (previous_version is None):
        raise ValueError(
            "API_KEY_PREVIOUS_PEPPER and "
            "API_KEY_PREVIOUS_PEPPER_VERSION must be configured together"
        )
    if previous_pepper is not None and previous_version is not None:
        if not previous_pepper.strip():
            raise ValueError("API_KEY_PREVIOUS_PEPPER must not be empty")
        if previous_version <= 0 or previous_version == current_version:
            raise ValueError("API key pepper versions must be positive and distinct")
        if version == previous_version:
            return previous_pepper
    raise ValueError(f"Unknown API key hash version: {version}")


def api_key_hash_versions() -> tuple[int, ...]:
    """Return configured hash versions without exposing any pepper value."""
    current_version = settings.API_KEY_PEPPER_VERSION
    _api_key_pepper(current_version)
    versions = [current_version]
    previous_pepper = settings.API_KEY_PREVIOUS_PEPPER
    previous_version = settings.API_KEY_PREVIOUS_PEPPER_VERSION
    if previous_pepper is not None and previous_version is not None:
        _api_key_pepper(previous_version)
        if previous_version not in versions:
            versions.append(previous_version)
    return tuple(versions)


def hash_api_key(raw_key: str, *, version: int | None = None) -> str:
    """Hash a raw API key with the versioned server pepper."""
    hash_version = (
        settings.API_KEY_PEPPER_VERSION if version is None else version
    )
    pepper = _api_key_pepper(hash_version).encode("utf-8")
    return hmac.new(pepper, raw_key.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_api_key_hash(raw_key: str, expected_hash: str, *, version: int) -> bool:
    try:
        actual_hash = hash_api_key(raw_key, version=version)
    except ValueError:
        return False
    return hmac.compare_digest(actual_hash, expected_hash)


def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    expire = datetime.now(UTC) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(
    plain_password: str, hashed_password: str
) -> tuple[bool, str | None]:
    return password_hash.verify_and_update(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def generate_opaque_token() -> str:
    """Return a high-entropy token whose plaintext is only sent once."""
    return secrets.token_urlsafe(32)


def hash_opaque_token(raw_token: str, *, purpose: str) -> str:
    """Hash an opaque token with the application secret before persistence."""
    message = f"{purpose}:{raw_token}".encode()
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"), message, hashlib.sha256
    ).hexdigest()
