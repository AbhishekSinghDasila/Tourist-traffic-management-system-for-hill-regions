from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, field_validator


class CheckpointPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    district: str
    state: str
    lat: float
    lng: float
    is_active: bool


class VehicleCreate(BaseModel):
    plate_number: str
    state_code: Optional[str] = None

    @field_validator("plate_number")
    @classmethod
    def normalise_plate(cls, v: str) -> str:
        return v.upper().replace(" ", "")


class VehiclePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    plate_number: str
    state_code: Optional[str]
    flag_count: int


class TrafficEntryCreate(BaseModel):
    plate_number: str
    checkpoint_id: UUID
    direction: str

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        if v.upper() not in ("ENTRY", "EXIT"):
            raise ValueError("direction must be ENTRY or EXIT")
        return v.upper()

    @field_validator("plate_number")
    @classmethod
    def normalise_plate(cls, v: str) -> str:
        return v.upper().replace(" ", "")


class TrafficEntryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    direction: str
    status: str
    recorded_at: datetime


class DistrictDensity(BaseModel):
    district: str
    active_vehicles: int
    capacity: int
    percentage: float
    risk_level: str
    cached: bool
    as_of: datetime


class DensityListResponse(BaseModel):
    districts: list[DistrictDensity]
    total_active_vehicles: int
