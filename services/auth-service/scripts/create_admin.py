"""
Bootstrap script — creates the very first admin account.

Why this exists: the /register endpoint deliberately refuses to create
admin, police, or emergency_team accounts (see UserRegister validator
in app/schemas/user.py). This is intentional — public self-registration
must never be able to grant elevated roles.

So the first admin has to be created some other way. This script is
that "some other way" — run it once, manually, after the database is
up and migrated. After that, the admin account itself creates further
police/admin/emergency_team accounts through a protected admin-only
endpoint available in the admin panel.

Usage (from services/auth-service/ with venv active and env vars set):
    python -m scripts.create_admin
"""
import getpass
import sys

sys.path.insert(0, ".")

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import AdminUserCreate
from pydantic import ValidationError
from app.repositories.postgres_user_repository import PostgresUserRepository


def main():
    print("=== DevBhumi: Create first admin account ===")
    name = input("Name: ").strip()
    phone = input("Phone (10-15 digits, e.g. +919876543210): ").strip()
    password = getpass.getpass("Password (min 8 chars, 1 uppercase, 1 digit): ")

    try:
        payload = AdminUserCreate(name=name, phone=phone, password=password, role="admin")
    except ValidationError as error:
        print("Invalid account details: " + "; ".join(item["msg"] for item in error.errors()))
        raise SystemExit(1)

    with SessionLocal() as db:
        repo = PostgresUserRepository(db)
        if repo.get_by_phone(phone):
            print("That phone is already registered.")
            raise SystemExit(1)
        admin = User(
            name=payload.name, phone=payload.phone,
            hashed_password=hash_password(payload.password), role="admin",
        )
        created = repo.create(admin)
        print(f"Admin account created: id={created.id}")


if __name__ == "__main__":
    main()
