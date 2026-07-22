"""
FastAPI dependencies for authentication and RBAC.

require_role() is used at the route level — never inside service
logic. This keeps role-checking in exactly one place, so there's
no risk of a route forgetting to check, or checking inconsistently.
"""
from jose import JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token, is_token_blacklisted
from app.models.user import User
from app.repositories.postgres_user_repository import PostgresUserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error_code": "INVALID_TOKEN", "message": "Could not validate credentials"},
    )

    try:
        payload = decode_token(token)
    except JWTError:
        raise credentials_error

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "WRONG_TOKEN_TYPE", "message": "Refresh token used where access token required"},
        )

    jti = payload.get("jti")
    if jti and is_token_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "TOKEN_REVOKED", "message": "This session has been logged out"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_error

    repo = PostgresUserRepository(db)
    user = repo.get_by_id(user_id)
    if user is None:
        # Covers the edge case: account deactivated/deleted while token
        # is still technically valid by signature/expiry.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "USER_NOT_FOUND", "message": "User account no longer exists or is inactive"},
        )

    return user


def require_role(*allowed_roles: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error_code": "INSUFFICIENT_PERMISSIONS", "message": f"This action requires one of roles: {allowed_roles}"},
            )
        return current_user
    return dependency
