"""
ML service routes.

GET  /api/v1/predict/crowd/{district}     predict crowd for a district today
POST /api/v1/predict/crowd                predict with custom date/weather
GET  /api/v1/predict/crowd/all            predict all districts (map overlay)
GET  /api/v1/predict/model/info           model metadata and feature names
POST /api/v1/predict/model/train          retrain model (admin-level, no auth for now)
"""
from datetime import datetime, timezone, date
import calendar

from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.schemas.prediction import (
    PredictionRequest, PredictionResponse,
    BatchPredictionResponse, ModelInfoResponse,
)
from app.services.predictor import predictor
from app.services.data_generator import (
    DISTRICTS, is_holiday, is_peak_season, is_monsoon, weather_score
)

router = APIRouter(prefix="/api/v1/predict", tags=["crowd prediction"])


def _features_from_date(target_date: date, weather: float) -> dict:
    """Extract all model features from a date."""
    dow = target_date.weekday()   # 0=Monday, 6=Sunday
    # Clamp to [0, 10] — the range the model was trained on. The POST schema
    # already clamps via its validator, but the GET query-param endpoints
    # below don't go through that schema, so clamp here too.
    weather = max(0.0, min(10.0, weather))
    return {
        "month":          target_date.month,
        "day_of_week":    dow,
        "is_weekend":     1 if dow >= 5 else 0,
        "is_holiday":     is_holiday(target_date.month, target_date.day),
        "is_peak_season": is_peak_season(target_date.month),
        "is_monsoon":     is_monsoon(target_date.month),
        "weather_score":  round(weather, 2),
    }


def _make_prediction(district: str, target_date: date, weather: float) -> PredictionResponse:
    features = _features_from_date(target_date, weather)
    result = predictor.predict(district=district, **features)

    return PredictionResponse(
        district=result["district"],
        target_date=target_date,
        predicted_vehicles=result["predicted_vehicles"],
        capacity=result["capacity"],
        capacity_pct=result["capacity_pct"],
        risk_level=result["risk_level"],
        features_used=features,
        predicted_at=datetime.now(timezone.utc),
    )


@router.get("/crowd/all", response_model=BatchPredictionResponse)
def predict_all_districts(weather: float = 7.0):
    """
    Predict crowd for ALL districts today.
    Powers the risk overlay on the traffic map.
    Returns RED districts separately for map highlighting.
    """
    if not predictor.is_ready:
        raise HTTPException(status_code=503, detail={"error_code": "MODEL_NOT_READY"})

    today = datetime.now(timezone.utc).date()
    predictions = []
    high_risk = []

    for district in DISTRICTS.keys():
        pred = _make_prediction(district, today, weather)
        predictions.append(pred)
        if pred.risk_level == "RED":
            high_risk.append(district)

    # Sort by capacity_pct descending — highest risk first
    predictions.sort(key=lambda p: p.capacity_pct, reverse=True)

    return BatchPredictionResponse(
        predictions=predictions,
        total_districts=len(predictions),
        high_risk_districts=high_risk,
    )


# NOTE: this route must stay registered AFTER "/crowd/all" — FastAPI/Starlette
# matches routes in registration order, and "/crowd/{district}" would
# otherwise swallow requests to "/crowd/all" (matching district="all") and
# 404 them before this dedicated route ever gets a chance to run.
@router.get("/crowd/{district}", response_model=PredictionResponse)
def predict_district_today(district: str, weather: float = 7.0):
    """
    Predict crowd for a district today.
    Public endpoint — tourists call this to decide whether to visit.
    weather param is 0-10; caller can pass real weather API value.
    """
    if not predictor.is_ready:
        raise HTTPException(
            status_code=503,
            detail={"error_code": "MODEL_NOT_READY",
                    "message": "ML model not loaded. Run the training script first."}
        )
    if district.lower() not in DISTRICTS:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "DISTRICT_NOT_FOUND",
                    "message": f"District '{district}' not supported. Available: {list(DISTRICTS.keys())}"}
        )

    today = datetime.now(timezone.utc).date()
    return _make_prediction(district.lower(), today, weather)


@router.post("/crowd", response_model=PredictionResponse)
def predict_custom(payload: PredictionRequest):
    """
    Predict crowd with custom date and weather.
    Tourists use this to plan future trips: 'What will Nainital be like next Sunday?'
    """
    if not predictor.is_ready:
        raise HTTPException(status_code=503, detail={"error_code": "MODEL_NOT_READY"})

    if payload.district.lower() not in DISTRICTS:
        raise HTTPException(status_code=404, detail={"error_code": "DISTRICT_NOT_FOUND"})

    target_date = payload.target_date or datetime.now(timezone.utc).date()
    return _make_prediction(payload.district.lower(), target_date, payload.weather_score)


@router.get("/model/info", response_model=ModelInfoResponse)
def get_model_info():
    """Model metadata — useful for debugging and interviews."""
    from app.services.predictor import FEATURE_COLUMNS
    return ModelInfoResponse(
        model_type="XGBoostRegressor",
        is_ready=predictor.is_ready,
        features=FEATURE_COLUMNS,
        districts_supported=list(DISTRICTS.keys()),
        training_info={
            "n_estimators": 200,
            "max_depth": 6,
            "learning_rate": 0.1,
            "training_samples": 8000,
            "test_samples": 2000,
        }
    )


@router.post("/model/train", status_code=202)
def retrain_model(background_tasks: BackgroundTasks):
    """
    Retrain the model in the background.
    Returns immediately with 202 Accepted — training runs async.
    In production this would be protected by admin role.
    """
    def _train():
        from app.services.predictor import train_and_save_model
        metrics = train_and_save_model()
        predictor.load()   # reload after training
        import logging
        logging.getLogger("ml-service").info(f"Model retrained: {metrics}")

    background_tasks.add_task(_train)
    return {"message": "Model training started in background. Call /model/info to check status."}
