"""
EmergencyAlert, AlertRecipient, UserLocation models.

STATUS flow: ACTIVE -> RESOLVED | CANCELLED
Blueprint edge case 4.4: CANCELLED sends cancellation push to DELIVERED recipients.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

ALERT_TYPES    = ("AMBULANCE", "ACCIDENT", "LANDSLIDE", "FLOOD", "FIRE", "OTHER")
ALERT_STATUSES = ("ACTIVE", "RESOLVED", "CANCELLED")


class EmergencyAlert(Base):
    __tablename__ = "emergency_alerts"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    triggered_by        = Column(UUID(as_uuid=True), nullable=False)
    triggered_role      = Column(String(20), nullable=False)
    alert_type          = Column(String(20), nullable=False, default="AMBULANCE")
    description         = Column(String(300), nullable=True)
    lat                 = Column(Float, nullable=False)
    lng                 = Column(Float, nullable=False)
    district            = Column(String(80), nullable=True, index=True)
    radius_km           = Column(Float, nullable=False, default=2.0)
    status              = Column(String(20), nullable=False, default="ACTIVE", index=True)
    recipients_notified = Column(Integer, nullable=False, default=0)
    created_at          = Column(DateTime(timezone=True),
                                 default=lambda: datetime.now(timezone.utc), index=True)
    resolved_at         = Column(DateTime(timezone=True), nullable=True)
    recipients          = relationship("AlertRecipient", back_populates="alert",
                                       cascade="all, delete-orphan")


class AlertRecipient(Base):
    __tablename__ = "alert_recipients"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id        = Column(UUID(as_uuid=True), ForeignKey("emergency_alerts.id"),
                             nullable=False, index=True)
    recipient_type  = Column(String(20), nullable=False)   # USER | POLICE_STATION
    recipient_id    = Column(String(100), nullable=False)
    channel         = Column(String(20), nullable=False, default="PUSH")
    delivery_status = Column(String(20), nullable=False, default="PENDING")
    sent_at         = Column(DateTime(timezone=True), nullable=True)
    alert           = relationship("EmergencyAlert", back_populates="recipients")


class UserLocation(Base):
    """Last known GPS for each user. Used for proximity checks. Never exposed via API."""
    __tablename__ = "user_locations"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    lat        = Column(Float, nullable=False)
    lng        = Column(Float, nullable=False)
    district   = Column(String(80), nullable=True)
    updated_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
