"""
Repository interfaces for the traffic service.

Three repositories, one per aggregate:
- ICheckpointRepository  — read checkpoints (mostly static data)
- IVehicleRepository     — upsert vehicles by plate number
- ITrafficEntryRepository — write entries, count active vehicles per district

Routes and services depend only on these interfaces.
Tests use in-memory implementations. Prod uses Postgres implementations.
"""
from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from app.models.checkpoint import Checkpoint
from app.models.vehicle import Vehicle
from app.models.traffic_entry import TrafficEntry


class ICheckpointRepository(ABC):

    @abstractmethod
    def get_by_id(self, checkpoint_id: UUID) -> Optional[Checkpoint]: ...

    @abstractmethod
    def get_by_district(self, district: str) -> list[Checkpoint]: ...

    @abstractmethod
    def get_all_active(self) -> list[Checkpoint]: ...


class IVehicleRepository(ABC):

    @abstractmethod
    def get_by_plate(self, plate_number: str) -> Optional[Vehicle]: ...

    @abstractmethod
    def upsert(self, plate_number: str, state_code: Optional[str]) -> Vehicle:
        """Get existing vehicle or create new one. Updates last_seen timestamp."""
        ...

    @abstractmethod
    def increment_flag(self, plate_number: str, reason: str) -> Vehicle: ...


class ITrafficEntryRepository(ABC):

    @abstractmethod
    def create(self, vehicle_id: UUID, checkpoint_id: UUID, direction: str) -> TrafficEntry: ...

    @abstractmethod
    def count_active_by_district(self, district: str) -> int:
        """
        Returns current active tourist vehicle count for a district.
        Formula: ENTRY records - EXIT records where status=ACTIVE.
        This is the core number that drives the density map.
        """
        ...

    @abstractmethod
    def count_active_all_districts(self) -> dict[str, int]:
        """Returns {district: active_count} for all districts. Used for map overview."""
        ...

    @abstractmethod
    def mark_timed_out(self, older_than_hours: int = 18) -> int:
        """
        Scheduled job target. Marks ACTIVE entries with no matching EXIT
        after `older_than_hours` as TIMED_OUT so they don't inflate counts.
        Returns number of records updated.
        """
        ...
