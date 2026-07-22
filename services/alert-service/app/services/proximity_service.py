"""
Proximity service — finds users within alert radius using Haversine.

How user locations are tracked:
  - Users call PUT /api/v1/alerts/location when app opens (client-side)
  - Location stored in user_locations table
  - Locations older than 2 hours are excluded (stale location problem)
  - Users who haven't shared location are skipped — no forced tracking

Blueprint edge case 4.4:
  "User location not available for proximity check → skip that user"
  Handled here by only querying users with recent locations.

Privacy note:
  user_locations is NEVER exposed via API. The table is write-only
  from the user's perspective. Only the alert broadcaster reads it,
  and only during active alert processing.
"""
import math
import logging
from datetime import datetime, timezone, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.alert import UserLocation

logger = logging.getLogger("alert-service.proximity")

LOCATION_STALENESS_HOURS = 2


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def find_users_in_radius(
    lat: float,
    lng: float,
    radius_km: float,
    db: Session,
    exclude_user_id: str = None,
) -> list[str]:
    """
    Returns list of user_id strings for users within radius_km of (lat, lng).
    Only includes users with location updated in the last 2 hours.
    Excludes the alert triggerer (exclude_user_id).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOCATION_STALENESS_HOURS)

    # Load all recent locations — for scale, use PostGIS or bounding box pre-filter
    # At our expected scale (<10k concurrent users) this is fine
    locations = (db.query(UserLocation)
                 .filter(UserLocation.updated_at >= cutoff)
                 .all())

    nearby = []
    for loc in locations:
        user_id_str = str(loc.user_id)
        if exclude_user_id and user_id_str == exclude_user_id:
            continue
        dist = haversine_km(lat, lng, loc.lat, loc.lng)
        if dist <= radius_km:
            nearby.append(user_id_str)

    logger.info(f"Found {len(nearby)} users within {radius_km}km of ({lat}, {lng})")
    return nearby
