from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Path where trained model artifacts are saved/loaded
    MODEL_DIR: str = "/app/model_artifacts"

    # Model training config
    RANDOM_SEED: int = 42
    TEST_SIZE: float = 0.2
    N_ESTIMATORS: int = 200
    MAX_DEPTH: int = 6
    LEARNING_RATE: float = 0.1

    @property
    def model_path(self) -> str:
        return f"{self.MODEL_DIR}/xgboost_crowd_model.joblib"

    @property
    def encoder_path(self) -> str:
        return f"{self.MODEL_DIR}/label_encoders.joblib"

    @property
    def feature_names_path(self) -> str:
        return f"{self.MODEL_DIR}/feature_names.joblib"


settings = Settings()
