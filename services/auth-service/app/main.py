"""
Auth service entrypoint.

Structured JSON logging is configured here so every log line is
machine-parseable (timestamp, service name, level, message) — this
matters once you have 5+ services and need to grep logs by request_id
across all of them.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger import jsonlogger

from app.core.config import settings
from app.routes import auth, demo

# ---------- Structured logging setup ----------
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    "%(asctime)s %(levelname)s %(name)s %(message)s",
    rename_fields={"asctime": "timestamp", "levelname": "level", "name": "service"},
)
logHandler.setFormatter(formatter)
logging.basicConfig(level=settings.LOG_LEVEL, handlers=[logHandler])
logger = logging.getLogger("auth-service")

app = FastAPI(
    title="DevBhumi Auth Service",
    version="1.0.0",
    description="Handles registration, login, JWT issuance, and RBAC for the DevBhumi platform.",
)

# CORS — tightened to known frontend origins in production via env var,
# wide open here for local dev only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(demo.router)


@app.get("/health")
def health_check():
    """Used by Docker's HEALTHCHECK directive and by Nginx upstream checks."""
    return {"status": "ok", "service": "auth-service"}


@app.on_event("startup")
def on_startup():
    logger.info("auth-service starting up", extra={"environment": settings.ENVIRONMENT})
