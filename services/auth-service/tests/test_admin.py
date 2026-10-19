from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4
from sqlalchemy.exc import IntegrityError
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.user import AdminUserCreate, UserRegister

PAYLOAD = dict(name="Officer", phone="+919876543210", password="StrongPass123",
               role="police", district="nainital")


def test_public_registration_cannot_create_staff():
    with pytest.raises(ValidationError):
        UserRegister(**PAYLOAD)
    assert AdminUserCreate(**PAYLOAD).role == "police"


@pytest.mark.parametrize("role", ["tourist", "citizen", "police", "emergency_team"])
def test_non_admin_cannot_list_or_create_accounts(role):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role=role)
    app.dependency_overrides[get_db] = lambda: MagicMock()
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/auth/users").status_code == 403
            assert client.post("/api/v1/auth/users", json=PAYLOAD).status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_admin_can_list_and_police_requires_district():
    db = MagicMock()
    db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="admin")
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/auth/users").json() == []
            assert client.post("/api/v1/auth/users", json={**PAYLOAD, "district": None}).status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_admin_creation_hashes_password_and_excludes_hash_from_response():
    from app.core.security import verify_password
    captured = []
    def persist(user):
        user.id = uuid4()
        captured.append(user)
        return user
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="admin")
    app.dependency_overrides[get_db] = lambda: MagicMock()
    try:
        with patch("app.routes.auth.PostgresUserRepository.create", side_effect=persist):
            response = TestClient(app).post("/api/v1/auth/users", json=PAYLOAD)
        assert response.status_code == 201
        assert response.json()["role"] == "police"
        assert "hashed_password" not in response.json()
        assert "password" not in response.json()
        assert verify_password(PAYLOAD["password"], captured[0].hashed_password)
    finally:
        app.dependency_overrides.clear()


def test_duplicate_managed_account_rolls_back():
    db = MagicMock()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="admin")
    app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("app.routes.auth.PostgresUserRepository.create",
                   side_effect=IntegrityError("insert", {}, Exception("duplicate"))):
            assert TestClient(app).post("/api/v1/auth/users", json=PAYLOAD).status_code == 409
        db.rollback.assert_called_once()
    finally:
        app.dependency_overrides.clear()
