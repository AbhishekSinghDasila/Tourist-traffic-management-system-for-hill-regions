"""
Traffic service routes.

Public endpoints (no auth):
  GET /api/v1/traffic/density             — all districts (map overview)
  GET /api/v1/traffic/density/{district}  — single district

Protected endpoints:
  POST /api/v1/traffic/entry              — record vehicle at checkpoint (police/admin)
  POST /api/v1/traffic/timeout            — trigger cleanup job (admin only)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role, TokenUser
from app.core.redis_client import redis_client
from app.repositories.postgres_repositories import (
    PostgresCheckpointRepository,
    PostgresVehicleRepository,
    PostgresTrafficEntryRepository,
)
from app.schemas.traffic import (
    TrafficEntryCreate, TrafficEntryPublic,
    DistrictDensity, DensityListResponse,
)
from app.services.density_service import TrafficDensityService, _cache_key_district

router = APIRouter(prefix="/api/v1/traffic", tags=["traffic"])


@router.get("/density", response_model=DensityListResponse)
def get_all_density(db: Session = Depends(get_db)):
    """All districts — powers the map. Public, cached 60s in Redis."""
    svc = TrafficDensityService(
        checkpoint_repo=PostgresCheckpointRepository(db),
        entry_repo=PostgresTrafficEntryRepository(db),
    )
    return svc.get_all_districts_density()


@router.get("/density/{district}", response_model=DistrictDensity)
def get_district_density(district: str, db: Session = Depends(get_db)):
    """Single district density. Public, cached 60s in Redis."""
    svc = TrafficDensityService(
        checkpoint_repo=PostgresCheckpointRepository(db),
        entry_repo=PostgresTrafficEntryRepository(db),
    )
    return svc.get_district_density(district)


@router.post("/entry", response_model=TrafficEntryPublic, status_code=status.HTTP_201_CREATED)
def record_vehicle_entry(
    payload: TrafficEntryCreate,
    db: Session = Depends(get_db),
    current_user: TokenUser = Depends(require_role("police", "admin", "emergency_team")),
):
    """
    Record a vehicle passing through a checkpoint.
    Called by the toll simulator script or toll plaza hardware.
    Invalidates the district Redis cache on every write.
    """
    checkpoint_repo = PostgresCheckpointRepository(db)
    vehicle_repo    = PostgresVehicleRepository(db)
    entry_repo      = PostgresTrafficEntryRepository(db)

    checkpoint = checkpoint_repo.get_by_id(payload.checkpoint_id)
    if not checkpoint:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "CHECKPOINT_NOT_FOUND",
                    "message": f"Checkpoint {payload.checkpoint_id} not found"},
        )

    vehicle = vehicle_repo.upsert(payload.plate_number, None)
    entry   = entry_repo.create(vehicle.id, checkpoint.id, payload.direction)

    # Invalidate Redis cache — next density read will reflect this vehicle.
    # Must use the same key format the read path uses (lower-cased district),
    # otherwise a mixed-case district value would leave the stale cache entry
    # in place and the density read would keep serving stale counts.
    redis_client.delete(_cache_key_district(checkpoint.district))

    return entry


@router.post("/timeout", status_code=status.HTTP_200_OK)
def run_timeout_job(
    hours: int = 18,
    db: Session = Depends(get_db),
    current_user: TokenUser = Depends(require_role("admin")),
):
    """Mark vehicles that entered but never exited as TIMED_OUT. Admin only."""
    entry_repo = PostgresTrafficEntryRepository(db)
    count = entry_repo.mark_timed_out(older_than_hours=hours)
    return {"message": f"Marked {count} entries as TIMED_OUT", "updated": count}
