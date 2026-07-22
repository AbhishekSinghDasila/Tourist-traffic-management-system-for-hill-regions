"""
AuditLog — records every privileged action.

Blueprint requirement: every time an admin views complaint identity
(user_id, name, phone), it must be logged. This makes it impossible
for admins to access sensitive data silently.

Also logs: status changes, account deactivations, role changes.
Audit logs can NEVER be deleted — complaint_svc has no DELETE grant
on this table.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id      = Column(UUID(as_uuid=True), nullable=False, index=True)  # who did it
    actor_role    = Column(String(20),  nullable=False)
    action        = Column(String(50),  nullable=False, index=True)
    # e.g. VIEW_COMPLAINT_IDENTITY, UPDATE_STATUS, ARCHIVE_COMPLAINT
    target_type   = Column(String(30),  nullable=False)   # e.g. "complaint"
    target_id     = Column(String(100), nullable=False)   # UUID of the target
    detail        = Column(Text,        nullable=True)    # JSON string for extra context
    created_at    = Column(DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc), index=True)
