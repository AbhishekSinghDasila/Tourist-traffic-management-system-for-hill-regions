"""
Train the XGBoost crowd prediction model and save artifacts.

Run this ONCE after the ml-service container starts:
  docker compose -f docker-compose.dev.yml exec ml-service python -m scripts.train_model

Training takes ~30 seconds on CPU.
After training, the model is available at /app/model_artifacts/.
The service loads it automatically on startup.

Output:
  model_artifacts/xgboost_crowd_model.joblib
  model_artifacts/label_encoders.joblib
  model_artifacts/feature_names.joblib
"""
import sys
import logging

sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from app.services.predictor import train_and_save_model, predictor

if __name__ == "__main__":
    print("=== DevBhumi ML Service: Training crowd prediction model ===")
    print("Training on 10,000 synthetic samples...")

    metrics = train_and_save_model(n_samples=10000)

    print("\n=== Training Complete ===")
    print(f"  MAE : {metrics['mae']} vehicles (avg prediction error)")
    print(f"  R²  : {metrics['r2']} (1.0 = perfect, >0.85 = good)")
    print(f"  Train samples : {metrics['train_samples']}")
    print(f"  Test samples  : {metrics['test_samples']}")

    # Verify it loads correctly
    print("\nVerifying model loads correctly...")
    ok = predictor.load()
    if ok:
        # Quick smoke test
        result = predictor.predict(
            district="nainital",
            month=5,          # May — peak season
            day_of_week=6,    # Sunday
            is_weekend=1,
            is_holiday=0,
            is_peak_season=1,
            is_monsoon=0,
            weather_score=9.0,
        )
        print(f"\nSmoke test — Nainital, May Sunday:")
        print(f"  Predicted vehicles : {result['predicted_vehicles']}")
        print(f"  Capacity           : {result['capacity']}")
        print(f"  Capacity %         : {result['capacity_pct']}%")
        print(f"  Risk level         : {result['risk_level']}")
        print("\nModel is ready. The API endpoints are now live.")
    else:
        print("ERROR: Model failed to load after training.")
        sys.exit(1)
