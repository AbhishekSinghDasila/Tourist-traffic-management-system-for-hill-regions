"""
Postgres implementation of IUserRepository.

All queries here use the ORM (parameterised under the hood) —
never raw string-formatted SQL. This is the only file in the
service that touches the users table directly.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repository import IUserRepository


class PostgresUserRepository(IUserRepository):

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id, User.is_active == True).first()  # noqa: E712

    def get_by_phone(self, phone: str) -> Optional[User]:
        return self.db.query(User).filter(User.phone == phone).first()

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def deactivate(self, user_id: str) -> None:
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_active = False
            self.db.commit()
