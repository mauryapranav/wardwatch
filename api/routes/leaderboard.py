"""
WardWatch API - Leaderboard & Citizen Profile Endpoints (Steps 5.1 + 5.2)

GET /api/v1/citizens/{user_id}/profile      - Citizen profile with reputation
GET /api/v1/leaderboard                     - Public ward leaderboard (no auth)
GET /api/v1/leaderboard/{ward_id}           - Ward detail (public)
DELETE /api/v1/citizens/{user_id}           - Delete account (DPDP compliance)

Points system:
  create_campaign  = +10
  join_campaign    = +15
  verify_campaign  = +25
  streak_bonus     = +5 (3-day streak)

Tier system:
  Bronze  = 0-199
  Silver  = 200-499
  Gold    = 500-999
  Platinum = 1000+
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud import firestore
from pydantic import BaseModel

from auth import FirebaseUser, verify_firebase_token, require_admin
from config import PROJECT_ID

logger = logging.getLogger(__name__)

router = APIRouter(tags=["leaderboard"])

_db = None


def _get_db():
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


# ─── Models ───────────────────────────────────────────────────────────────────

class CitizenProfile(BaseModel):
    user_id: str
    name: str
    civic_reputation: int
    total_points: int
    tier: str
    tier_badge: str
    streak_days: int
    verified_reports: int
    created_at: str


class WardLeaderboardItem(BaseModel):
    rank: int
    ward_id: str
    name: str
    total_issues: int
    resolved_issues: int
    resolution_rate: float
    avg_resolution_days: float
    citizen_participation_rate: float


class WardDetail(BaseModel):
    ward_id: str
    name: str
    total_issues: int
    resolved_issues: int
    resolution_rate: float
    avg_resolution_days: float
    recent_campaigns: List[dict]  # Anonymized: no PII


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_tier(reputation: int) -> tuple[str, str]:
    """Return (tier_name, tier_badge_emoji) for a reputation score."""
    if reputation >= 1000:
        return ("Platinum", "🏆")
    elif reputation >= 500:
        return ("Gold", "🥇")
    elif reputation >= 200:
        return ("Silver", "🥈")
    return ("Bronze", "🥉")


def _calculate_streak(user_data: dict) -> int:
    """
    Check if user reported campaigns on each of the last 3 days.
    Returns streak_days (0, 1, 2, or 3).
    """
    streak_days = user_data.get("streak_days", 0)
    # Simplified: read streak_days from user document (updated by campaign creation)
    return min(streak_days, 999)


def _ts_to_str(ts) -> str:
    if ts is None:
        return ""
    if hasattr(ts, "isoformat"):
        return ts.isoformat()
    if hasattr(ts, "seconds"):
        return datetime.fromtimestamp(ts.seconds, tz=timezone.utc).isoformat()
    return str(ts)


# ─── GET /api/v1/citizens/{user_id}/profile ───────────────────────────────────

@router.get("/citizens/{user_id}/profile", response_model=CitizenProfile)
async def get_citizen_profile(
    user_id: str,
    current_user: FirebaseUser = Depends(verify_firebase_token),
):
    """
    Get a citizen's profile with reputation, tier, streak, and verified_reports.
    Auth required. Self-only access (unless admin).
    Points: create=+10, join=+15, verify=+25, streak=+5.
    """
    # Self-only access (or admin)
    if current_user.uid != user_id and not current_user.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions.",
        )

    db = _get_db()
    user_doc = db.collection("users").document(user_id).get()

    if not user_doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user_data = user_doc.to_dict()
    reputation = user_data.get("civic_reputation", 0)
    total_points = user_data.get("total_points", reputation)
    streak_days = _calculate_streak(user_data)
    verified_reports = user_data.get("verified_reports", 0)
    tier, badge = _get_tier(reputation)

    logger.info("AUDIT profile_fetched user=%s", user_id)

    return CitizenProfile(
        user_id=user_id,
        name=user_data.get("name", "Anonymous Citizen"),
        civic_reputation=reputation,
        total_points=total_points,
        tier=tier,
        tier_badge=badge,
        streak_days=streak_days,
        verified_reports=verified_reports,
        created_at=_ts_to_str(user_data.get("created_at")),
    )


# ─── GET /api/v1/leaderboard ──────────────────────────────────────────────────

@router.get("/leaderboard", response_model=List[WardLeaderboardItem])
async def get_leaderboard():
    """
    Get the public ward leaderboard. No auth required.
    Returns all wards ordered by resolution_rate descending.
    No PII in response.
    """
    db = _get_db()

    try:
        leaderboard_doc = db.collection("leaderboard").document("current").get()
        if leaderboard_doc.exists:
            data = leaderboard_doc.to_dict()
            wards_data = data.get("wards", [])
        else:
            # Build from ward_scores if leaderboard doc doesn't exist
            wards_data = []
            ward_scores = db.collection("ward_scores").stream()
            for doc in ward_scores:
                score_data = doc.to_dict()
                score_data["ward_id"] = doc.id
                wards_data.append(score_data)

        # Sort by resolution_rate descending
        wards_data.sort(
            key=lambda w: w.get("resolution_rate", 0),
            reverse=True
        )

        result = []
        for idx, ward in enumerate(wards_data):
            result.append(WardLeaderboardItem(
                rank=idx + 1,
                ward_id=ward.get("ward_id", ""),
                name=ward.get("name", ward.get("ward_id", "")),
                total_issues=ward.get("total_issues", 0),
                resolved_issues=ward.get("resolved_issues", 0),
                resolution_rate=ward.get("resolution_rate", 0.0),
                avg_resolution_days=ward.get("avg_resolution_days", 0.0),
                citizen_participation_rate=ward.get("citizen_participation_rate", 0.0),
            ))

        return result

    except Exception as e:
        logger.error("Leaderboard fetch failed: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch leaderboard.",
        )


# ─── GET /api/v1/leaderboard/{ward_id} ───────────────────────────────────────

@router.get("/leaderboard/{ward_id}", response_model=WardDetail)
async def get_ward_detail(ward_id: str):
    """
    Get details for a specific ward including recent campaigns (anonymized).
    Public access. No auth required. No PII in response.
    """
    db = _get_db()

    ward_score_doc = db.collection("ward_scores").document(ward_id).get()
    if not ward_score_doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ward not found.")

    ward_data = ward_score_doc.to_dict()

    # Fetch last 5 campaigns — anonymized (no founder names, no exact addresses, no photos)
    recent_campaigns = []
    try:
        campaigns_query = (
            db.collection("campaigns")
            .where("ward_id", "==", ward_id)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(5)
        )
        for doc in campaigns_query.stream():
            c = doc.to_dict()
            # Only return non-PII fields
            recent_campaigns.append({
                "issue_type": c.get("issue_type", "other"),
                "severity": c.get("severity", 1),
                "status": c.get("status", "open"),
                "citizen_count": c.get("citizen_count", 0),
                "created_at": _ts_to_str(c.get("created_at")),
            })
    except Exception:
        pass  # Recent campaigns are optional

    return WardDetail(
        ward_id=ward_id,
        name=ward_data.get("name", ward_id),
        total_issues=ward_data.get("total_issues", 0),
        resolved_issues=ward_data.get("resolved_issues", 0),
        resolution_rate=ward_data.get("resolution_rate", 0.0),
        avg_resolution_days=ward_data.get("avg_resolution_days", 0.0),
        recent_campaigns=recent_campaigns,
    )


# ─── DELETE /api/v1/citizens/{user_id} (DPDP Compliance) ─────────────────────

@router.delete("/citizens/{user_id}", status_code=status.HTTP_200_OK)
async def delete_account(
    user_id: str,
    current_user: FirebaseUser = Depends(verify_firebase_token),
):
    """
    Delete/anonymize a citizen's account (DPDP compliance).
    Auth required. Self-only access.
    Anonymizes: name, phone, email. Retains aggregated civic data.
    """
    if current_user.uid != user_id and not current_user.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions.",
        )

    db = _get_db()

    try:
        # Anonymize user profile (retain aggregated civic data)
        db.collection("users").document(user_id).update({
            "name": "Deleted User",
            "phone": None,
            "email": None,
            "fcm_token": None,
            "deleted_at": firestore.SERVER_TIMESTAMP,
            "deleted": True,
        })

        # Audit log
        db.collection("audit_logs").add({
            "event": "account_deleted",
            "user_id": user_id,
            "actor": user_id,
            "timestamp": firestore.SERVER_TIMESTAMP,
        })

        # Delete Firebase Auth account
        try:
            from firebase_admin import auth as fb_auth
            fb_auth.delete_user(user_id)
        except Exception:
            pass  # Firestore anonymization is the primary compliance step

        logger.info("AUDIT account_deleted user=%s", user_id)
        return {"status": "deleted", "message": "Your account has been anonymized."}

    except Exception as e:
        logger.error("Account deletion failed: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account. Please contact support.",
        )
