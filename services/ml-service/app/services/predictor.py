"""
XGBoost crowd prediction model trainer.

Architecture decision: Strategy pattern.
BasePredictor defines the interface. XGBoostPredictor implements it.
Adding a new model (LSTM, RandomForest) = new class, zero route changes.

Model is trained on synthetic data, saved to disk with joblib,
and loaded at service startup. This means:
- No retraining on every container restart (fast startup)
- Model can be retrained offline and the artifact replaced
- Multiple services can read the same model artifact

Features → crowd_count mapping:
  district (encoded) + temporal features + weather → crowd vehicles
  
Then crowd_count / district_capacity * 100 = capacity_percentage
And capacity_percentage → risk_level (GREEN/AMBER/RED)
"""
import logging
import os
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, r2_score
from xgboost import XGBRegressor

from app.core.config import settings
from app.services.data_generator import generate_training_data, DISTRICTS

logger = logging.getLogger("ml-service.trainer")

FEATURE_COLUMNS = [
    "district_encoded",
    "month",
    "day_of_week",
    "is_weekend",
    "is_holiday",
    "is_peak_season",
    "is_monsoon",
    "weather_score",
]


def train_and_save_model(n_samples: int = 10000) -> dict:
    """
    Trains the XGBoost model on synthetic data and saves artifacts to disk.
    Returns training metrics.
    Called once during initial setup (scripts/train_model.py).
    """
    logger.info(f"Generating {n_samples} synthetic training samples...")
    df = generate_training_data(n_samples, seed=settings.RANDOM_SEED)

    # Encode district (categorical → numeric)
    le = LabelEncoder()
    df["district_encoded"] = le.fit_transform(df["district"])

    X = df[FEATURE_COLUMNS]
    y = df["crowd_count"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=settings.TEST_SIZE,
        random_state=settings.RANDOM_SEED
    )

    logger.info("Training XGBoost model...")
    model = XGBRegressor(
        n_estimators=settings.N_ESTIMATORS,
        max_depth=settings.MAX_DEPTH,
        learning_rate=settings.LEARNING_RATE,
        random_state=settings.RANDOM_SEED,
        tree_method="hist",   # fast CPU training
        verbosity=0,
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2  = r2_score(y_test, y_pred)

    logger.info(f"Model trained. MAE={mae:.1f} vehicles, R²={r2:.3f}")

    # Save artifacts
    os.makedirs(settings.MODEL_DIR, exist_ok=True)
    joblib.dump(model, settings.model_path)
    joblib.dump(le, settings.encoder_path)
    joblib.dump(FEATURE_COLUMNS, settings.feature_names_path)

    logger.info(f"Artifacts saved to {settings.MODEL_DIR}")
    return {
        "mae": round(mae, 1),
        "r2": round(r2, 3),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
    }


class XGBoostPredictor:
    """
    Loads the saved XGBoost model and serves predictions.
    Instantiated once at app startup — not per request.
    """

    def __init__(self):
        self._model: Optional[XGBRegressor] = None
        self._encoder: Optional[LabelEncoder] = None
        self._ready = False

    def load(self) -> bool:
        """Load model artifacts from disk. Returns True if successful."""
        try:
            if not os.path.exists(settings.model_path):
                logger.warning(f"Model not found at {settings.model_path}. Run train script first.")
                return False

            self._model   = joblib.load(settings.model_path)
            self._encoder = joblib.load(settings.encoder_path)
            self._ready   = True
            logger.info("XGBoost model loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    @property
    def is_ready(self) -> bool:
        return self._ready

    def predict(
        self,
        district: str,
        month: int,
        day_of_week: int,
        is_weekend: int,
        is_holiday: int,
        is_peak_season: int,
        is_monsoon: int,
        weather_score: float,
    ) -> dict:
        """
        Returns crowd prediction for a district on given conditions.
        Raises RuntimeError if model not loaded.
        """
        if not self._ready:
            raise RuntimeError("Model not loaded. Run the training script first.")

        # Encode district
        try:
            district_encoded = self._encoder.transform([district.lower()])[0]
        except ValueError:
            # Unknown district — use mean encoding
            district_encoded = len(self._encoder.classes_) // 2
            logger.warning(f"Unknown district '{district}', using default encoding")

        features = pd.DataFrame([{
            "district_encoded": district_encoded,
            "month":            month,
            "day_of_week":      day_of_week,
            "is_weekend":       is_weekend,
            "is_holiday":       is_holiday,
            "is_peak_season":   is_peak_season,
            "is_monsoon":       is_monsoon,
            "weather_score":    weather_score,
        }])

        predicted_count = max(0, int(self._model.predict(features)[0]))

        # Calculate capacity percentage
        capacity = DISTRICTS.get(district.lower(), 3000)
        pct = min(100.0, round((predicted_count / capacity) * 100, 1))

        # Risk level
        if pct >= 85:
            risk = "RED"
        elif pct >= 60:
            risk = "AMBER"
        else:
            risk = "GREEN"

        return {
            "district":         district.lower(),
            "predicted_vehicles": predicted_count,
            "capacity":         capacity,
            "capacity_pct":     pct,
            "risk_level":       risk,
        }


# Singleton — one instance per service process
predictor = XGBoostPredictor()
