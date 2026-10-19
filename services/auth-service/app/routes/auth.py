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

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user, oauth2_scheme, require_role
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
from app.schemas.user import UserRegister, UserPublic, AccessTokenResponse, AdminUserCreate

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# The refresh token never needs to be readable by frontend JS — it only
# ever needs to travel back to these two auth routes. HttpOnly means an
# XSS bug elsewhere in the frontend can't exfiltrate it; scoping the
# cookie path here (rather than "/") means the browser doesn't attach it
# to every other service's requests either.
REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


@router.get("/users", response_model=list[UserPublic])
def list_users(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    return db.query(User).order_by(User.created_at, User.id).offset(offset).limit(limit).all()


@router.post("/users", response_model=UserPublic, status_code=201)
def create_managed_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    if payload.role == "police" and not payload.district:
        raise HTTPException(422, detail="Police accounts require a district")
    user = User(
        **payload.model_dump(exclude={"password"}),
        hashed_password=hash_password(payload.password),
    )
    try:
        return PostgresUserRepository(db).create(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, detail="An account with that phone or email already exists")


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT != "development",
        samesite="lax",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,
    )


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
    try:
        return repo.create(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, detail="An account with that phone or email already exists")


@router.post("/login", response_model=AccessTokenResponse)
def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
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
    _set_refresh_cookie(response, refresh_token)

    return AccessTokenResponse(access_token=access_token)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    no_cookie = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error_code": "SESSION_EXPIRED", "message": "Refresh token is invalid or expired. Please log in again."},
    )
    if refresh_token is None:
        raise no_cookie

    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise no_cookie

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
def logout(
    response: Response,
    token: str = Depends(oauth2_scheme),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    # Blacklist both tokens for this session — not just the short-lived
    # access token. Without blacklisting the refresh token too, "logout"
    # would only last 15 minutes: the refresh cookie could still mint a
    # fresh access token for up to its full 7-day life.
    for t in (token, refresh_token):
        if not t:
            continue
        try:
            payload = decode_token(t)
        except JWTError:
            continue
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            remaining_ttl = int(exp - datetime.now(timezone.utc).timestamp())
            blacklist_token(jti, remaining_ttl)

    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


@router.get("/me", response_model=UserPublic)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
