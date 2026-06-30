"""
WardWatch API - Campaign (Issue) Endpoints

POST   /api/v1/issues              - Create campaign
GET    /api/v1/issues/nearby       - Nearby campaigns
GET    /api/v1/issues/{id}         - Get campaign by ID
POST   /api/v1/issues/{id}/join    - Join a campaign

All endpoints require Firebase Auth. Create/join require phone_verified.
"""
import logging
import math
from datetime import datetime, timezone, timedelta
import html
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from google.cloud import firestore
from pydantic import BaseModel, Field, field_validator

from auth import FirebaseUser, verify_firebase_token, require_phone_verified
from config import PROJECT_ID
from rate_limit import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/issues", tags=["issues"])

_db = None

def _get_db():
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


# ─── Pydantic Models ──────────────────────────────────────────────────────────

ISSUE_TYPES = ["pothole", "streetlight", "water", "garbage", "sidewalk", "other"]


class LocationModel(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0)
    lng: float = Field(..., ge=-180.0, le=180.0)


class CreateCampaignRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=500)
    issue_type: str = Field(...)
    severity: int = Field(..., ge=1, le=5)
    location: LocationModel
    address: str = Field(..., min_length=1, max_length=300)
    storage_path: str = Field(..., min_length=1)
    photo_id: str = Field(..., min_length=1)

    @field_validator("issue_type")
    @classmethod
    def validate_issue_type(cls, v):
        if v not in ISSUE_TYPES:
            raise ValueError(f"issue_type must be one of {ISSUE_TYPES}")
        return v


class CreateCampaignResponse(BaseModel):
    campaign_id: str
    status: str
    duplicate_found: bool = False
    existing_campaign_id: Optional[str] = None


class NearbyIssueItem(BaseModel):
    campaign_id: str
    title: str
    issue_type: str
    severity: int
    location: LocationModel
    address: str
    status: str
    citizen_count: int
    created_at: str
    distance_meters: Optional[float] = None


class PhotoSummary(BaseModel):
    photo_id: str
    storage_path: str
    thumbnail_url: Optional[str] = None


class TimelineEvent(BaseModel):
    action: str
    actor: str
    timestamp: str
    notes: Optional[str] = None


class CampaignDetailResponse(BaseModel):
    campaign_id: str
    title: str
    description: str
    issue_type: str
    severity: int
    location: LocationModel
    address: str
    status: str
    citizen_count: int
    sla_deadline: Optional[str] = None
    created_at: str
    photos: List[PhotoSummary] = []
    timeline: List[TimelineEvent] = []
    members_count: int = 0


class JoinCampaignResponse(BaseModel):
    campaign_id: str
    citizen_count: int
    joined: bool


# ─── Helper Functions ──────────────────────────────────────────────────────────

def _haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance in meters between two GPS coordinates."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _derive_ward_id(lat: float, lng: float) -> str:
    """
    Derive ward_id from GPS coordinates.
    For hackathon: simple grid-based lookup.
    Production: use actual ward boundary data.
    """
    # Mumbai ward boundaries (simplified for demo)
    if 19.05 <= lat <= 19.20 and 72.82 <= lng <= 72.92:
        return "ward_12_andheri"
    elif 19.02 <= lat <= 19.05 and 72.82 <= lng <= 72.88:
        return "ward_8_bandra"
    elif 19.08 <= lat <= 19.13 and 72.82 <= lng <= 72.87:
        return "ward_15_juhu"
    else:
        return "ward_unknown"


def _derive_zone_id(ward_id: str) -> str:
    """Derive zone from ward_id."""
    zone_map = {
        "ward_12_andheri": "zone_k_west",
        "ward_8_bandra": "zone_h_west",
        "ward_15_juhu": "zone_k_west",
    }
    return zone_map.get(ward_id, "zone_unknown")


def _ts_to_str(ts) -> str:
    """Convert Firestore timestamp to ISO string."""
    if ts is None:
        return ""
    if hasattr(ts, "isoformat"):
        return ts.isoformat()
    if hasattr(ts, "seconds"):
        return datetime.fromtimestamp(ts.seconds, tz=timezone.utc).isoformat()
    return str(ts)


async def _log_audit(action: str, user_id: str, campaign_id: str, notes: str = ""):
    """Write an audit log entry to Firestore."""
    try:
        db = _get_db()
        db.collection("audit_logs").add({
            "event": action,
            "actor": user_id,
            "campaign_id": campaign_id,
            "notes": notes,
            "timestamp": firestore.SERVER_TIMESTAMP,
        })
    except Exception as e:
        logger.error("Failed to write audit log: %s", type(e).__name__)


# ─── POST /api/v1/issues ─────────────────────────────────────────────────────

@router.post("", response_model=CreateCampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    request: CreateCampaignRequest,
    user: FirebaseUser = Depends(require_phone_verified),
):
    """
    Create a new civic campaign.
    Requires auth + phone_verified.
    Rate limit: 5/min per user.
    Performs duplicate detection within 50m radius, same type, last 30 days.
    """
    check_rate_limit(user.uid, "create_campaign", max_requests=5)

    db = _get_db()

    # Duplicate detection: campaigns within 50m, same type, last 30 days
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    # Bounding box approximation (1 degree lat ~ 111km)
    lat_delta = 50 / 111000  # 50 meters in degrees
    lng_delta = 50 / (111000 * math.cos(math.radians(request.location.lat)))

    try:
        nearby_query = (
            db.collection("campaigns")
            .where("issue_type", "==", request.issue_type)
            .where("created_at", ">=", thirty_days_ago)
            .limit(50)
        )
        nearby_docs = list(nearby_query.stream())

        for doc in nearby_docs:
            data = doc.to_dict()
            
            # BUG-1 Fix: Filter status in Python since Firestore only allows one inequality
            if data.get("status") == "closed":
                continue
                
            loc = data.get("location", {})
            if isinstance(loc, dict):
                existing_lat = loc.get("lat", 0)
                existing_lng = loc.get("lng", 0)
            elif hasattr(loc, "latitude"):  # Firestore GeoPoint
                existing_lat = loc.latitude
                existing_lng = loc.longitude
            else:
                continue

            dist = _haversine_distance(
                request.location.lat, request.location.lng,
                existing_lat, existing_lng,
            )
            if dist <= 50:
                logger.info("AUDIT duplicate_check user=%s found=%s", user.uid, doc.id)
                return CreateCampaignResponse(
                    campaign_id=doc.id,
                    status="DUPLICATE_FOUND",
                    duplicate_found=True,
                    existing_campaign_id=doc.id,
                )
    except Exception as e:
        logger.error("Duplicate check failed: %s", type(e).__name__)
        # Continue with creation if duplicate check fails

    # Derive ward and zone
    ward_id = _derive_ward_id(request.location.lat, request.location.lng)
    zone_id = _derive_zone_id(ward_id)

    # Create campaign document
    # M1 Fix: XSS sanitization on user input
    campaign_data = {
        "title": html.escape(request.title.strip()),
        "description": html.escape(request.description.strip()),
        "issue_type": request.issue_type,
        "severity": request.severity,
        "location": {
            "lat": request.location.lat,
            "lng": request.location.lng,
        },
        "address": request.address,
        "ward_id": ward_id,
        "zone_id": zone_id,
        "status": "open",
        "founder_id": user.uid,
        "citizen_count": 1,
        "current_level": 1,
        "sla_deadline": None,
        "assigned_to": None,
        "mass_issue": False,
        "false_closure_count": 0,
        "created_at": firestore.SERVER_TIMESTAMP,
        "timeline": [{
            "action": "created",
            "actor": user.uid,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "notes": "Campaign created by citizen",
        }],
    }

    try:
        # Create campaign
        _, campaign_ref = db.collection("campaigns").add(campaign_data)
        campaign_id = campaign_ref.id

        # Create founder member document
        db.collection("campaigns").document(campaign_id).collection("members").document(user.uid).set({
            "joined_at": firestore.SERVER_TIMESTAMP,
            "role": "founder",
            "user_id": user.uid,
        })

        # Update user civic_reputation (+10 points)
        user_ref = db.collection("users").document(user.uid)
        user_ref.set(
            {"civic_reputation": firestore.Increment(10), "total_points": firestore.Increment(10)},
            merge=True,
        )

        # Audit log
        await _log_audit("campaign_created", user.uid, campaign_id)

        logger.info("AUDIT campaign_created user=%s campaign=%s", user.uid, campaign_id)

        return CreateCampaignResponse(
            campaign_id=campaign_id,
            status="CREATED",
            duplicate_found=False,
        )

    except Exception as e:
        logger.error("Campaign creation failed: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create campaign. Please try again.",
        )


# ─── GET /api/v1/issues/nearby ──────────────────────────────────────────────────

@router.get("/nearby", response_model=List[NearbyIssueItem])
async def get_nearby_campaigns(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lng: float = Query(..., ge=-180.0, le=180.0),
    # H3: Limit max radius to 2km (2000m) to prevent large O(n) scans
    radius: int = Query(default=2000, ge=100, le=2000),
    user: FirebaseUser = Depends(verify_firebase_token),
):
    """
    Get nearby campaigns within the specified radius.
    Requires auth. Rate limit: 50/min per user.
    Returns list data only (no photos, no full timeline).
    Audit logs with rounded coordinates for privacy.
    """
    check_rate_limit(user.uid, "nearby", max_requests=50)

    db = _get_db()

    # Bounding box approximation
    lat_delta = radius / 111000
    lng_delta = radius / (111000 * max(math.cos(math.radians(lat)), 0.001))

    lat_min, lat_max = lat - lat_delta, lat + lat_delta
    lng_min, lng_max = lng - lng_delta, lng + lng_delta

    try:
        # H3: Firestore bounding box query (approximation)
        # We can only do inequality filters on ONE field in Firestore.
        # Filtering on location.lat significantly reduces the payload size before Python filtering.
        query = (
            db.collection("campaigns")
            .where("location.lat", ">=", lat_min)
            .where("location.lat", "<=", lat_max)
            .limit(200)
        )
        docs = list(query.stream())
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch nearby campaigns.",
        )

    results = []
    for doc in docs:
        data = doc.to_dict()
        
        # H3: Since we replaced the status filter with location filter in Firestore, 
        # we must filter out closed campaigns here.
        if data.get("status") == "closed":
            continue

        loc = data.get("location", {})
        if isinstance(loc, dict):
            c_lat = loc.get("lat", 0)
            c_lng = loc.get("lng", 0)
        elif hasattr(loc, "latitude"):
            c_lat = loc.latitude
            c_lng = loc.longitude
        else:
            continue

        # H3: Fast bounding box check for longitude before expensive haversine calculation
        if not (lng_min <= c_lng <= lng_max):
            continue

        dist = _haversine_distance(lat, lng, c_lat, c_lng)
        if dist > radius:
            continue

        results.append(NearbyIssueItem(
            campaign_id=doc.id,
            title=data.get("title", ""),
            issue_type=data.get("issue_type", "other"),
            severity=data.get("severity", 1),
            location=LocationModel(lat=c_lat, lng=c_lng),
            address=data.get("address", ""),
            status=data.get("status", "open"),
            citizen_count=data.get("citizen_count", 0),
            created_at=_ts_to_str(data.get("created_at")),
            distance_meters=round(dist, 1),
        ))

    # Sort by citizen_count descending, limit to 50
    results.sort(key=lambda x: x.citizen_count, reverse=True)
    results = results[:50]

    # Audit log with rounded coordinates
    logger.info(
        "AUDIT nearby_query user=%s lat=%.2f lng=%.2f radius=%d count=%d",
        user.uid, round(lat, 2), round(lng, 2), radius, len(results),
    )

    return results


# ─── GET /api/v1/issues/{campaign_id} ─────────────────────────────────────────────

@router.get("/{campaign_id}", response_model=CampaignDetailResponse)
async def get_campaign(
    campaign_id: str,
    user: FirebaseUser = Depends(verify_firebase_token),
):
    """
    Get full campaign details by ID.
    Requires auth + campaign membership.
    Returns 403 for non-members (no existence leakage).
    """
    db = _get_db()

    # Check campaign existence
    campaign_ref = db.collection("campaigns").document(campaign_id)
    campaign_doc = campaign_ref.get()

    if not campaign_doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")

    # Check membership (returns 403, not 404, to avoid existence leakage for non-members)
    member_ref = campaign_ref.collection("members").document(user.uid)
    member_doc = member_ref.get()

    if not member_doc.exists and not user.admin:
        # Check if official assigned to this campaign
        campaign_data = campaign_doc.to_dict()
        if not (user.role == "official" and campaign_data.get("assigned_to") == user.uid):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    data = campaign_doc.to_dict()

    # Fetch photos
    photos = []
    try:
        photo_docs = db.collection("photos").where("campaign_id", "==", campaign_id).limit(20).stream()
        for pd in photo_docs:
            pd_data = pd.to_dict()
            photos.append(PhotoSummary(
                photo_id=pd.id,
                storage_path=pd_data.get("storagePath", pd_data.get("storage_path", "")),
                thumbnail_url=pd_data.get("thumbnailUrl"),
            ))
    except Exception:
        pass  # Non-fatal

    # Members count
    members_count = 0
    try:
        members_count = len(list(campaign_ref.collection("members").list_documents()))
    except Exception:
        pass

    # Parse location
    loc = data.get("location", {})
    if isinstance(loc, dict):
        location = LocationModel(lat=loc.get("lat", 0), lng=loc.get("lng", 0))
    elif hasattr(loc, "latitude"):
        location = LocationModel(lat=loc.latitude, lng=loc.longitude)
    else:
        location = LocationModel(lat=0, lng=0)

    # Parse timeline
    timeline = []
    for event in data.get("timeline", []):
        timeline.append(TimelineEvent(
            action=event.get("action", ""),
            actor=event.get("actor", ""),
            timestamp=str(event.get("timestamp", "")),
            notes=event.get("notes"),
        ))

    return CampaignDetailResponse(
        campaign_id=campaign_doc.id,
        title=data.get("title", ""),
        description=data.get("description", ""),
        issue_type=data.get("issue_type", "other"),
        severity=data.get("severity", 1),
        location=location,
        address=data.get("address", ""),
        status=data.get("status", "open"),
        citizen_count=data.get("citizen_count", 0),
        sla_deadline=_ts_to_str(data.get("sla_deadline")),
        created_at=_ts_to_str(data.get("created_at")),
        photos=photos,
        timeline=timeline,
        members_count=members_count,
    )


# ─── POST /api/v1/issues/{campaign_id}/join ───────────────────────────────────

@router.post("/{campaign_id}/join", response_model=JoinCampaignResponse)
async def join_campaign(
    campaign_id: str,
    user: FirebaseUser = Depends(require_phone_verified),
):
    """
    Join an existing campaign as a supporting citizen.
    Requires auth + phone_verified.
    Rate limit: 10/min per user.
    Increments citizen_count atomically.
    Awards +5 civic_reputation to the joining user.
    Idempotent: re-joining returns current count without error.
    """
    check_rate_limit(user.uid, "join_campaign", max_requests=10)

    db = _get_db()

    # Verify campaign exists and is not closed
    campaign_ref = db.collection("campaigns").document(campaign_id)
    campaign_doc = campaign_ref.get()

    if not campaign_doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")

    campaign_data = campaign_doc.to_dict()
    if campaign_data.get("status") == "closed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot join a closed campaign.",
        )

    # Check if already a member (idempotent)
    member_ref = campaign_ref.collection("members").document(user.uid)
    member_doc = member_ref.get()

    if member_doc.exists:
        # Already joined — return current count without error
        return JoinCampaignResponse(
            campaign_id=campaign_id,
            citizen_count=campaign_data.get("citizen_count", 1),
            joined=False,
        )

    try:
        # Add member document
        member_ref.set({
            "joined_at": firestore.SERVER_TIMESTAMP,
            "role": "supporter",
            "user_id": user.uid,
        })

        # Atomically increment citizen_count
        campaign_ref.update({
            "citizen_count": firestore.Increment(1),
        })

        # Award +5 civic_reputation to joining user
        user_ref = db.collection("users").document(user.uid)
        user_ref.set(
            {"civic_reputation": firestore.Increment(5), "total_points": firestore.Increment(5)},
            merge=True,
        )

        # Append timeline event
        campaign_ref.update({
            "timeline": firestore.ArrayUnion([{
                "action": "citizen_joined",
                "actor": user.uid,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "notes": f"Citizen joined. Total supporters: {campaign_data.get('citizen_count', 1) + 1}",
            }])
        })

        # Fetch updated citizen_count
        updated_doc = campaign_ref.get()
        new_count = updated_doc.to_dict().get("citizen_count", 1) if updated_doc.exists else 1

        # Audit log
        await _log_audit("citizen_joined", user.uid, campaign_id)
        logger.info("AUDIT citizen_joined user=%s campaign=%s count=%d", user.uid, campaign_id, new_count)

        return JoinCampaignResponse(
            campaign_id=campaign_id,
            citizen_count=new_count,
            joined=True,
        )

    except Exception as e:
        logger.error("Join campaign failed: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to join campaign. Please try again.",
        )
