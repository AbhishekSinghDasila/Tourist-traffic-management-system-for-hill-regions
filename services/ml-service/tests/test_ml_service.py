"""
Unit tests for ML service.
Tests data generation logic and prediction schema — no trained model needed.
"""
import os, sys
sys.path.insert(0, ".")
os.environ.setdefault("MODEL_DIR", "/tmp/test_models")

import pytest
import pandas as pd
from datetime import date

from app.services.data_generator import (
    generate_training_data, is_holiday, is_peak_season,
    is_monsoon, weather_score, DISTRICTS
)


# ── Data generator tests ──────────────────────────────────
def test_generate_returns_correct_row_count():
    df = generate_training_data(n_samples=100)
    assert len(df) == 100


def test_generated_data_has_required_columns():
    df = generate_training_data(n_samples=50)
    required = ["district", "month", "day_of_week", "is_weekend",
                "is_holiday", "is_peak_season", "is_monsoon",
                "weather_score", "crowd_count", "capacity"]
    for col in required:
        assert col in df.columns, f"Missing column: {col}"


def test_crowd_count_never_negative():
    df = generate_training_data(n_samples=500)
    assert (df["crowd_count"] >= 0).all()


def test_all_districts_appear_in_data():
    df = generate_training_data(n_samples=2000)
    generated_districts = set(df["district"].unique())
    for d in DISTRICTS:
        assert d in generated_districts, f"District {d} never appeared"


def test_monsoon_months_have_lower_average_crowd():
    df = generate_training_data(n_samples=5000)
    monsoon = df[df["is_monsoon"] == 1]["crowd_count"].mean()
    non_monsoon = df[df["is_monsoon"] == 0]["crowd_count"].mean()
    assert monsoon < non_monsoon, "Monsoon should have lower crowds than non-monsoon"


def test_weekends_have_higher_average_crowd():
    df = generate_training_data(n_samples=5000)
    weekends = df[df["is_weekend"] == 1]["crowd_count"].mean()
    weekdays = df[df["is_weekend"] == 0]["crowd_count"].mean()
    assert weekends > weekdays, "Weekends should have higher crowds than weekdays"


# ── Feature engineering tests ─────────────────────────────
def test_is_holiday_republic_day():
    assert is_holiday(1, 26) == 1


def test_is_holiday_normal_day():
    assert is_holiday(3, 10) == 0


def test_peak_season_april():
    assert is_peak_season(4) == 1


def test_peak_season_july_is_monsoon_not_peak():
    assert is_peak_season(7) == 0
    assert is_monsoon(7) == 1


def test_monsoon_august():
    assert is_monsoon(8) == 1


def test_monsoon_october_is_not_monsoon():
    assert is_monsoon(10) == 0


def test_weather_score_in_range():
    for month in range(1, 13):
        score = weather_score(month)
        assert 0 <= score <= 12, f"Score {score} out of expected range for month {month}"


# ── Schema tests ──────────────────────────────────────────
def test_prediction_request_clamps_weather():
    from app.schemas.prediction import PredictionRequest
    req = PredictionRequest(district="nainital", weather_score=15.0)
    assert req.weather_score == 10.0

    req2 = PredictionRequest(district="nainital", weather_score=-5.0)
    assert req2.weather_score == 0.0


def test_districts_dict_has_all_expected_districts():
    expected = ["nainital", "mussoorie", "haridwar", "rishikesh",
                "ranikhet", "almora", "kedarnath", "shimla", "manali"]
    for d in expected:
        assert d in DISTRICTS, f"{d} missing from DISTRICTS"
