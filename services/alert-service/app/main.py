import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger import jsonlogger

from app.core.config import settings
from app.routes.alert import router

logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    "%(asctime)s %(levelname)s %(name)s %(message)s",
    rename_fields={"asctime": "timestamp", "levelname": "level", "name": "service"},
)
logHandler.setFormatter(formatter)
logging.basicConfig(level=settings.LOG_LEVEL, handlers=[logHandler])
logger = logging.getLogger("alert-service")

app = FastAPI(
    title="DevBhumi Emergency Alert Service",
    version="1.0.0",
    description="Real-time emergency alert broadcasting for ambulance corridor and disaster alerts.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "alert-service"}


@app.on_event("startup")
def on_startup():
    logger.info("alert-service starting up",
                extra={"environment": settings.ENVIRONMENT,
                       "fcm_enabled": settings.USE_FCM,
                       "alert_radius_km": settings.ALERT_RADIUS_KM})
