"""
Core security primitives: password hashing and JWT issue/verification.

JWT design decisions (do not change without re-reading the blueprint):
- RS256 (asymmetric) — private key signs, public key verifies.
  This means other services can verify tokens without ever holding
  the signing key.
- Access token: short-lived (15 min). Refresh token: long-lived (7 days).
- Every token carries a unique 'jti' (JWT ID) so it can be individually
  revoked via the Redis blacklist, without invalidating other sessions
  for the same user.
"""
import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings
from app.core.redis_client import redis_client

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(subject: str, role: str, district: str | None, expires_delta: timedelta, token_type: str) -> tuple[str, str]:
    """Returns (encoded_token, jti). jti is returned separately so the
    caller can store refresh-token jti's if needed for rotation tracking."""
    now = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())
    payload = {
        "sub": subject,
        "role": role,
        "district": district,
        "iat": now,
        "exp": now + expires_delta,
        "jti": jti,
        "iss": settings.JWT_ISSUER,
        "type": token_type,
    }
    token = jwt.encode(payload, settings.jwt_private_key, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def create_access_token(user_id: str, role: str, district: str | None = None) -> tuple[str, str]:
    return _create_token(
        subject=user_id,
        role=role,
        district=district,
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )


def create_refresh_token(user_id: str, role: str, district: str | None = None) -> tuple[str, str]:
    return _create_token(
        subject=user_id,
        role=role,
        district=district,
        expires_delta=timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )


def decode_token(token: str) -> dict:
    """Raises JWTError if signature is invalid, expired, or malformed.
    Callers must catch this and translate to a 401 response."""
    payload = jwt.decode(
        token,
        settings.jwt_public_key,
        algorithms=[settings.JWT_ALGORITHM],
        issuer=settings.JWT_ISSUER,
    )
    return payload


def blacklist_token(jti: str, ttl_seconds: int) -> None:
    """Called on logout. Adds the token's jti to Redis so it is
    rejected on future requests even though it hasn't expired yet."""
    if ttl_seconds > 0:
        redis_client.setex(f"blacklist:{jti}", ttl_seconds, "1")


def is_token_blacklisted(jti: str) -> bool:
    return redis_client.exists(f"blacklist:{jti}") == 1
