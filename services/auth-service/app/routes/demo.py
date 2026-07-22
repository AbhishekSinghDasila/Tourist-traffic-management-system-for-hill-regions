"""
Temporary demo routes to prove RBAC is wired correctly end-to-end.
These get deleted once the real complaint-service exists in week 5 —
they exist purely so we can test role enforcement right now without
waiting for other services to be built.
"""
from fastapi import APIRouter, Depends

from app.core.deps import require_role
from app.models.user import User

router = APIRouter(prefix="/api/v1/demo", tags=["demo - remove before week 5"])


@router.get("/police-only")
def police_only_route(current_user: User = Depends(require_role("police", "admin"))):
    return {"message": f"Welcome officer {current_user.name}, station {current_user.station_id}"}


@router.get("/admin-only")
def admin_only_route(current_user: User = Depends(require_role("admin"))):
    return {"message": f"Welcome admin {current_user.name}. Full access granted."}
