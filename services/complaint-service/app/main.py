import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger import jsonlogger

from app.core.config import settings
from app.routes.complaint import router

logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    "%(asctime)s %(levelname)s %(name)s %(message)s",
    rename_fields={"asctime": "timestamp", "levelname": "level", "name": "service"},
)
logHandler.setFormatter(formatter)
logging.basicConfig(level=settings.LOG_LEVEL, handlers=[logHandler])
logger = logging.getLogger("complaint-service")

app = FastAPI(
    title="DevBhumi Complaint Service",
    version="1.0.0",
    description="Anonymous citizen complaint portal with OCR plate extraction.",
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
    return {"status": "ok", "service": "complaint-service"}


@app.on_event("startup")
def on_startup():
    logger.info("complaint-service starting up",
                extra={"environment": settings.ENVIRONMENT, "ocr_enabled": settings.USE_OCR})
