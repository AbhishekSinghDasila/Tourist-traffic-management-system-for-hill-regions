from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str
    REDIS_URL: str
    JWT_PUBLIC_KEY_PATH: str
    JWT_ALGORITHM: str = "RS256"
    JWT_ISSUER: str = "devbhumi-auth-service"
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    ALERT_RADIUS_KM: float = 2.0
    USE_FCM: bool = False
    FCM_CREDENTIALS_PATH: str = ""

    @property
    def jwt_public_key(self) -> str:
        return Path(self.JWT_PUBLIC_KEY_PATH).read_text()


settings = Settings()
