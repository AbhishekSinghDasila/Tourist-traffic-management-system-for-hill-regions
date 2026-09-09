from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.core.config import settings
from app.models.alert import ALERT_TYPES


class AlertCreate(BaseModel):
    alert_type: str = "AMBULANCE"
    description: Optional[str] = None
    lat: float
    lng: float
    district: Optional[str] = None
    # validate_default=True: ensures the 0.5-10km cap below still applies even
    # if ALERT_RADIUS_KM is misconfigured outside that range (pydantic v2
    # skips validators on default values otherwise).
    radius_km: float = Field(default_factory=lambda: settings.ALERT_RADIUS_KM, validate_default=True)

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
