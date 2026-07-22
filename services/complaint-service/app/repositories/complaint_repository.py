"""
Complaint repository — interface + Postgres implementation.

Key design: get_for_police() and get_full() are separate methods
returning different data shapes. This enforces the privacy model
at the data access layer, not just the API layer.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.complaint import Complaint, ComplaintMedia


# ── Interface ─────────────────────────────────────────────
class IComplaintRepository(ABC):

    @abstractmethod
    def create(self, complaint: Complaint) -> Complaint: ...

    @abstractmethod
    def add_media(self, media: ComplaintMedia) -> ComplaintMedia: ...

    @abstractmethod
    def get_by_id(self, complaint_id: UUID) -> Optional[Complaint]: ...

    @abstractmethod
    def get_for_police(self, station_id: UUID, limit: int, offset: int) -> list[Complaint]:
        """Returns complaints assigned to a specific station. No user_id filtering needed
        in query — privacy enforced by schema (ComplaintPoliceView has no user_id field)."""
        ...

    @abstractmethod
    def get_by_user(self, user_id: UUID, limit: int, offset: int) -> list[Complaint]:
        """Citizen viewing their own complaints."""
        ...

    @abstractmethod
    def get_full_for_admin(self, complaint_id: UUID) -> Optional[Complaint]:
        """Admin-only: returns full complaint including user_id. Caller must write audit log."""
        ...

    @abstractmethod
    def update_status(self, complaint_id: UUID, status: str, updated_by: UUID) -> Optional[Complaint]: ...

    @abstractmethod
    def count_recent_by_plate(self, plate_number: str, hours: int = 24) -> int:
        """Used for spam detection: same plate complained N times in 24h."""
        ...


# ── Postgres implementation ───────────────────────────────
class PostgresComplaintRepository(IComplaintRepository):

    def __init__(self, db: Session):
        self.db = db

    def create(self, complaint: Complaint) -> Complaint:
        self.db.add(complaint)
        self.db.commit()
        self.db.refresh(complaint)
        return complaint

    def add_media(self, media: ComplaintMedia) -> ComplaintMedia:
        self.db.add(media)
        self.db.commit()
        self.db.refresh(media)
        return media

    def get_by_id(self, complaint_id: UUID) -> Optional[Complaint]:
        return (self.db.query(Complaint)
                .options(joinedload(Complaint.media))
                .filter(Complaint.id == complaint_id)
                .first())

    def get_for_police(self, station_id: UUID, limit: int = 20, offset: int = 0) -> list[Complaint]:
        """
        Police see complaints routed to their station.
        Row-level isolation: station_id comes from the officer's JWT,
        NOT from a user-supplied query parameter.
        """
        return (self.db.query(Complaint)
                .options(joinedload(Complaint.media))
                .filter(Complaint.assigned_station_id == station_id)
                .filter(Complaint.status != "ARCHIVED")
                .order_by(Complaint.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all())

    def get_by_user(self, user_id: UUID, limit: int = 20, offset: int = 0) -> list[Complaint]:
        return (self.db.query(Complaint)
                .filter(Complaint.user_id == user_id)
                .order_by(Complaint.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all())

    def get_full_for_admin(self, complaint_id: UUID) -> Optional[Complaint]:
        """Admin only — returns full object. Caller MUST write audit log."""
        return (self.db.query(Complaint)
                .options(joinedload(Complaint.media))
                .filter(Complaint.id == complaint_id)
                .first())

    def update_status(self, complaint_id: UUID, status: str, updated_by: UUID) -> Optional[Complaint]:
        complaint = self.db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if complaint:
            complaint.status = status
            complaint.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(complaint)
        return complaint

    def count_recent_by_plate(self, plate_number: str, hours: int = 24) -> int:
        """Spam check: how many complaints for this plate in the last N hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return (self.db.query(Complaint)
                .filter(Complaint.plate_number == plate_number)
                .filter(Complaint.created_at >= cutoff)
                .count())
