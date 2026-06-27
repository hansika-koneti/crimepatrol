"""
CrimePatrol — JWT Authentication & Password Security
Single-admin dashboard: no RBAC. One admin user only.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.core.config import get_settings
from backend.core.exceptions import InvalidTokenError, TokenExpiredError

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =============================================================================
# Password Utilities
# =============================================================================

def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the plain-text password."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if the plain-text password matches the hash."""
    return _pwd_context.verify(plain, hashed)


# =============================================================================
# JWT Utilities
# =============================================================================

def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject: Identity claim — typically the admin email.
        extra_claims: Optional additional payload fields.
        expires_delta: Override default expiry from settings.

    Returns:
        Signed JWT string.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.app_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Raises:
        TokenExpiredError: Token has expired.
        InvalidTokenError: Token is malformed or signature is invalid.

    Returns:
        Decoded payload dict.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.app_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as exc:
        if "expired" in str(exc).lower():
            raise TokenExpiredError("Access token has expired.") from exc
        raise InvalidTokenError(f"Invalid token: {exc}") from exc


def get_token_subject(token: str) -> str:
    """
    Extract the `sub` claim from a valid token.

    Raises:
        InvalidTokenError: If `sub` is missing.
    """
    payload = decode_access_token(token)
    subject = payload.get("sub")
    if not subject:
        raise InvalidTokenError("Token is missing subject claim.")
    return str(subject)
