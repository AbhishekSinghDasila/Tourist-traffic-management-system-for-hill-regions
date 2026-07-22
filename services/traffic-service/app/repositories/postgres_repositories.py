"""
Postgres implementations of the traffic repository interfaces.

All queries use the ORM (parameterised). No raw string-formatted SQL.
Each class only touches the tables it owns — checkpoint_svc DB user
will only have permissions on checkpoints, vehicles, traffic_entries.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.models.checkpoint import Checkpoint
from app.models.vehicle import Vehicle
from app.models.traffic_entry import TrafficEntry, DIRECTION_ENTRY, DIRECTION_EXIT, STATUS_ACTIVE, STATUS_TIMED_OUT
from app.repositories.interfaces import ICheckpointRepository, IVehicleRepository, ITrafficEntryRepository


# ── Checkpoint ────────────────────────────────────────────
class PostgresCheckpointRepository(ICheckpointRepository):

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, checkpoint_id: UUID) -> Optional[Checkpoint]:
        return self.db.query(Checkpoint).filter(Checkpoint.id == checkpoint_id).first()

    def get_by_district(self, district: str) -> list[Checkpoint]:
        return (self.db.query(Checkpoint)
                .filter(Checkpoint.district == district.lower())
                .filter(Checkpoint.is_active == True)  # noqa: E712
                .all())

    def get_all_active(self) -> list[Checkpoint]:
        return self.db.query(Checkpoint).filter(Checkpoint.is_active == True).all()  # noqa: E712


# ── Vehicle ───────────────────────────────────────────────
class PostgresVehicleRepository(IVehicleRepository):

    def __init__(self, db: Session):
        self.db = db

    def get_by_plate(self, plate_number: str) -> Optional[Vehicle]:
        return self.db.query(Vehicle).filter(
            Vehicle.plate_number == plate_number.upper()
        ).first()

    def upsert(self, plate_number: str, state_code: Optional[str] = None) -> Vehicle:
        plate = plate_number.upper()
        vehicle = self.get_by_plate(plate)
        now = datetime.now(timezone.utc)

        if vehicle:
            vehicle.last_seen = now
            self.db.commit()
            self.db.refresh(vehicle)
            return vehicle

        vehicle = Vehicle(
            plate_number=plate,
            state_code=state_code.upper() if state_code else None,
            first_seen=now,
            last_seen=now,
        )
        self.db.add(vehicle)
        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle

    def increment_flag(self, plate_number: str, reason: str) -> Vehicle:
        vehicle = self.get_by_plate(plate_number)
        if not vehicle:
            vehicle = self.upsert(plate_number, None)

        vehicle.flag_count += 1
        existing = vehicle.flag_reasons or ""
        vehicle.flag_reasons = f"{existing},{reason}".strip(",")
        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle


# ── TrafficEntry ──────────────────────────────────────────
class PostgresTrafficEntryRepository(ITrafficEntryRepository):

    def __init__(self, db: Session):
        self.db = db

    def create(self, vehicle_id: UUID, checkpoint_id: UUID, direction: str) -> TrafficEntry:
        entry = TrafficEntry(
            vehicle_id=vehicle_id,
            checkpoint_id=checkpoint_id,
            direction=direction.upper(),
            status=STATUS_ACTIVE,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def count_active_by_district(self, district: str) -> int:
        """
        Counts active vehicles in a district.
        Joins traffic_entries → checkpoints to filter by district.
        Formula: entries - exits (both with status=ACTIVE).
        Floor at 0 — handles the edge case where exit arrives before
        entry is processed (race condition or data gap).
        """
        result = (
            self.db.query(
                func.sum(
                    case(
                        (TrafficEntry.direction == DIRECTION_ENTRY, 1),
                        (TrafficEntry.direction == DIRECTION_EXIT, -1),
                        else_=0
                    )
                ).label("net_count")
            )
            .join(Checkpoint, TrafficEntry.checkpoint_id == Checkpoint.id)
            .filter(Checkpoint.district == district.lower())
            .filter(TrafficEntry.status == STATUS_ACTIVE)
            .scalar()
        )
        return max(0, result or 0)

    def count_active_all_districts(self) -> dict[str, int]:
        """
        Single query for all districts — used for the map overview endpoint.
        Much more efficient than calling count_active_by_district() N times.
        """
        rows = (
            self.db.query(
                Checkpoint.district,
                func.sum(
                    case(
                        (TrafficEntry.direction == DIRECTION_ENTRY, 1),
                        (TrafficEntry.direction == DIRECTION_EXIT, -1),
                        else_=0
                    )
                ).label("net_count")
            )
            .join(Checkpoint, TrafficEntry.checkpoint_id == Checkpoint.id)
            .filter(TrafficEntry.status == STATUS_ACTIVE)
            .group_by(Checkpoint.district)
            .all()
        )
        return {row.district: max(0, row.net_count or 0) for row in rows}

    def mark_timed_out(self, older_than_hours: int = 18) -> int:
        """
        Blueprint edge case 4.3: vehicles that entered but never exited.
        Marks their ENTRY records as TIMED_OUT after 18 hours.
        Called by the scheduler every 6 hours.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        updated = (
            self.db.query(TrafficEntry)
            .filter(TrafficEntry.direction == DIRECTION_ENTRY)
            .filter(TrafficEntry.status == STATUS_ACTIVE)
            .filter(TrafficEntry.recorded_at < cutoff)
            .all()
        )
        count = len(updated)
        for entry in updated:
            entry.status = STATUS_TIMED_OUT
        self.db.commit()
        return count
