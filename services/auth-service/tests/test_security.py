"""
Unit tests for app/core/security.py — no database, no network.
Run with: pytest tests/test_security.py -v
"""
import os
import time
import sys

sys.path.insert(0, ".")

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_PRIVATE_KEY_PATH", "/tmp/fake_secrets/priv.pem")
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", "/tmp/fake_secrets/pub.pem")

import pytest
from jose import JWTError

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


def test_password_hash_and_verify_roundtrip():
    plain = "StrongPass123"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True


def test_wrong_password_fails_verification():
    hashed = hash_password("CorrectPass123")
    assert verify_password("WrongPass123", hashed) is False


def test_access_token_roundtrip():
    token, jti = create_access_token(user_id="user-123", role="citizen", district="nainital")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "citizen"
    assert payload["district"] == "nainital"
    assert payload["type"] == "access"
    assert payload["jti"] == jti


def test_refresh_token_has_longer_expiry_than_access_token():
    access_token, _ = create_access_token(user_id="user-123", role="tourist")
    refresh_token, _ = create_refresh_token(user_id="user-123", role="tourist")

    access_payload = decode_token(access_token)
    refresh_payload = decode_token(refresh_token)

    assert refresh_payload["exp"] > access_payload["exp"]
    assert access_payload["type"] == "access"
    assert refresh_payload["type"] == "refresh"


def test_tampered_token_fails_verification():
    token, _ = create_access_token(user_id="user-123", role="tourist")
    # Flip a character in the signature portion
    tampered = token[:-5] + ("a" if token[-5] != "a" else "b") + token[-4:]

    with pytest.raises(JWTError):
        decode_token(tampered)


def test_each_token_has_unique_jti():
    token1, jti1 = create_access_token(user_id="user-123", role="tourist")
    token2, jti2 = create_access_token(user_id="user-123", role="tourist")
    assert jti1 != jti2
