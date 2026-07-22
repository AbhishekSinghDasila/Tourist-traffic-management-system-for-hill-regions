"""
TrafficEntry — one record per vehicle passing through a checkpoint.

Direction: ENTRY = vehicle entering the district, EXIT = leaving.
By counting ENTRY records minus EXIT records per district, we get
the current active tourist vehicle count.

Edge case (from blueprint section 4.3): if a vehicle enters but
never exits (breakdown/diversion), a scheduled job marks it
TIMED_OUT after 18 hours so it doesn't inflate the count forever.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

DIRECTION_ENTRY = "ENTRY"
DIRECTION_EXIT  = "EXIT"
STATUS_ACTIVE   = "ACTIVE"
STATUS_TIMED_OUT = "TIMED_OUT"


class TrafficEntry(Base):
    __tablename__ = "traffic_entries"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id    = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False)
    checkpoint_id = Column(UUID(as_uuid=True), ForeignKey("checkpoints.id"), nullable=False)

    direction  = Column(String(10), nullable=False)   # ENTRY | EXIT
    status     = Column(String(20), nullable=False, default=STATUS_ACTIVE)
    recorded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships — for joins in analytics queries
    vehicle    = relationship("Vehicle",    foreign_keys=[vehicle_id])
    checkpoint = relationship("Checkpoint", foreign_keys=[checkpoint_id])

# Composite index — most queries filter by district+direction+status
# This makes the tourist count query fast even with millions of rows
Index("ix_traffic_entries_checkpoint_direction",
      TrafficEntry.checkpoint_id, TrafficEntry.direction, TrafficEntry.status)
