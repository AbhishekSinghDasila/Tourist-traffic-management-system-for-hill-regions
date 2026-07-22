"""
Three separate complaint response schemas — privacy enforced by structure.

The key design: police CANNOT receive user identity because
ComplaintPoliceView structurally has no user_id field.
It's not filtered at runtime — it's impossible by type.

ComplaintCreate     → citizen submitting a complaint (input)
ComplaintPoliceView → what police see (no user_id, no image URL)
ComplaintAdminView  → what admin sees (everything, triggers audit log)
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, field_validator

from app.models.complaint import COMPLAINT_CATEGORIES, VALID_STATUSES


# ── Input schema ──────────────────────────────────────────
class ComplaintCreate(BaseModel):
    category: str = "OTHER"
    description: Optional[str] = None
    lat: float
    lng: float
    district: Optional[str] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        v = v.upper()
        if v not in COMPLAINT_CATEGORIES:
            return "OTHER"
        return v

    @field_validator("lat")
    @classmethod
    def validate_lat(cls, v: float) -> float:
        if not (-90 <= v <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator("lng")
    @classmethod
    def validate_lng(cls, v: float) -> float:
        if not (-180 <= v <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        return v


# ── Media views ───────────────────────────────────────────
class MediaPoliceView(BaseModel):
    """Police see OCR text only — never the image URL."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    ocr_plate_text: Optional[str]
    ocr_confidence: Optional[float]
    media_type: str


class MediaAdminView(BaseModel):
    """Admin sees everything including S3 key to generate presigned URL."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    s3_key: str
    ocr_plate_text: Optional[str]
    ocr_confidence: Optional[float]
    media_type: str
    file_size: Optional[int]
    uploaded_at: datetime


# ── Complaint views ───────────────────────────────────────
class ComplaintPoliceView(BaseModel):
    """
    Police response — structurally cannot contain user_id.
    No user_id field means FastAPI cannot accidentally include it
    even if the DB model has it.
    """
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    plate_number: Optional[str]
    vehicle_state: Optional[str]
    category: str
    description: Optional[str]
    lat: float
    lng: float
    district: Optional[str]
    status: str
    created_at: datetime
    media: list[MediaPoliceView] = []


class ComplaintAdminView(BaseModel):
    """
    Admin response — includes user_id.
    Accessing this endpoint writes an AuditLog record.
    """
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID             # ← only admin sees this
    plate_number: Optional[str]
    vehicle_state: Optional[str]
    category: str
    description: Optional[str]
    lat: float
    lng: float
    district: Optional[str]
    assigned_station_id: Optional[UUID]
    status: str
    flag_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
    media: list[MediaAdminView] = []


class ComplaintPublic(BaseModel):
    """Minimal response returned immediately after submission."""
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: str
    category: str
    created_at: datetime


class StatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        v = v.upper()
        if v not in VALID_STATUSES:
            raise ValueError(f"Status must be one of: {VALID_STATUSES}")
        return v
