import os
from urllib.parse import urlsplit

os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", "/tmp/test-public.pem")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")

from app.services.storage_service import generate_presigned_url, _get_s3_client
from app.core.config import settings


def test_presigned_url_uses_browser_endpoint_without_changing_upload_endpoint(monkeypatch):
    monkeypatch.setattr(settings, "S3_ENDPOINT_URL", "http://minio:9000")
    monkeypatch.setattr(settings, "S3_PUBLIC_ENDPOINT_URL", "https://media.example.test")
    assert _get_s3_client().meta.endpoint_url == "http://minio:9000"
    url = generate_presigned_url("complaints/test/image.jpg")
    assert urlsplit(url).netloc == "media.example.test"
    assert "complaints/test/image.jpg" in urlsplit(url).path
    assert urlsplit(url).query
