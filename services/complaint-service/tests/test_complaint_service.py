"""
Unit tests for complaint service.
No DB, no S3, no OCR, no Kafka — all mocked.

Focus: privacy architecture and business logic correctness.
"""
import os, sys
sys.path.insert(0, ".")
os.environ.setdefault("DATABASE_URL",        "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL",           "redis://localhost:6379/0")
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", "/tmp/fake_secrets/pub.pem")
os.environ.setdefault("USE_OCR",             "false")
os.environ.setdefault("AWS_ACCESS_KEY_ID",   "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY","test")

import uuid
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from app.models.complaint import Complaint, ComplaintMedia
from app.repositories.complaint_repository import IComplaintRepository
from app.services.ocr_service import extract_plate, _normalise_plate, PLATE_PATTERN
from app.services.station_finder import _haversine_km


# ── Mock repository ───────────────────────────────────────
class MockComplaintRepository(IComplaintRepository):
    def __init__(self):
        self._complaints: dict[UUID, Complaint] = {}
        self._media: list[ComplaintMedia] = []
        self._plate_counts: dict[str, int] = {}

    def create(self, complaint: Complaint) -> Complaint:
        complaint.created_at = datetime.now(timezone.utc)
        complaint.updated_at = datetime.now(timezone.utc)
        self._complaints[complaint.id] = complaint
        return complaint

    def add_media(self, media: ComplaintMedia) -> ComplaintMedia:
        self._media.append(media)
        return media

    def get_by_id(self, complaint_id: UUID) -> Optional[Complaint]:
        return self._complaints.get(complaint_id)

    def get_for_police(self, station_id: UUID, limit=20, offset=0) -> list[Complaint]:
        return [c for c in self._complaints.values()
                if c.assigned_station_id == station_id]

    def get_by_user(self, user_id: UUID, limit=20, offset=0) -> list[Complaint]:
        return [c for c in self._complaints.values() if c.user_id == user_id]

    def get_full_for_admin(self, complaint_id: UUID) -> Optional[Complaint]:
        return self._complaints.get(complaint_id)

    def update_status(self, complaint_id: UUID, status: str, updated_by: UUID):
        if complaint_id in self._complaints:
            self._complaints[complaint_id].status = status
        return self._complaints.get(complaint_id)

    def count_recent_by_plate(self, plate_number: str, hours: int = 24) -> int:
        return self._plate_counts.get(plate_number, 0)


# ── OCR tests ─────────────────────────────────────────────
def test_plate_normalisation():
    assert _normalise_plate("UK 07 BC 1234") == "UK07BC1234"
    assert _normalise_plate("dl-01-ab-9999") == "DL01AB9999"
    assert _normalise_plate("MH12CD5678") == "MH12CD5678"


def test_plate_pattern_matches_valid_indian_plates():
    assert PLATE_PATTERN.match("UK07BC1234")
    assert PLATE_PATTERN.match("DL01AB9999")
    assert PLATE_PATTERN.match("MH12CD5678")


def test_plate_pattern_rejects_invalid():
    assert not PLATE_PATTERN.match("INVALID")
    assert not PLATE_PATTERN.match("123456")
    assert not PLATE_PATTERN.match("1234567")  # pure digits


def test_extract_plate_returns_none_when_ocr_disabled():
    plate, confidence = extract_plate(b"fake_image_bytes", use_ocr=False)
    assert plate is None
    assert confidence is None


# ── Haversine distance tests ──────────────────────────────
def test_haversine_nainital_to_itself():
    dist = _haversine_km(29.39, 79.45, 29.39, 79.45)
    assert dist == 0.0


def test_haversine_nainital_to_haldwani():
    # Nainital to Haldwani is ~35km
    dist = _haversine_km(29.3919, 79.4542, 29.2167, 79.5167)
    assert 15 < dist < 30


def test_haversine_prefers_closer_station():
    from app.services.station_finder import _nearest
    from app.models.police_station import PoliceStation

    near = PoliceStation()
    near.id = uuid.uuid4()
    near.lat, near.lng = 29.39, 79.45   # close to complaint

    far = PoliceStation()
    far.id = uuid.uuid4()
    far.lat, far.lng = 30.45, 78.06    # Mussoorie — far away

    result = _nearest(29.38, 79.44, [near, far])
    assert result.id == near.id


# ── Spam detection tests ──────────────────────────────────
def test_complaint_flagged_as_pending_review_at_spam_threshold():
    repo = MockComplaintRepository()
    repo._plate_counts["UK07BC1234"] = 3   # already 3 complaints for this plate

    mock_db = MagicMock()

    with patch("app.services.complaint_service.upload_complaint_image",
               return_value=("complaints/test/img.jpg", "image/jpeg", 1024)), \
         patch("app.services.complaint_service.extract_plate",
               return_value=("UK07BC1234", 0.95)), \
         patch("app.services.complaint_service.find_nearest_station",
               return_value=None), \
         patch("app.services.complaint_service.publish_complaint_created",
               return_value=False):

        from app.services.complaint_service import ComplaintService
        svc = ComplaintService(repo=repo, db=mock_db)
        complaint = svc.submit_complaint(
            user_id=uuid.uuid4(),
            category="LITTERING",
            description="Dumping garbage",
            lat=29.39,
            lng=79.45,
            district="nainital",
            image_bytes=b"fake_image",
        )

    assert complaint.status == "PENDING_REVIEW"
    assert "UK07BC1234" in complaint.flag_reason


def test_complaint_pending_when_plate_not_spammed():
    repo = MockComplaintRepository()
    # No previous complaints for this plate
    mock_db = MagicMock()

    with patch("app.services.complaint_service.upload_complaint_image",
               return_value=("complaints/test/img.jpg", "image/jpeg", 1024)), \
         patch("app.services.complaint_service.extract_plate",
               return_value=(None, None)), \
         patch("app.services.complaint_service.find_nearest_station",
               return_value=None), \
         patch("app.services.complaint_service.publish_complaint_created",
               return_value=False):

        from app.services.complaint_service import ComplaintService
        svc = ComplaintService(repo=repo, db=mock_db)
        complaint = svc.submit_complaint(
            user_id=uuid.uuid4(),
            category="NOISE_POLLUTION",
            description="Loud music",
            lat=29.39, lng=79.45, district="nainital",
            image_bytes=b"fake_image",
        )

    assert complaint.status == "PENDING"
    assert complaint.flag_reason is None


def test_user_id_not_in_police_view_schema():
    """
    Structural test: ComplaintPoliceView must not have user_id field.
    This is the core privacy guarantee tested at the type level.
    """
    from app.schemas.complaint import ComplaintPoliceView
    assert "user_id" not in ComplaintPoliceView.model_fields


def test_user_id_in_admin_view_schema():
    """Admin view must have user_id."""
    from app.schemas.complaint import ComplaintAdminView
    assert "user_id" in ComplaintAdminView.model_fields
