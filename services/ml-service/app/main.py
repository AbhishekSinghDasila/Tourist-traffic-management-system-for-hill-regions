import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger import jsonlogger

from app.core.config import settings
from app.routes.predict import router
from app.services.predictor import predictor

logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    "%(asctime)s %(levelname)s %(name)s %(message)s",
    rename_fields={"asctime": "timestamp", "levelname": "level", "name": "service"},
)
logHandler.setFormatter(formatter)
logging.basicConfig(level=settings.LOG_LEVEL, handlers=[logHandler])
logger = logging.getLogger("ml-service")

app = FastAPI(
    title="DevBhumi ML Service",
    version="1.0.0",
    description="XGBoost crowd prediction for Uttarakhand and HP tourist districts.",
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
    return {
        "status": "ok",
        "service": "ml-service",
        "model_ready": predictor.is_ready,
    }


@app.on_event("startup")
def on_startup():
    # Try to load existing model on startup
    # If not found, service starts but predictions return 503
    # until the training script is run
    loaded = predictor.load()
    logger.info(
        "ml-service starting up",
        extra={
            "environment": settings.ENVIRONMENT,
            "model_loaded": loaded,
            "model_path": settings.model_path,
        }
    )
    if not loaded:
        logger.warning(
            "Model artifacts not found. Run: "
            "docker compose exec ml-service python -m scripts.train_model"
        )
