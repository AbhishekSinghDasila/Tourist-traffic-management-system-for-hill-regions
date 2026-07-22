"""
ComplaintService — orchestrates the full complaint submission flow:

1. Validate image (magic bytes, size)
2. Upload to S3
3. Run OCR on image to extract plate number
4. Spam check (same plate 3+ times in 24h)
5. Find nearest police station (Haversine)
6. Create complaint record in DB
7. Create media record in DB
8. Publish complaint.created Kafka event (graceful degradation)
9. Return complaint ID to user

If S3 upload fails → DB insert is skipped → 503 returned to user.
If Kafka fails → complaint is still saved → warning logged.
This ordering ensures we never have a complaint in DB without media.
"""
import logging
import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.complaint import Complaint, ComplaintMedia
from app.models.audit_log import AuditLog
from app.repositories.complaint_repository import IComplaintRepository
from app.services.ocr_service import extract_plate
from app.services.storage_service import upload_complaint_image
from app.services.station_finder import find_nearest_station
from app.services.kafka_publisher import publish_complaint_created

logger = logging.getLogger("complaint-service.service")

SPAM_THRESHOLD = 3   # same plate, 3+ complaints in 24h → PENDING_REVIEW


class ComplaintService:

    def __init__(self, repo: IComplaintRepository, db: Session):
        self.repo = repo
        self.db = db

    def submit_complaint(
        self,
        user_id: UUID,
        category: str,
        description: Optional[str],
        lat: float,
        lng: float,
        district: Optional[str],
        image_bytes: bytes,
    ) -> Complaint:
        """
        Full complaint submission flow.
        Raises ValueError for invalid input.
        Raises RuntimeError if S3 upload fails (complaint not saved).
        """
        complaint_id = uuid.uuid4()

        # ── Step 1: Upload image to S3 ────────────────────
        # Done BEFORE DB insert — if S3 fails we don't create orphan complaints
        s3_key, media_type, file_size = upload_complaint_image(
            image_bytes, str(complaint_id)
        )

        # ── Step 2: OCR plate extraction ──────────────────
        plate_number, ocr_confidence = extract_plate(
            image_bytes,
            use_ocr=settings.USE_OCR
        )

        # Derive state code from plate (first 2 chars of valid Indian plate)
        vehicle_state = None
        if plate_number and len(plate_number) >= 2:
            vehicle_state = plate_number[:2]

        # ── Step 3: Spam check ────────────────────────────
        status = "PENDING"
        flag_reason = None
        if plate_number:
            recent_count = self.repo.count_recent_by_plate(plate_number)
            if recent_count >= SPAM_THRESHOLD:
                status = "PENDING_REVIEW"
                flag_reason = f"Plate {plate_number} complained {recent_count + 1} times in 24h"
                logger.warning(f"Spam flag: {flag_reason}")

        # ── Step 4: Find nearest station ──────────────────
        station = find_nearest_station(lat, lng, self.db, district)
        if not station:
            logger.warning(f"No police station found for lat={lat}, lng={lng}, district={district}")

        # ── Step 5: Create complaint in DB ────────────────
        complaint = Complaint(
            id=complaint_id,
            user_id=user_id,
            plate_number=plate_number,
            vehicle_state=vehicle_state,
            category=category,
            description=description,
            lat=lat,
            lng=lng,
            district=district,
            assigned_station_id=station.id if station else None,
            status=status,
            flag_reason=flag_reason,
        )
        saved_complaint = self.repo.create(complaint)

        # ── Step 6: Save media record ─────────────────────
        media = ComplaintMedia(
            complaint_id=saved_complaint.id,
            s3_key=s3_key,
            media_type=media_type,
            file_size=file_size,
            ocr_plate_text=plate_number,
            ocr_confidence=ocr_confidence,
        )
        self.repo.add_media(media)

        # ── Step 7: Publish Kafka event ───────────────────
        publish_complaint_created(
            complaint_id=saved_complaint.id,
            station_id=station.id if station else None,
            district=district,
            category=category,
            plate_number=plate_number,
            lat=lat,
            lng=lng,
            kafka_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        )

        logger.info(
            f"Complaint {saved_complaint.id} created: "
            f"plate={plate_number}, station={station.name if station else 'unassigned'}, "
            f"status={status}"
        )
        return saved_complaint

    def write_audit_log(
        self,
        actor_id: UUID,
        actor_role: str,
        action: str,
        target_type: str,
        target_id: str,
        detail: Optional[str] = None,
    ) -> None:
        """Write an audit log entry. Called before every admin identity access."""
        log = AuditLog(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
        )
        self.db.add(log)
        self.db.commit()
