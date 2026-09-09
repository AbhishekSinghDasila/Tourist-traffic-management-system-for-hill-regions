"""
Storage service — uploads complaint images to S3 (or MinIO locally).

Design decisions:
- Images stored by S3 key (not full URL) in the DB
- Presigned URLs generated on-demand with 5-minute expiry
- Police never receive S3 keys or presigned URLs — only OCR text
- Only admin can generate a presigned URL (via protected endpoint)
- File type validated by reading magic bytes, not Content-Type header

Local dev uses MinIO (S3-compatible) via docker-compose.
Production uses real AWS S3.

Edge case from blueprint 4.2:
  "S3 upload fails mid-complaint → roll back DB insert"
  Handled in complaint_service.py by wrapping upload + DB in try/except.
"""
import io
import logging
import uuid
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger("complaint-service.storage")

# Allowed image magic bytes
ALLOWED_MAGIC = {
    b"\xff\xd8\xff": "image/jpeg",    # JPEG
    b"\x89PNG":      "image/png",     # PNG
    b"RIFF":         "image/webp",    # WebP (RIFF container — needs WEBP fourcc check too)
}


def _validate_image_type(data: bytes) -> Optional[str]:
    """
    Validate by magic bytes — not by extension or Content-Type.
    Returns media_type string or None if not a valid image.
    """
    for magic, media_type in ALLOWED_MAGIC.items():
        if data[:len(magic)] == magic:
            if magic == b"RIFF" and data[8:12] != b"WEBP":
                # RIFF is a generic container (also used by WAV/AVI/etc.) —
                # only accept it if the fourcc confirms it's actually WebP.
                continue
            return media_type
    return None


def _get_s3_client():
    kwargs = {
        "region_name": settings.AWS_REGION,
    }
    if settings.AWS_ACCESS_KEY_ID:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    if settings.S3_ENDPOINT_URL:
        kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL

    return boto3.client("s3", **kwargs)


def upload_complaint_image(
    image_bytes: bytes,
    complaint_id: str,
) -> tuple[str, str, int]:
    """
    Uploads image to S3. Returns (s3_key, media_type, file_size).
    Raises ValueError for invalid file type.
    Raises RuntimeError if S3 upload fails.
    """
    # Validate file type by magic bytes
    media_type = _validate_image_type(image_bytes)
    if not media_type:
        raise ValueError("File must be a valid JPEG, PNG, or WebP image")

    # Validate file size
    file_size = len(image_bytes)
    if file_size > settings.MAX_IMAGE_SIZE_BYTES:
        raise ValueError(f"Image exceeds maximum size of {settings.MAX_IMAGE_SIZE_BYTES // (1024*1024)}MB")

    # Generate S3 key — organised by complaint ID for easy retrieval
    ext = media_type.split("/")[1].replace("jpeg", "jpg")
    s3_key = f"complaints/{complaint_id}/{uuid.uuid4()}.{ext}"

    try:
        client = _get_s3_client()

        # Ensure bucket exists (dev only — production bucket pre-created)
        if settings.ENVIRONMENT == "development":
            try:
                client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
            except ClientError:
                client.create_bucket(Bucket=settings.S3_BUCKET_NAME)

        client.upload_fileobj(
            io.BytesIO(image_bytes),
            settings.S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={"ContentType": media_type},
        )
        logger.info(f"Uploaded complaint image: {s3_key} ({file_size} bytes)")
        return s3_key, media_type, file_size

    except ClientError as e:
        logger.error(f"S3 upload failed for complaint {complaint_id}: {e}")
        raise RuntimeError(f"Image upload failed: {e}")


def generate_presigned_url(s3_key: str, expiry_seconds: int = 300) -> str:
    """
    Generates a presigned URL valid for expiry_seconds (default 5 minutes).
    Only called by admin endpoints. Never sent to police.
    """
    try:
        client = _get_s3_client()
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": s3_key},
            ExpiresIn=expiry_seconds,
        )
        return url
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL for {s3_key}: {e}")
        raise RuntimeError(f"Could not generate image URL: {e}")
