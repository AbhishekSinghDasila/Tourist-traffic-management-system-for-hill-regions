from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, field_validator
from app.models.alert import ALERT_TYPES


class AlertCreate(BaseModel):
    alert_type: str = "AMBULANCE"
    description: Optional[str] = None
    lat: float
    lng: float
    district: Optional[str] = None
    radius_km: float = 2.0

    @field_validator("alert_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        v = v.upper()
        return v if v in ALERT_TYPES else "OTHER"

    @field_validator("radius_km")
    @classmethod
    def validate_radius(cls, v: float) -> float:
        # Cap radius at 10km — beyond that, broadcast is too wide
        return min(max(v, 0.5), 10.0)


class AlertPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    alert_type: str
    description: Optional[str]
    lat: float
    lng: float
    district: Optional[str]
    radius_km: float
    status: str
    recipients_notified: int
    created_at: datetime


class AlertCancelRequest(BaseModel):
    reason: Optional[str] = None


class LocationUpdate(BaseModel):
    lat: float
    lng: float
    district: Optional[str] = None
