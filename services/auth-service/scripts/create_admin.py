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
endpoint (to be added when the admin panel is built).

Usage (from services/auth-service/ with venv active and env vars set):
    python -m scripts.create_admin
"""
import getpass
import sys

sys.path.insert(0, ".")

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.repositories.postgres_user_repository import PostgresUserRepository


def main():
    print("=== DevBhumi: Create first admin account ===")
    name = input("Name: ").strip()
    phone = input("Phone (10-15 digits, e.g. +919876543210): ").strip()
    password = getpass.getpass("Password (min 8 chars, 1 uppercase, 1 digit): ")

    if len(password) < 8:
        print("Password too short. Aborting.")
        return

    db = SessionLocal()
    repo = PostgresUserRepository(db)

    if repo.get_by_phone(phone):
        print(f"A user with phone {phone} already exists. Aborting.")
        return

    admin = User(
        name=name,
        phone=phone,
        hashed_password=hash_password(password),
        role="admin",
    )
    created = repo.create(admin)
    print(f"Admin account created: id={created.id}, phone={created.phone}")


if __name__ == "__main__":
    main()
