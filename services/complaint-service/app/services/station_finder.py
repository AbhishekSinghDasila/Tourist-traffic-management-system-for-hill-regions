"""
Station finder — routes complaints to the nearest police station.

Uses Haversine formula to calculate great-circle distance between
complaint GPS coordinates and each police station.

Edge case from blueprint 4.2:
  "Police station mapping fails (no station near location)"
  → Returns None, complaint gets assigned to district admin account.
  This is handled in complaint_service.py.

Why not PostGIS?
  PostGIS would be ideal for production but adds significant setup
  complexity. Haversine in Python is accurate enough for our scale
  (< 10,000 stations) and keeps the service self-contained.
"""
import math
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.police_station import PoliceStation

logger = logging.getLogger("complaint-service.station_finder")


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Returns distance in kilometres between two GPS coordinates.
    Haversine formula — accurate to within 0.5% for distances under 1000km.
    """
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def find_nearest_station(
    lat: float,
    lng: float,
    db: Session,
    district: Optional[str] = None,
) -> Optional[PoliceStation]:
    """
    Finds the nearest active police station to the given coordinates.

    If district is provided, searches within that district first.
    Falls back to all stations if no district match found.
    Returns None if no stations exist at all.
    """
    # Try district-scoped search first (faster, more relevant)
    if district:
        stations = (db.query(PoliceStation)
                    .filter(PoliceStation.district == district.lower())
                    .filter(PoliceStation.is_active == True)  # noqa: E712
                    .all())
        if stations:
            return _nearest(lat, lng, stations)

    # Fall back to all active stations
    all_stations = db.query(PoliceStation).filter(PoliceStation.is_active == True).all()  # noqa: E712
    if not all_stations:
        logger.warning(f"No active police stations found for lat={lat}, lng={lng}")
        return None

    return _nearest(lat, lng, all_stations)


def _nearest(lat: float, lng: float, stations: list[PoliceStation]) -> PoliceStation:
    return min(stations, key=lambda s: _haversine_km(lat, lng, s.lat, s.lng))
