"""JWT verification for alert-service — verify only, no signing."""
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.core.redis_client import redis_client

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://localhost:8001/api/v1/auth/login")


@dataclass
class TokenUser:
    user_id: str
    role: str
    district: Optional[str]
    jti: str


def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenUser:
    err = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error_code": "INVALID_TOKEN", "message": "Could not validate credentials"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.jwt_public_key,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
        )
    except JWTError:
        raise err

    if payload.get("type") != "access":
        raise err

    jti = payload.get("jti", "")
    if redis_client.exists(f"blacklist:{jti}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "TOKEN_REVOKED", "message": "Session logged out"},
        )

    return TokenUser(
        user_id=payload["sub"],
        role=payload.get("role", "tourist"),
        district=payload.get("district"),
        jti=jti,
    )


def require_role(*allowed_roles: str):
    def dependency(current_user: TokenUser = Depends(get_current_user)) -> TokenUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error_code": "INSUFFICIENT_PERMISSIONS",
                        "message": f"Requires one of roles: {allowed_roles}"},
            )
        return current_user
    return dependency
