"""
Alert service routes.

POST  /api/v1/alerts                  emergency_team/police/admin — trigger alert
GET   /api/v1/alerts                  any authenticated — list active alerts
GET   /api/v1/alerts/history          police/admin — alert history
GET   /api/v1/alerts/{id}             any authenticated — single alert
PATCH /api/v1/alerts/{id}/cancel      admin only — cancel false alarm
POST  /api/v1/alerts/location         any authenticated — update own location
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role, TokenUser
from app.models.alert import EmergencyAlert
from app.schemas.alert import AlertCreate, AlertPublic, LocationUpdate, AlertCancelRequest
from app.services.alert_service import dispatch_alert, cancel_alert, update_user_location

router = APIRouter(prefix="/api/v1/alerts", tags=["emergency alerts"])


@router.post("", response_model=AlertPublic, status_code=status.HTTP_201_CREATED)
def trigger_alert(
    payload: AlertCreate,
    db: Session = Depends(get_db),
    current_user: TokenUser = Depends(
        require_role("emergency_team", "police", "admin")
    ),
):
    """
    Trigger an emergency alert.
    Finds all users within radius_km and sends push notifications.
    Also notifies the district police station.
    This is the star feature — ambulance stuck in traffic scenario.
    """
    alert = dispatch_alert(
        triggered_by=current_user.user_id,
        triggered_role=current_user.role,
        alert_type=payload.alert_type,
        description=payload.description,
        lat=payload.lat,
        lng=payload.lng,
        district=payload.district or current_user.district,
        radius_km=payload.radius_km,
        db=db,
    )
    return alert


@router.get("", response_model=list[AlertPublic])
def get_active_alerts(
    district: str = None,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: TokenUser = Depends(get_current_user),
):
    """Active alerts. Tourists/citizens see this — it's public safety information."""
    query = db.query(EmergencyAlert).filter(EmergencyAlert.status == "ACTIVE")
    if district:
        query = query.filter(EmergencyAlert.district == district.lower())
    return query.order_by(EmergencyAlert.created_at.desc()).limit(limit).all()


@router.get("/history", response_model=list[AlertPublic])
def get_alert_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: TokenUser = Depends(require_role("police", "admin")),
):
    """Alert history — police and admin only."""
    return (db.query(EmergencyAlert)
            .order_by(EmergencyAlert.created_at.desc())
            .limit(limit)
            .all())


@router.get("/{alert_id}", response_model=AlertPublic)
def get_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: TokenUser = Depends(get_current_user),
):
    alert = db.query(EmergencyAlert).filter(EmergencyAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "ALERT_NOT_FOUND", "message": "Alert not found"},
        )
    return alert


@router.patch("/{alert_id}/cancel", response_model=AlertPublic)
def cancel_alert_route(
    alert_id: UUID,
    payload: AlertCancelRequest,
    db: Session = Depends(get_db),
    current_user: TokenUser = Depends(require_role("admin")),
):
    """
    Cancel a false alarm. Admin only.
    Sends cancellation push to all previously-notified users.
    """
    alert = cancel_alert(alert_id, current_user.user_id, payload.reason, db)
    if not alert:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "ALERT_NOT_FOUND_OR_NOT_ACTIVE",
                    "message": "Alert not found or already resolved/cancelled"},
        )
    return alert


@router.post("/location", status_code=status.HTTP_204_NO_CONTENT)
def update_location(
    payload: LocationUpdate,
    db: Session = Depends(get_db),
    current_user: TokenUser = Depends(get_current_user),
):
    """
    Update the authenticated user's location.
    Stored in Redis (1hr TTL) + Postgres.
    Used for proximity check during alert dispatch.
    """
    update_user_location(
        user_id=current_user.user_id,
        lat=payload.lat,
        lng=payload.lng,
        district=payload.district or current_user.district,
        db=db,
    )
