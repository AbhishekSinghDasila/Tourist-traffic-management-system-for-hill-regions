"""
Auth routes.

Edge cases handled here, per the blueprint section 4.1:
- Duplicate phone on register -> 409, not 500
- Wrong password -> 401 with generic message (don't reveal whether
  phone exists, to avoid account enumeration)
- Expired refresh token -> 401 SESSION_EXPIRED
- Logout blacklists only the current session's jti, not all sessions
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, oauth2_scheme
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    blacklist_token,
)
from app.models.user import User
from app.repositories.postgres_user_repository import PostgresUserRepository
from app.schemas.user import UserRegister, UserPublic, TokenResponse, AccessTokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    repo = PostgresUserRepository(db)

    existing = repo.get_by_phone(payload.phone)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_code": "PHONE_ALREADY_REGISTERED", "message": "An account with this phone number already exists"},
        )

    user = User(
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        district=payload.district,
    )
    created = repo.create(user)
    return created


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    repo = PostgresUserRepository(db)

    # form_data.username carries the phone number (OAuth2 form spec
    # names it 'username' but we treat it as phone)
    user = repo.get_by_phone(form_data.username)

    # Deliberately generic error for both "no such user" and "wrong
    # password" — revealing which one it was enables account enumeration.
    invalid_creds = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error_code": "INVALID_CREDENTIALS", "message": "Incorrect phone number or password"},
    )

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise invalid_creds

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "ACCOUNT_DEACTIVATED", "message": "This account has been deactivated"},
        )

    access_token, _ = create_access_token(str(user.id), user.role, user.district)
    refresh_token, _ = create_refresh_token(str(user.id), user.role, user.district)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(refresh_token: str, db: Session = Depends(get_db)):
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "SESSION_EXPIRED", "message": "Refresh token is invalid or expired. Please log in again."},
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "WRONG_TOKEN_TYPE", "message": "Access token used where refresh token required"},
        )

    jti = payload.get("jti")
    from app.core.security import is_token_blacklisted
    if jti and is_token_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "TOKEN_REVOKED", "message": "This session has been logged out"},
        )

    repo = PostgresUserRepository(db)
    user = repo.get_by_id(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "USER_NOT_FOUND", "message": "User account no longer exists"},
        )

    # Note: we intentionally use the user's CURRENT role from the DB here,
    # not the role embedded in the old refresh token. This still means a
    # role change won't take effect on the existing access token until
    # next refresh — but at least refresh reflects the latest role rather
    # than perpetuating a stale one indefinitely.
    new_access_token, _ = create_access_token(str(user.id), user.role, user.district)
    return AccessTokenResponse(access_token=new_access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_token(token)
    except JWTError:
        # Token is already invalid/expired — nothing to blacklist, treat as success
        return

    jti = payload.get("jti")
    exp = payload.get("exp")
    if jti and exp:
        remaining_ttl = int(exp - datetime.now(timezone.utc).timestamp())
        blacklist_token(jti, remaining_ttl)


@router.get("/me", response_model=UserPublic)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
