"""
Complaint and ComplaintMedia models.

PRIVACY ARCHITECTURE (from blueprint section 2.6):
- user_id is stored here as a FK — but the police-facing API endpoint
  uses ComplaintPoliceView schema which structurally EXCLUDES user_id.
- Only admin role can call the endpoint that returns full complaint
  with user identity, and every such call is logged in audit_logs.
- complaint_media stores the S3 URL — police only see OCR-extracted
  plate text, NOT the original image URL.
- Complaints can never be hard-deleted (no DELETE permission for
  complaint_svc DB user) — only soft-archived by admin.

STATUS flow:
  PENDING → ASSIGNED → IN_PROGRESS → RESOLVED | CLOSED
  PENDING_REVIEW (spam/duplicate flag)
  ARCHIVED (admin soft-delete)
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

VALID_STATUSES = (
    "PENDING", "ASSIGNED", "IN_PROGRESS",
    "RESOLVED", "CLOSED", "PENDING_REVIEW", "ARCHIVED"
)

COMPLAINT_CATEGORIES = (
    "NOISE_POLLUTION", "LITTERING", "DRUNK_DRIVING",
    "ILLEGAL_PARKING", "RASH_DRIVING", "DRUG_ABUSE",
    "HARASSMENT", "OVERCHARGING", "OTHER"
)


class Complaint(Base):
    __tablename__ = "complaints"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User identity — stored but NEVER exposed to police via API
    user_id           = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Vehicle info — extracted by OCR from uploaded image
    plate_number      = Column(String(20),  nullable=True)   # null if OCR fails
    vehicle_state     = Column(String(10),  nullable=True)   # e.g. "UK", "DL"

    # Incident details
    category          = Column(String(30),  nullable=False, default="OTHER")
    description       = Column(Text,        nullable=True)

    # Location of the incident
    lat               = Column(Float,       nullable=False)
    lng               = Column(Float,       nullable=False)
    district          = Column(String(80),  nullable=True, index=True)

    # Routing
    assigned_station_id = Column(UUID(as_uuid=True),
                                 ForeignKey("police_stations.id"), nullable=True)
    status            = Column(String(20),  nullable=False, default="PENDING", index=True)

    # Spam detection — same plate complained 3+ times in 24h
    flag_reason       = Column(String(200), nullable=True)

    created_at        = Column(DateTime(timezone=True),
                               default=lambda: datetime.now(timezone.utc), index=True)
    updated_at        = Column(DateTime(timezone=True),
                               default=lambda: datetime.now(timezone.utc),
                               onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    media             = relationship("ComplaintMedia", back_populates="complaint",
                                     cascade="all, delete-orphan")
    station           = relationship("PoliceStation", foreign_keys=[assigned_station_id])


class ComplaintMedia(Base):
    __tablename__ = "complaint_media"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complaint_id  = Column(UUID(as_uuid=True), ForeignKey("complaints.id"), nullable=False)

    # S3 presigned URL — short-lived, admin only
    # Police NEVER receive this URL — only the ocr_plate_text below
    s3_key        = Column(String(500), nullable=False)   # S3 object key (not full URL)
    media_type    = Column(String(20),  nullable=False, default="image/jpeg")
    file_size     = Column(Integer,     nullable=True)

    # OCR result — what police see instead of the raw image
    ocr_plate_text = Column(String(50), nullable=True)   # e.g. "UK07BC1234"
    ocr_confidence = Column(Float,      nullable=True)   # 0.0-1.0

    uploaded_at   = Column(DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc))

    complaint     = relationship("Complaint", back_populates="media")
