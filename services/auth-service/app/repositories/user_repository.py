"""
Repository interface for User.

Routes and services depend on this interface, not on a concrete
implementation. This makes it possible to swap in an in-memory
mock during tests without touching any route code.
"""
from abc import ABC, abstractmethod
from typing import Optional

from app.models.user import User


class IUserRepository(ABC):

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]:
        ...

    @abstractmethod
    def get_by_phone(self, phone: str) -> Optional[User]:
        ...

    @abstractmethod
    def create(self, user: User) -> User:
        ...

    @abstractmethod
    def deactivate(self, user_id: str) -> None:
        ...
