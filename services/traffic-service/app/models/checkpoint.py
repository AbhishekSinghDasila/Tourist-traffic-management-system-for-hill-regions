"""
Checkpoint — represents a toll plaza or entry point into a district.

Every vehicle entry/exit event is recorded against a checkpoint.
The checkpoint's district field is how we aggregate tourist counts
per district for the density map.
"""
import uuid
from sqlalchemy import Column, String, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Checkpoint(Base):
    __tablename__ = "checkpoints"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name       = Column(String(120), nullable=False)        # e.g. "Bhowali Toll Plaza"
    district   = Column(String(80),  nullable=False, index=True)  # e.g. "nainital"
    state      = Column(String(80),  nullable=False, default="uttarakhand")
    lat        = Column(Float,        nullable=False)
    lng        = Column(Float,        nullable=False)
    is_active  = Column(Boolean,      nullable=False, default=True)

    # Maximum tourist vehicles the district can comfortably handle.
    # Used to compute capacity percentage: (active_count / capacity) * 100
    capacity   = Column(String(20),   nullable=False, default="5000")
