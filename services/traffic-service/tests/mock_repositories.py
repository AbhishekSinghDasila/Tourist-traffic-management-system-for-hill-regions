"""
In-memory mock implementations of the three repository interfaces.
Used exclusively in tests — zero database, zero network.

This proves the Liskov Substitution principle: the service layer
works identically whether it receives PostgresXxxRepository or
MockXxxRepository. The tests don't know or care which one they get.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from app.models.checkpoint import Checkpoint
from app.models.vehicle import Vehicle
from app.models.traffic_entry import TrafficEntry, STATUS_ACTIVE, STATUS_TIMED_OUT, DIRECTION_ENTRY, DIRECTION_EXIT
from app.repositories.interfaces import ICheckpointRepository, IVehicleRepository, ITrafficEntryRepository


class MockCheckpointRepository(ICheckpointRepository):

    def __init__(self, checkpoints: list[Checkpoint] = None):
        self._store: dict[UUID, Checkpoint] = {}
        for cp in (checkpoints or []):
            self._store[cp.id] = cp

    def get_by_id(self, checkpoint_id: UUID) -> Optional[Checkpoint]:
        return self._store.get(checkpoint_id)

    def get_by_district(self, district: str) -> list[Checkpoint]:
        return [cp for cp in self._store.values()
                if cp.district == district.lower() and cp.is_active]

    def get_all_active(self) -> list[Checkpoint]:
        return [cp for cp in self._store.values() if cp.is_active]

    def seed(self, checkpoint: Checkpoint) -> None:
        self._store[checkpoint.id] = checkpoint


class MockVehicleRepository(IVehicleRepository):

    def __init__(self):
        self._store: dict[str, Vehicle] = {}

    def get_by_plate(self, plate_number: str) -> Optional[Vehicle]:
        return self._store.get(plate_number.upper())

    def upsert(self, plate_number: str, state_code: Optional[str] = None) -> Vehicle:
        plate = plate_number.upper()
        now = datetime.now(timezone.utc)
        if plate in self._store:
            self._store[plate].last_seen = now
            return self._store[plate]
        vehicle = Vehicle(
            id=uuid4(),
            plate_number=plate,
            state_code=state_code,
            flag_count=0,
            first_seen=now,
            last_seen=now,
        )
        self._store[plate] = vehicle
        return vehicle

    def increment_flag(self, plate_number: str, reason: str) -> Vehicle:
        vehicle = self.upsert(plate_number, None)
        vehicle.flag_count += 1
        existing = vehicle.flag_reasons or ""
        vehicle.flag_reasons = f"{existing},{reason}".strip(",")
        return vehicle


class MockTrafficEntryRepository(ITrafficEntryRepository):

    def __init__(self):
        self._entries: list[TrafficEntry] = []

    def create(self, vehicle_id: UUID, checkpoint_id: UUID, direction: str) -> TrafficEntry:
        entry = TrafficEntry(
            id=uuid4(),
            vehicle_id=vehicle_id,
            checkpoint_id=checkpoint_id,
            direction=direction.upper(),
            status=STATUS_ACTIVE,
            recorded_at=datetime.now(timezone.utc),
        )
        self._entries.append(entry)
        return entry

    def count_active_by_district(self, district: str) -> int:
        # Mirrors count_active_all_districts but scoped to one district.
        # Requires set_checkpoint_district_map() to have been called in
        # test setup, same as count_active_all_districts.
        return self.count_active_all_districts().get(district.lower(), 0)

    def count_active_all_districts(self) -> dict[str, int]:
        # Build district→net_count from stored entries + checkpoint district
        # Entries store checkpoint_id — we need the district from checkpoint.
        # In tests, we pre-build this mapping through the helper below.
        counts: dict[str, int] = {}
        for entry in self._entries:
            if entry.status != STATUS_ACTIVE:
                continue
            district = self._checkpoint_district_map.get(entry.checkpoint_id, "unknown")
            delta = 1 if entry.direction == DIRECTION_ENTRY else -1
            counts[district] = max(0, counts.get(district, 0) + delta)
        return counts

    def mark_timed_out(self, older_than_hours: int = 18) -> int:
        # Mirrors PostgresTrafficEntryRepository.mark_timed_out: only
        # entries with no later matching EXIT for the same vehicle are
        # timed out. A vehicle that entered and later exited normally
        # (even after `older_than_hours`) must keep its ENTRY ACTIVE,
        # otherwise the district count would be undercounted.
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        count = 0
        for entry in self._entries:
            if not (entry.direction == DIRECTION_ENTRY
                    and entry.status == STATUS_ACTIVE
                    and entry.recorded_at < cutoff):
                continue
            has_later_exit = any(
                other.vehicle_id == entry.vehicle_id
                and other.direction == DIRECTION_EXIT
                and other.recorded_at > entry.recorded_at
                for other in self._entries
            )
            if not has_later_exit:
                entry.status = STATUS_TIMED_OUT
                count += 1
        return count

    def set_checkpoint_district_map(self, mapping: dict[UUID, str]) -> None:
        """Call this in test setup so count_active_all_districts works."""
        self._checkpoint_district_map = mapping

    @property
    def _checkpoint_district_map(self) -> dict[UUID, str]:
        return getattr(self, "_cdmap", {})

    @_checkpoint_district_map.setter
    def _checkpoint_district_map(self, val):
        self._cdmap = val
