"""
TrafficDensityService — the core business logic layer.

This is where Redis caching is applied. The pattern for every read:
  1. Check Redis cache
  2. Cache hit → return cached value (mark cached=True in response)
  3. Cache miss → query DB, populate cache, return value

Cache invalidation:
  - TTL-based (60 seconds) for tourist counts — acceptable staleness
  - Never cache emergency alert data or complaint data

District capacity thresholds (determines risk colour on map):
  GREEN  < 60%  — normal, no action needed
  AMBER  60-85% — busy, tourists should consider alternatives
  RED    > 85%  — near capacity, strong advisory to divert
"""
import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.redis_client import redis_client
from app.models.checkpoint import Checkpoint
from app.repositories.interfaces import ICheckpointRepository, ITrafficEntryRepository
from app.schemas.traffic import DistrictDensity, DensityListResponse

# District vehicle capacity — how many vehicles the district can handle comfortably.
# These are estimates; in production they'd come from the checkpoints table.
DISTRICT_CAPACITIES = {
    "nainital":    5000,
    "mussoorie":   4000,
    "ranikhet":    2000,
    "almora":      2500,
    "kedarnath":   3000,
    "badrinath":   3000,
    "haridwar":    8000,
    "rishikesh":   6000,
    "shimla":      6000,
    "manali":      5000,
    "dharamsala":  4000,
    "default":     3000,
}


def _risk_level(percentage: float) -> str:
    if percentage >= 85:
        return "RED"
    if percentage >= 60:
        return "AMBER"
    return "GREEN"


def _cache_key_district(district: str) -> str:
    return f"tourist_count:{district.lower()}"


def _cache_key_all() -> str:
    return "tourist_count:all_districts"


class TrafficDensityService:

    def __init__(
        self,
        checkpoint_repo: ICheckpointRepository,
        entry_repo: ITrafficEntryRepository,
    ):
        self.checkpoint_repo = checkpoint_repo
        self.entry_repo = entry_repo

    def get_district_density(self, district: str) -> DistrictDensity:
        """
        Single district density. Checks Redis first.
        Cache miss → DB query → populate cache.
        """
        district = district.lower()
        cache_key = _cache_key_district(district)
        now = datetime.now(timezone.utc)
        capacity = DISTRICT_CAPACITIES.get(district, DISTRICT_CAPACITIES["default"])

        # ── Cache check ───────────────────────────────────
        cached_val = redis_client.get(cache_key)
        if cached_val is not None:
            active = int(cached_val)
            pct = min(100.0, round((active / capacity) * 100, 1))
            return DistrictDensity(
                district=district,
                active_vehicles=active,
                capacity=capacity,
                percentage=pct,
                risk_level=_risk_level(pct),
                cached=True,
                as_of=now,
            )

        # ── Cache miss → DB ───────────────────────────────
        active = self.entry_repo.count_active_by_district(district)
        redis_client.setex(cache_key, settings.TOURIST_COUNT_CACHE_TTL, str(active))

        pct = min(100.0, round((active / capacity) * 100, 1))
        return DistrictDensity(
            district=district,
            active_vehicles=active,
            capacity=capacity,
            percentage=pct,
            risk_level=_risk_level(pct),
            cached=False,
            as_of=now,
        )

    def get_all_districts_density(self) -> DensityListResponse:
        """
        All districts in one response — for the map overview.
        Uses a single DB query (count_active_all_districts) instead of
        N queries, then caches each district individually.
        """
        now = datetime.now(timezone.utc)

        # Try to build from individual district caches first
        checkpoints = self.checkpoint_repo.get_all_active()
        districts = list({cp.district for cp in checkpoints})

        densities = []
        districts_needing_db = []

        for district in districts:
            cached_val = redis_client.get(_cache_key_district(district))
            if cached_val is not None:
                active = int(cached_val)
                capacity = DISTRICT_CAPACITIES.get(district, DISTRICT_CAPACITIES["default"])
                pct = min(100.0, round((active / capacity) * 100, 1))
                densities.append(DistrictDensity(
                    district=district,
                    active_vehicles=active,
                    capacity=capacity,
                    percentage=pct,
                    risk_level=_risk_level(pct),
                    cached=True,
                    as_of=now,
                ))
            else:
                districts_needing_db.append(district)

        # Single DB query for all cache-miss districts
        if districts_needing_db:
            all_counts = self.entry_repo.count_active_all_districts()
            for district in districts_needing_db:
                active = all_counts.get(district, 0)
                redis_client.setex(
                    _cache_key_district(district),
                    settings.TOURIST_COUNT_CACHE_TTL,
                    str(active)
                )
                capacity = DISTRICT_CAPACITIES.get(district, DISTRICT_CAPACITIES["default"])
                pct = min(100.0, round((active / capacity) * 100, 1))
                densities.append(DistrictDensity(
                    district=district,
                    active_vehicles=active,
                    capacity=capacity,
                    percentage=pct,
                    risk_level=_risk_level(pct),
                    cached=False,
                    as_of=now,
                ))

        densities.sort(key=lambda d: d.percentage, reverse=True)
        total = sum(d.active_vehicles for d in densities)
        return DensityListResponse(districts=densities, total_active_vehicles=total)

    def record_entry(
        self,
        plate_number: str,
        checkpoint_id,
        direction: str,
        state_code: Optional[str],
        vehicle_repo,
        entry_repo,
    ) -> None:
        """
        Record a vehicle passing through a checkpoint.
        After writing, invalidate the district's cache so the next
        read reflects the updated count immediately.
        """
        vehicle = vehicle_repo.upsert(plate_number, state_code)
        checkpoint = self.checkpoint_repo.get_by_id(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        entry_repo.create(vehicle.id, checkpoint.id, direction)

        # Invalidate cache for this district — next read will hit DB
        redis_client.delete(_cache_key_district(checkpoint.district))
