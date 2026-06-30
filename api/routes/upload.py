"""
WardWatch API - File Upload Endpoint
POST /api/v1/upload

Validates file type (via python-magic, not extension), size, and auth.
Uploads to Cloud Storage under campaigns/temp/{user_id}/{timestamp}_{filename}.

Rate limit: 5 uploads per minute per user.
"""
import io
import logging
import time
from datetime import datetime, timezone

import magic
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from google.cloud import storage
from pydantic import BaseModel

from auth import FirebaseUser, require_phone_verified
from config import PROJECT_ID
from rate_limit import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

# Allowed MIME types (validated via magic, not extension)
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
RATE_LIMIT_UPLOADS_PER_MINUTE = 5

# GCS bucket name (constructed from PROJECT_ID, never hardcoded)
def _get_bucket_name() -> str:
    return f"{PROJECT_ID}.appspot.com"


class UploadResponse(BaseModel):
    storage_path: str
    download_url: str
    size: int
    content_type: str


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    user: FirebaseUser = Depends(require_phone_verified),
):
    """
    Upload a photo for a civic campaign report.

    - Validates file type using python-magic (not file extension)
    - Validates file size (max 10MB)
    - Uploads to GCS under campaigns/temp/{user_id}/{timestamp}_{filename}
    - Returns storage path and signed URL

    Rate limit: 5 uploads per minute per user.
    """
    # Rate limiting
    check_rate_limit(user.uid, "upload", max_requests=RATE_LIMIT_UPLOADS_PER_MINUTE)

    # Read file content
    try:
        content = await file.read()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file.",
        )

    # Validate file size
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 10MB.",
        )

    # Validate file type using python-magic (reads magic bytes, not extension)
    try:
        mime_type = magic.from_buffer(content, mime=True)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not determine file type.",
        )

    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Invalid file type. Only JPEG, PNG, and WebP images are allowed.",
        )

    # Build storage path
    timestamp = int(time.time())
    safe_filename = f"{timestamp}_{user.uid[:8]}"
    storage_path = f"campaigns/temp/{user.uid}/{safe_filename}"

    # Upload to Cloud Storage
    try:
        gcs_client = storage.Client(project=PROJECT_ID)
        bucket = gcs_client.bucket(_get_bucket_name())
        blob = bucket.blob(storage_path)
        blob.upload_from_string(
            content,
            content_type=mime_type,
        )
        # Generate a signed URL valid for 1 hour (for preview only)
        download_url = blob.generate_signed_url(
            expiration=3600,
            method="GET",
            version="v4",
        )
    except Exception:
        logger.error(
            "Upload failed for user %s",
            user.uid[:8],  # Truncated UID only, no file details
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed. Please try again.",
        )

    # Audit log (user_id, timestamp, file_type — no file content or full path)
    logger.info(
        "AUDIT upload user=%s type=%s size=%d",
        user.uid,
        mime_type,
        len(content),
    )

    return UploadResponse(
        storage_path=storage_path,
        download_url=download_url,
        size=len(content),
        content_type=mime_type,
    )
