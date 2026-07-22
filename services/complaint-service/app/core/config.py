from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str
    REDIS_URL: str

    # JWT — verify only, no private key needed
    JWT_PUBLIC_KEY_PATH: str
    JWT_ALGORITHM: str = "RS256"
    JWT_ISSUER: str = "devbhumi-auth-service"

    # S3 / MinIO object storage for complaint images
    S3_BUCKET_NAME: str = "devbhumi-complaints"
    S3_ENDPOINT_URL: str = ""          # empty = real AWS; set for MinIO local
    AWS_REGION: str = "ap-south-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"

    # Max upload size enforced in service layer (Nginx enforces 10MB at edge)
    MAX_IMAGE_SIZE_BYTES: int = 8 * 1024 * 1024   # 8 MB

    # Police station coordinates for nearest-station routing
    # In production this would be a DB table; for now it's config
    USE_OCR: bool = True   # set False in unit tests to skip EasyOCR model load

    @property
    def jwt_public_key(self) -> str:
        return Path(self.JWT_PUBLIC_KEY_PATH).read_text()


settings = Settings()
