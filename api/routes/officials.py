"""
WardWatch API - Officials Endpoints (Steps 3.3 + 3.5)

GET /api/v1/officials/{official_id}/issues  - Get issues for an official
PUT /api/v1/officials/{official_id}/status  - Update campaign status

All endpoints require Firebase Auth + official role.
Self-only access: user_id must match official_id (or admin).
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud import firestore
from pydantic import BaseModel, Field

from auth import FirebaseUser, require_official
from config import PROJECT_ID
from rate_limit import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/officials", tags=["officials"])

_db = None


def _get_db():
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


# ─── Models ───────────────────────────────────────────────────────────────────

VALID_STATUS_UPDATES = ["acknowledged", "in_progress", "resolved", "request_more_info"]


class OfficialIssueItem(BaseModel):
    campaign_id: str
    title: str
    issue_type: str
    severity: int
    citizen_count: int
    status: str
    sla_deadline: Optional[str] = None
    created_at: str
    address: str


class StatusUpdateRequest(BaseModel):
    campaign_id: str
    status: str = Field(...)
    notes: Optional[str] = Field(default=None, max_length=500)


class StatusUpdateResponse(BaseModel):
    campaign_id: str
    old_status: str
    new_status: str
    updated_at: str


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _ts_to_str(ts) -> str:
    if ts is None:
        return ""
    if hasattr(ts, "isoformat"):
        return ts.isoformat()
    if hasattr(ts, "seconds"):
        return datetime.fromtimestamp(ts.seconds, tz=timezone.utc).isoformat()
    return str(ts)


async def _send_fcm_to_members(campaign_id: str, title: str, body: str, data: dict):
    """
    Send FCM push notification to all campaign members.
    Uses messaging.send_each() for batching up to 500 tokens.
    Errors are logged but do not fail the status update.
    """
    try:
        from firebase_admin import messaging
        db = _get_db()
        members_ref = db.collection("campaigns").document(campaign_id).collection("members")
        members = list(members_ref.stream())

        messages = []
        for member_doc in members:
            member_data = member_doc.to_dict()
            user_id = member_data.get("user_id", member_doc.id)
            try:
                user_doc = db.collection("users").document(user_id).get()
                if not user_doc.exists:
                    continue
                fcm_token = user_doc.to_dict().get("fcm_token")
                if not fcm_token:
                    continue

                message = messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    data={k: str(v) for k, v in data.items()},
                    token=fcm_token,
                )
                messages.append(message)
            except Exception:
                pass  # Skip if user doc read fails

        sent = 0
        failed = 0
        
        # Batch send_each accepts up to 500 messages per call
        if messages:
            for i in range(0, len(messages), 500):
                batch = messages[i:i+500]
                try:
                    response = messaging.send_each(batch)
                    sent += response.success_count
                    failed += response.failure_count
                except Exception as e:
                    failed += len(batch)
                    logger.error("FCM batch send failed: %s", type(e).__name__)

        # Audit log (no sensitive data in notification body logged)
        db.collection("audit_logs").add({
            "event": "fcm_notifications_sent",
            "campaign_id": campaign_id,
            "sent": sent,
            "failed": failed,
            "actor": "officials_api",
            "timestamp": firestore.SERVER_TIMESTAMP,
        })

        logger.info("AUDIT fcm campaign=%s sent=%d failed=%d", campaign_id, sent, failed)
    except Exception as e:
        logger.error("FCM notification process failed: %s", type(e).__name__)


# ─── GET /api/v1/officials/{official_id}/issues ────────────────────────────────

@router.get("/{official_id}/issues", response_model=List[OfficialIssueItem])
async def get_official_issues(
    official_id: str,
    user: FirebaseUser = Depends(require_official),
):
    """
    Get all active campaigns assigned to this official or in their ward.
    Requires: auth + official role + self-only access (user_id == official_id).
    Returns campaigns ordered by SLA deadline (closest first). Limit 100.
    """
    # Self-only access
    if user.uid != official_id and not user.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions.",
        )

    db = _get_db()
    ward_id = user.ward_id

    try:
        results = {}

        # Query campaigns assigned to this official
        assigned_query = (
            db.collection("campaigns")
            .where("assigned_to", "==", official_id)
            .where("status", "!=", "closed")
            .limit(100)
        )
        for doc in assigned_query.stream():
            results[doc.id] = doc

        # Also get campaigns in official's ward (not yet assigned)
        if ward_id:
            ward_query = (
                db.collection("campaigns")
                .where("ward_id", "==", ward_id)
                .where("status", "!=", "closed")
                .limit(100)
            )
            for doc in ward_query.stream():
                results[doc.id] = doc

        issues = []
        for doc in results.values():
            data = doc.to_dict()
            issues.append(OfficialIssueItem(
                campaign_id=doc.id,
                title=data.get("title", ""),
                issue_type=data.get("issue_type", "other"),
                severity=data.get("severity", 1),
                citizen_count=data.get("citizen_count", 0),
                status=data.get("status", "open"),
                sla_deadline=_ts_to_str(data.get("sla_deadline")) or None,
                created_at=_ts_to_str(data.get("created_at")),
                address=data.get("address", ""),
            ))

        # Sort by SLA deadline (None/empty last, closest first)
        def sla_key(item):
            if not item.sla_deadline:
                return "9999"
            return item.sla_deadline

        issues.sort(key=sla_key)
        issues = issues[:100]

        logger.info(
            "AUDIT official_issues_fetched official=%s count=%d",
            official_id, len(issues),
        )

        return issues

    except Exception as e:
        logger.error("Failed to fetch official issues: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch issues. Please try again.",
        )


# ─── PUT /api/v1/officials/{official_id}/status ───────────────────────────────

@router.put("/{official_id}/status", response_model=StatusUpdateResponse)
async def update_campaign_status(
    official_id: str,
    request: StatusUpdateRequest,
    user: FirebaseUser = Depends(require_official),
):
    """
    Update the status of a campaign.
    Requires: auth + official role + self-only access.
    Valid status values: acknowledged, in_progress, resolved, request_more_info.
    If resolved: system sets status to 'verifying' and starts verification window.
    FCM notification sent to all campaign members.
    """
    # Self-only access
    if user.uid != official_id and not user.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions.",
        )

    # M7 Fix: Rate limit official status updates (max 20 per minute per official)
    check_rate_limit(user.uid, "status_update", max_requests=20)

    # Validate status enum
    if request.status not in VALID_STATUS_UPDATES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status. Must be one of: {VALID_STATUS_UPDATES}",
        )

    db = _get_db()

    # Fetch campaign
    campaign_ref = db.collection("campaigns").document(request.campaign_id)
    campaign_doc = campaign_ref.get()

    if not campaign_doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found.")

    campaign_data = campaign_doc.to_dict()
    old_status = campaign_data.get("status", "open")
    ward_id = campaign_data.get("ward_id")

    # Verify official is assigned to the campaign OR campaign is in their ward
    assigned_to = campaign_data.get("assigned_to")
    official_ward = user.ward_id

    is_assigned = (assigned_to == user.uid)
    is_ward_match = (official_ward and ward_id == official_ward)

    if not is_assigned and not is_ward_match and not user.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions.",
        )

    # If official marks as "resolved", system sets it to "verifying"
    # This starts the 72-hour citizen verification window
    final_status = "verifying" if request.status == "resolved" else request.status

    now_iso = datetime.now(timezone.utc).isoformat()
    timeline_event = {
        "action": "status_updated",
        "actor": user.uid,
        "timestamp": now_iso,
        "notes": request.notes or f"Status updated to {final_status} by official.",
    }

    try:
        update_data = {
            "status": final_status,
            "timeline": firestore.ArrayUnion([timeline_event]),
            "updated_at": firestore.SERVER_TIMESTAMP,
        }

        campaign_ref.update(update_data)

        # Update official stats (last action timestamp)
        try:
            db.collection("officials").document(user.uid).update({
                "last_action_at": firestore.SERVER_TIMESTAMP,
            })
        except Exception:
            pass  # Non-fatal

        # Audit log
        db.collection("audit_logs").add({
            "event": "status_updated",
            "campaign_id": request.campaign_id,
            "from_status": old_status,
            "to_status": final_status,
            "actor": user.uid,
            "notes": request.notes,
            "timestamp": firestore.SERVER_TIMESTAMP,
        })

        logger.info(
            "AUDIT status_updated official=%s campaign=%s %s->%s",
            user.uid, request.campaign_id, old_status, final_status,
        )

        # FCM notification to all campaign members (async, non-blocking)
        campaign_title = campaign_data.get("title", "Campaign")
        await _send_fcm_to_members(
            campaign_id=request.campaign_id,
            title=f"Campaign Update: {campaign_title[:50]}",
            body=f"Status changed to {final_status.replace('_', ' ')}.",
            data={
                "campaign_id": request.campaign_id,
                "action": "status_change",
                "status": final_status,
            },
        )

        return StatusUpdateResponse(
            campaign_id=request.campaign_id,
            old_status=old_status,
            new_status=final_status,
            updated_at=now_iso,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Status update failed: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update status. Please try again.",
        )
