"""
PoliceStation — used to route complaints to the nearest station.

In production, police officers' accounts have a station_id that maps
to a row in this table. Complaints are assigned to the nearest station
using Haversine distance from the complaint's GPS location.
"""
import uuid
from sqlalchemy import Column, String, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class PoliceStation(Base):
    __tablename__ = "police_stations"

    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name     = Column(String(120), nullable=False)
    district = Column(String(80),  nullable=False, index=True)
    state    = Column(String(80),  nullable=False)
    lat      = Column(Float,       nullable=False)
    lng      = Column(Float,       nullable=False)
    phone    = Column(String(20),  nullable=True)
    is_active = Column(Boolean,    nullable=False, default=True)
