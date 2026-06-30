"""
WardWatch API - Geocoding Proxy Endpoint (Step 1.11 — backend proxy for Flutter)

The Flutter app NEVER calls Google Maps directly.
This endpoint proxies reverse geocoding using the Maps API key from Secret Manager.
Maps API key is NEVER in the Flutter binary — only the map display key is in AndroidManifest.xml.

Routes:
  GET /api/v1/geo/reverse?lat={float}&lng={float} → address string
"""
import logging
import re
from fastapi import APIRouter, Depends, HTTPException, Query, status
import httpx

from auth import FirebaseUser, verify_firebase_token
from config import PROJECT_ID

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/geo", tags=["geocoding"])

GEOCODING_BASE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


@router.get("/reverse")
async def reverse_geocode(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lng: float = Query(..., ge=-180.0, le=180.0),
    current_user: FirebaseUser = Depends(verify_firebase_token),
):
    """
    Reverse geocode a GPS coordinate to a human-readable address.
    Auth required. Maps API key is server-side only — never sent to client.
    Lat/lng logged at 2 decimal places for privacy.
    """
    # Lazy-load MAPS_API_KEY inside the endpoint (not at module import time)
    try:
        from secrets import secrets
        maps_api_key = secrets.MAPS_API_KEY
    except Exception:
        import os
        maps_api_key = os.environ.get("MAPS_API_KEY", "")

    if not maps_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Geocoding service temporarily unavailable.",
        )

    # Log at reduced precision (2dp = ~1km accuracy, not exact location)
    logger.info(
        "AUDIT reverse_geocode user=%s lat=%.2f lng=%.2f",
        current_user.uid, round(lat, 2), round(lng, 2),
    )

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                GEOCODING_BASE_URL,
                params={
                    "latlng": f"{lat},{lng}",
                    "key": maps_api_key,
                    "result_type": "street_address|route|locality",
                    "language": "en",
                },
            )
            response.raise_for_status()
            data = response.json()

        if data.get("status") != "OK" or not data.get("results"):
            return {"address": f"Near {lat:.4f}, {lng:.4f}", "formatted": False}

        # Return only the formatted_address — no raw geometry data to client
        address = data["results"][0].get("formatted_address", "")
        # Strip country code from address for cleaner display
        address = re.sub(r",\s*India$", "", address).strip()

        return {"address": address, "formatted": True}

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Geocoding timed out. Please try again.",
        )
    except Exception as e:
        logger.error("Reverse geocoding failed: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Geocoding service error.",
        )
