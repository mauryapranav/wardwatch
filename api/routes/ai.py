"""
WardWatch API - AI Classification Endpoint
POST /api/v1/ai/classify

Classifies civic issue photos using Gemini Vision (gemini-2.0-flash-exp).
Requires authentication + phone verification.
Rate limit: 3 requests per minute per user.

Security:
- No Gemini API internals exposed in error messages
- No image content logged
- Rate limited to prevent abuse
"""
import json
import logging
from typing import Literal, Optional

import google.generativeai as genai
from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud import storage as gcs_storage
from pydantic import BaseModel, Field, field_validator

from auth import FirebaseUser, require_phone_verified
from config import PROJECT_ID
from rate_limit import check_rate_limit
from secrets import secrets

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])

# Allowed issue types
ALLOWED_ISSUE_TYPES = {"pothole", "streetlight", "water", "garbage", "sidewalk", "other"}
RATE_LIMIT_AI_PER_MINUTE = 3

# Gemini model
GEMINI_MODEL = "gemini-2.0-flash-exp"

# Classification prompt (structured output)
CLASSIFICATION_PROMPT = """Classify this civic issue photo. Return ONLY a JSON object with no markdown, no code blocks, just raw JSON:
{
  "type": "<one of: pothole, streetlight, water, garbage, sidewalk, other>",
  "severity": <integer 1-5 where 1=minor, 5=critical>,
  "confidence": <float 0.0-1.0>,
  "description": "<max 100 characters describing the issue>"
}
"""


class ClassifyRequest(BaseModel):
    storage_path: str = Field(..., min_length=1, max_length=500)


class ClassificationResult(BaseModel):
    type: Literal["pothole", "streetlight", "water", "garbage", "sidewalk", "other"]
    severity: int = Field(..., ge=1, le=5)
    confidence: float = Field(..., ge=0.0, le=1.0)
    description: str = Field(..., max_length=100)


def _get_bucket_name() -> str:
    return f"{PROJECT_ID}.appspot.com"


def _fetch_image_from_storage(storage_path: str) -> bytes:
    """Fetch image bytes from Cloud Storage."""
    try:
        client = gcs_storage.Client(project=PROJECT_ID)
        bucket = client.bucket(_get_bucket_name())
        blob = bucket.blob(storage_path)
        return blob.download_as_bytes()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found or inaccessible.",
        )


def _call_gemini_vision(image_bytes: bytes, content_type: str = "image/jpeg") -> dict:
    """Call Gemini Vision API and return parsed classification result."""
    try:
        genai.configure(api_key=secrets.GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)

        image_part = {
            "mime_type": content_type,
            "data": image_bytes,
        }

        response = model.generate_content(
            [
                CLASSIFICATION_PROMPT,
                {"inline_data": image_part},
            ],
            generation_config=genai.GenerationConfig(
                temperature=0.1,  # Low temperature for consistent classification
                max_output_tokens=200,
            ),
        )

        raw_text = response.text.strip()

        # Remove markdown code blocks if present
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            raw_text = "\n".join(
                line for line in lines
                if not line.startswith("```")
            ).strip()

        return json.loads(raw_text)

    except json.JSONDecodeError:
        logger.error("Gemini returned malformed JSON.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Classification service error. Please try again.",
        )
    except Exception:
        # Generic error — do not expose Gemini internals
        logger.error("Gemini Vision API call failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Classification service error. Please try again.",
        )


@router.post("/classify", response_model=ClassificationResult)
async def classify_issue(
    request: ClassifyRequest,
    user: FirebaseUser = Depends(require_phone_verified),
):
    """
    Classify a civic issue photo using Gemini Vision.

    - Requires phone_verified
    - Rate limit: 3/min per user
    - Fetches image from Cloud Storage using storage_path
    - Returns classification: type, severity, confidence, description
    """
    # Rate limiting
    check_rate_limit(user.uid, "ai_classify", max_requests=RATE_LIMIT_AI_PER_MINUTE)

    # Fetch image from Cloud Storage
    image_bytes = _fetch_image_from_storage(request.storage_path)

    # Call Gemini Vision
    raw_result = _call_gemini_vision(image_bytes)

    # Validate response structure
    try:
        result = ClassificationResult(
            type=raw_result.get("type", "other"),
            severity=int(raw_result.get("severity", 3)),
            confidence=float(raw_result.get("confidence", 0.5)),
            description=str(raw_result.get("description", ""))[:100],
        )
    except (ValueError, TypeError):
        logger.error("Gemini returned invalid field values.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Classification service error. Please try again.",
        )

    # Validate issue type is in allowed enum
    if result.type not in ALLOWED_ISSUE_TYPES:
        result.type = "other"  # Safe fallback

    # Audit log — no image content logged
    logger.info(
        "AUDIT ai_classify user=%s type=%s severity=%d confidence=%.2f",
        user.uid,
        result.type,
        result.severity,
        result.confidence,
    )

    return result
