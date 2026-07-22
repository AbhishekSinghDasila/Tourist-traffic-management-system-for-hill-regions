from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, field_validator


class PredictionRequest(BaseModel):
    district: str
    target_date: Optional[date] = None    # defaults to today if not provided
    weather_score: float = 7.0            # 0-10, caller can pass weather API value

    @field_validator("weather_score")
    @classmethod
    def clamp_weather(cls, v: float) -> float:
        return max(0.0, min(10.0, v))


class PredictionResponse(BaseModel):
    district: str
    target_date: date
    predicted_vehicles: int
    capacity: int
    capacity_pct: float
    risk_level: str                        # GREEN | AMBER | RED
    features_used: dict                    # shows interviewer exactly what went into model
    model_version: str = "xgboost-v1"
    predicted_at: datetime


class BatchPredictionResponse(BaseModel):
    predictions: list[PredictionResponse]
    total_districts: int
    high_risk_districts: list[str]         # RED districts — useful for map overlay


class ModelInfoResponse(BaseModel):
    model_type: str
    is_ready: bool
    features: list[str]
    districts_supported: list[str]
    training_info: dict
