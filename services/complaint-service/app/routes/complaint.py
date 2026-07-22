"""
Complaint service routes.

POST /api/v1/complaints                   citizen/police/admin — submit complaint
GET  /api/v1/complaints/mine              citizen — own complaints only
GET  /api/v1/complaints/station           police — complaints at their station
GET  /api/v1/complaints/{id}/admin        admin — full view + audit log
PATCH /api/v1/complaints/{id}/status      police/admin — update status
GET  /api/v1/complaints/{id}/image-url    admin — generate presigned S3 URL
"""
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role, TokenUser
from app.repositories.complaint_repository import PostgresComplaintRepository
from app.schemas.complaint import (
    ComplaintPublic, ComplaintPoliceView, ComplaintAdminView, StatusUpdate
)
from app.services.complaint_service import ComplaintService
from app.services.storage_service import generate_presigned_url
from app.core.config import settings

router = APIRouter(prefix="/api/v1/complaints", tags=["complaints"])


def _get_service(db: Session) -> ComplaintService:
    return ComplaintService(
        repo=PostgresComplaintRepository(db),
        db=db,
    )


@router.post("", response_model=ComplaintPublic, status_code=status.HTTP_201_CREATED)
async def submit_complaint(
    image: UploadFile = File(..., description="Photo of the vehicle/incident"),
    category: str = Form(default="OTHER"),
    description: str = Form(default=None),
    lat: float = Form(...),
    lng: float = Form(...),
    district: str = Form(default=None),
    db: Session = Depends(get_db),
    current_user: TokenUser = Depends(
        require_role("citizen", "police", "admin", "emergency_team")
    ),
):
    """
    Submit a complaint with an image.
    Image is validated by magic bytes (not Content-Type).
    OCR extracts plate number from image automatically.
    Complaint is routed to nearest police station.
    Complainant identity is NEVER sent to police.
    """
    image_bytes = await image.read()

    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "EMPTY_FILE", "message": "Image file is empty"},
        )

    svc = _get_service(db)
    try:
        complaint = svc.submit_complaint(
            user_id=UUID(current_user.user_id),
            category=category,
            description=description,
            lat=lat,
            lng=lng,
            district=district,
            image_bytes=image_bytes,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "INVALID_IMAGE", "message": str(e)},
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail={"error_code": "UPLOAD_FAILED", "message": str(e)},
        )

    return complaint


@router.get("/mine", response_model=list[ComplaintPublic])
def get_my_complaints(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: TokenUser = Depends(
        require_role("citizen", "police", "admin", "emergency_team")
    ),
):
    """Citizen views their own complaint history. Paginated."""
    repo = PostgresComplaintRepository(db)
    return repo.get_by_user(UUID(current_user.user_id), limit, offset)


@router.get("/station", response_model=list[ComplaintPoliceView])
def get_station_complaints(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: TokenUser = Depends(require_role("police", "admin")),
):
    """
    Police view complaints routed to their station.
    station_id comes from JWT — NOT from query params.
    Response uses ComplaintPoliceView: no user_id, no image URL.
    """
    from app.models.police_station import PoliceStation

    # Get station for this officer from their district in JWT
    if not current_user.district:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "NO_DISTRICT", "message": "Officer account has no district assigned"},
        )

    station = (db.query(PoliceStation)
               .filter(PoliceStation.district == current_user.district)
               .filter(PoliceStation.is_active == True)  # noqa: E712
               .first())

    if not station:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "STATION_NOT_FOUND",
                    "message": f"No police station found for district: {current_user.district}"},
        )

    repo = PostgresComplaintRepository(db)
    return repo.get_for_police(station.id, limit, offset)


@router.get("/{complaint_id}/admin", response_model=ComplaintAdminView)
def get_complaint_full(
    complaint_id: UUID,
    db: Session = Depends(get_db),
    current_user: TokenUser = Depends(require_role("admin")),
):
    """
    Admin-only: returns full complaint including user_id.
    EVERY call to this endpoint writes an audit log record.
    This makes it impossible to silently access complainant identity.
    """
    repo = PostgresComplaintRepository(db)
    svc = ComplaintService(repo=repo, db=db)

    complaint = repo.get_full_for_admin(complaint_id)
    if not complaint:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "COMPLAINT_NOT_FOUND", "message": "Complaint not found"},
        )

    # Mandatory audit log — every identity access is recorded
    svc.write_audit_log(
        actor_id=UUID(current_user.user_id),
        actor_role=current_user.role,
        action="VIEW_COMPLAINT_IDENTITY",
        target_type="complaint",
        target_id=str(complaint_id),
    )

    return complaint


@router.patch("/{complaint_id}/status", response_model=ComplaintPublic)
def update_complaint_status(
    complaint_id: UUID,
    payload: StatusUpdate,
    db: Session = Depends(get_db),
    current_user: TokenUser = Depends(require_role("police", "admin")),
):
    """Police or admin updates complaint status."""
    repo = PostgresComplaintRepository(db)
    updated = repo.update_status(complaint_id, payload.status, UUID(current_user.user_id))
    if not updated:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "COMPLAINT_NOT_FOUND", "message": "Complaint not found"},
        )
    return updated


@router.get("/{complaint_id}/image-url")
def get_image_url(
    complaint_id: UUID,
    db: Session = Depends(get_db),
    current_user: TokenUser = Depends(require_role("admin")),
):
    """
    Admin-only: generates a 5-minute presigned S3 URL for the complaint image.
    Writes audit log. Police NEVER access this endpoint.
    """
    repo = PostgresComplaintRepository(db)
    svc = ComplaintService(repo=repo, db=db)

    complaint = repo.get_by_id(complaint_id)
    if not complaint or not complaint.media:
        raise HTTPException(status_code=404, detail={"error_code": "NOT_FOUND"})

    svc.write_audit_log(
        actor_id=UUID(current_user.user_id),
        actor_role=current_user.role,
        action="VIEW_COMPLAINT_IMAGE",
        target_type="complaint",
        target_id=str(complaint_id),
    )

    urls = []
    for media in complaint.media:
        try:
            url = generate_presigned_url(media.s3_key)
            urls.append({"media_id": str(media.id), "url": url, "expires_in": 300})
        except RuntimeError:
            urls.append({"media_id": str(media.id), "url": None, "error": "URL generation failed"})

    return {"complaint_id": str(complaint_id), "images": urls}
