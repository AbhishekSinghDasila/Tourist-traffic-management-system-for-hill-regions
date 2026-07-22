"""
Synthetic training data generator for crowd prediction.

Why synthetic data?
  We don't have years of real toll plaza / hotel occupancy data.
  But we DO know the patterns from domain knowledge:
  - Weekends have 40-80% more tourists than weekdays
  - Holidays (Diwali, Holi, summer break) spike crowds 2-3x
  - Monsoon (July-Sept) reduces tourists by 50-70%
  - Peak season is April-June and Oct-Nov
  - Popular districts (Nainital, Mussoorie) saturate faster

This gives XGBoost real signal to learn from, producing a model
that makes sense when you demo it even without real data.

Features used:
  - district (categorical — encoded)
  - day_of_week (0=Mon, 6=Sun)
  - month (1-12)
  - is_weekend (binary)
  - is_holiday (binary — major Indian holidays)
  - is_peak_season (binary — Apr-Jun, Oct-Nov)
  - is_monsoon (binary — Jul-Sep)
  - weather_score (0-10, higher=better weather)

Target:
  - crowd_count (vehicles in the district at noon)
  - derived: capacity_percentage, risk_level
"""
import numpy as np
import pandas as pd

# District base capacities (max comfortable vehicles)
DISTRICTS = {
    "nainital":   5000,
    "mussoorie":  4000,
    "haridwar":   8000,
    "rishikesh":  6000,
    "ranikhet":   2000,
    "almora":     2500,
    "kedarnath":  3000,
    "badrinath":  3000,
    "shimla":     6000,
    "manali":     5000,
    "dharamsala": 4000,
}

# Popularity multiplier — how likely tourists are to visit this district
POPULARITY = {
    "nainital": 1.0, "mussoorie": 0.95, "haridwar": 0.9,
    "rishikesh": 0.85, "shimla": 0.9, "manali": 0.85,
    "dharamsala": 0.7, "almora": 0.5, "ranikhet": 0.45,
    "kedarnath": 0.6, "badrinath": 0.55,
}

# Major Indian holidays (month, day) — approx
HOLIDAYS = {
    (1, 26), (3, 25), (4, 14), (8, 15), (10, 2),
    (10, 24), (11, 1), (11, 12), (12, 25),
}


def is_holiday(month: int, day: int) -> int:
    return 1 if (month, day) in HOLIDAYS else 0


def is_peak_season(month: int) -> int:
    return 1 if month in (4, 5, 6, 10, 11) else 0


def is_monsoon(month: int) -> int:
    return 1 if month in (7, 8, 9) else 0


def weather_score(month: int) -> float:
    """0-10 score: higher = better weather for tourists."""
    scores = {1: 5, 2: 6, 3: 7, 4: 8, 5: 9, 6: 7,
              7: 3, 8: 2, 9: 4, 10: 9, 11: 8, 12: 6}
    return scores.get(month, 5) + np.random.uniform(-1, 1)


def generate_training_data(n_samples: int = 10000, seed: int = 42) -> pd.DataFrame:
    """
    Generates n_samples rows of synthetic training data.
    Each row represents a district on a specific date with a realistic crowd count.
    """
    np.random.seed(seed)
    rows = []

    district_list = list(DISTRICTS.keys())

    for _ in range(n_samples):
        district = np.random.choice(district_list)
        capacity = DISTRICTS[district]
        popularity = POPULARITY[district]

        month = np.random.randint(1, 13)
        day = np.random.randint(1, 29)
        day_of_week = np.random.randint(0, 7)

        is_wknd = 1 if day_of_week >= 5 else 0
        is_hol = is_holiday(month, day)
        is_peak = is_peak_season(month)
        is_mon = is_monsoon(month)
        weather = weather_score(month)

        # Base crowd: 20-40% of capacity on a normal weekday
        base_pct = np.random.uniform(0.20, 0.40)

        # Apply multipliers
        multiplier = 1.0
        multiplier *= popularity
        if is_wknd:
            multiplier *= np.random.uniform(1.4, 1.8)
        if is_hol:
            multiplier *= np.random.uniform(1.8, 2.5)
        if is_peak:
            multiplier *= np.random.uniform(1.3, 1.6)
        if is_mon:
            multiplier *= np.random.uniform(0.3, 0.6)

        # Weather effect
        weather_mult = 0.7 + (weather / 10) * 0.6
        multiplier *= weather_mult

        # Final crowd count with realistic noise
        crowd = int(capacity * base_pct * multiplier * np.random.uniform(0.85, 1.15))
        crowd = max(0, min(crowd, int(capacity * 1.2)))  # allow slight overcapacity

        rows.append({
            "district":      district,
            "month":         month,
            "day_of_week":   day_of_week,
            "is_weekend":    is_wknd,
            "is_holiday":    is_hol,
            "is_peak_season": is_peak,
            "is_monsoon":    is_mon,
            "weather_score": round(weather, 2),
            "crowd_count":   crowd,
            "capacity":      capacity,
        })

    df = pd.DataFrame(rows)
    df["capacity_pct"] = (df["crowd_count"] / df["capacity"] * 100).round(1)
    return df


if __name__ == "__main__":
    df = generate_training_data(10000)
    print(f"Generated {len(df)} rows")
    print(df.describe())
    print("\nSample rows:")
    print(df.sample(5).to_string())
