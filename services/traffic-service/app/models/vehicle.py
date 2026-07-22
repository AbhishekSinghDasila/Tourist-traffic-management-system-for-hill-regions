"""
Vehicle — a vehicle seen at a checkpoint.

plate_number is the primary identifier. flag_count tracks how many
complaints have been filed against this vehicle — used for the
reputation system in a later week.

We deliberately do NOT store owner identity here. Vehicles are
identified by plate only. Linking a plate to a person requires
a government API we don't have access to — so we don't pretend to.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plate_number = Column(String(20), nullable=False, unique=True, index=True)
    state_code   = Column(String(10), nullable=True)   # e.g. "UK", "DL", "MH"
    flag_count   = Column(Integer,    nullable=False, default=0)
    flag_reasons = Column(Text,       nullable=True)   # comma-separated complaint categories
    first_seen   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
