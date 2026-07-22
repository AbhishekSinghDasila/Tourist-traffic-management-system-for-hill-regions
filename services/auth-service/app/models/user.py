"""
User model.

Note: role is a plain string column, not a DB enum, so adding a new
role later doesn't require a migration that touches an enum type.
Validity of role values is enforced at the application layer
(see app/schemas/user.py and the VALID_ROLES constant).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base

VALID_ROLES = ("tourist", "citizen", "police", "emergency_team", "admin")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(120), nullable=False)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="tourist")

    # district is relevant for citizen/police roles — used for RBAC
    # row-level filtering (police only see complaints in their district)
    district = Column(String(80), nullable=True)
    station_id = Column(String(80), nullable=True)  # police only

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
