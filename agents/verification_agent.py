"""
WardWatch - Verification Agent (Step 4.4)

Function: verify_campaign(campaign_id: str) -> dict

Processes the 72-hour citizen verification window after an official marks an issue resolved.
Uses Gemini Vision to compare before/after photos.
Uses weighted voting based on citizen civic reputation.

Called by:
- Cloud Function when 72-hour window expires
- Manual endpoint (POST /api/v1/internal/verify) for hackathon testing
"""
import logging
import math
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

from google.cloud import firestore

logger = logging.getLogger(__name__)

_db: Optional[firestore.Client] = None

VERIFICATION_WINDOW_HOURS = 72
APPROVAL_THRESHOLD = 0.60  # 60% weighted approval required to close


def _get_db() -> firestore.Client:
    global _db
    if _db is None:
        project_id = os.environ.get('PROJECT_ID')
        if not project_id:
            raise ValueError("PROJECT_ID environment variable is not set")
        _db = firestore.Client(project=project_id)
    return _db


def _get_gemini():
    """Initialize Gemini with API key from Secret Manager or env."""
    try:
        import google.generativeai as genai
        api_key = os.environ.get('GEMINI_API_KEY', '')
        if not api_key:
            from secrets import secrets  # type: ignore
            api_key = secrets.GEMINI_API_KEY
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-2.0-flash-exp')
    except Exception as e:
        logger.error('Failed to initialize Gemini: %s', type(e).__name__)
        raise


def _weight_for_reputation(reputation: int) -> float:
    """Calculate vote weight based on civic reputation."""
    if reputation >= 500:
        return 1.0
    elif reputation >= 200:
        return 0.8
    elif reputation >= 100:
        return 0.6
    return 0.4


def _haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance in meters between two GPS coordinates."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _compare_photos_with_gemini(
    original_path: str,
    verification_path: str,
    project_id: str
) -> dict:
    """
    Use Gemini Vision to compare before and after photos.
    Downloads both images from Cloud Storage, sends to Gemini.
    Returns: {is_fixed, similarity_score, confidence, reasoning}
    On any error, returns {is_fixed: False, similarity_score: 0.0, confidence: 0.0}
    """
    try:
        from google.cloud import storage as gcs_storage
        import google.generativeai as genai
        import json

        model = _get_gemini()
        bucket_name = f"{project_id}.appspot.com"
        gcs_client = gcs_storage.Client(project=project_id)
        bucket = gcs_client.bucket(bucket_name)

        # Download both images (bytes)
        original_bytes = bucket.blob(original_path).download_as_bytes()
        verification_bytes = bucket.blob(verification_path).download_as_bytes()

        prompt = """Compare these two civic issue photos (before and after).
Return ONLY a JSON object with no markdown:
{
  "is_fixed": true or false,
  "similarity_score": 0.0 to 1.0,
  "confidence": 0.0 to 1.0,
  "reasoning": "one sentence explanation (max 100 chars)"
}"""

        response = model.generate_content([
            prompt,
            {"inline_data": {"mime_type": "image/jpeg", "data": original_bytes}},
            {"inline_data": {"mime_type": "image/jpeg", "data": verification_bytes}},
        ])

        raw = response.text.strip()
        # Strip markdown code blocks if present
        if raw.startswith('```'):
            lines = raw.split('\n')
            raw = '\n'.join(l for l in lines if not l.startswith('```')).strip()

        result = json.loads(raw)
        return {
            'is_fixed': bool(result.get('is_fixed', False)),
            'similarity_score': float(result.get('similarity_score', 0.0)),
            'confidence': float(result.get('confidence', 0.5)),
            'reasoning': str(result.get('reasoning', ''))[:100],
        }
    except Exception as e:
        logger.error('Gemini Vision comparison failed: %s', type(e).__name__)
        return {
            'is_fixed': False,
            'similarity_score': 0.0,
            'confidence': 0.0,
            'reasoning': 'Comparison failed.',
        }


def verify_campaign(campaign_id: str) -> dict:
    """
    Process the citizen verification for a campaign.

    Steps:
    1. Fetch campaign (must be in status 'verifying')
    2. Check 72-hour window (return pending if not expired)
    3. Fetch verification photos
    4. For each: check GPS proximity (within 50m), Gemini compare
    5. Weight votes by civic reputation
    6. If approval_rate >= 60%: close campaign, award +25 pts, update ward_scores
    7. If < 60%: reopen, flag official, auto-escalate level
    8. Audit log
    9. Return {status, campaign_id, approval_rate, weighted_score, total_verifications}
    """
    db = _get_db()
    project_id = os.environ.get('PROJECT_ID')
    if not project_id:
        raise ValueError("PROJECT_ID environment variable is not set")

    # ─── Step 1: Fetch campaign and validate status ────────────────────────────
    campaign_ref = db.collection('campaigns').document(campaign_id)
    campaign_doc = campaign_ref.get()

    if not campaign_doc.exists:
        return {'status': 'error', 'reason': 'Campaign not found.'}

    campaign_data = campaign_doc.to_dict()
    current_status = campaign_data.get('status')

    if current_status != 'verifying':
        return {
            'status': 'error',
            'reason': f'Campaign is in status {current_status!r}, expected "verifying".'
        }

    # ─── Step 2: Check 72-hour window ─────────────────────────────────────────
    verifying_since = None
    # Find when status changed to verifying from timeline
    for event in reversed(campaign_data.get('timeline', [])):
        action = event.get('action', '')
        if action == 'status_updated' or action == 'verification_started':
            try:
                ts_str = event.get('timestamp', '')
                if ts_str:
                    verifying_since = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    break
            except Exception:
                pass

    if verifying_since is None:
        # Fallback: use updated_at
        updated_at = campaign_data.get('updated_at')
        if updated_at and hasattr(updated_at, 'seconds'):
            verifying_since = datetime.fromtimestamp(updated_at.seconds, tz=timezone.utc)
        else:
            verifying_since = datetime.now(timezone.utc)

    if verifying_since.tzinfo is None:
        verifying_since = verifying_since.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    window_end = verifying_since + timedelta(hours=VERIFICATION_WINDOW_HOURS)

    if now < window_end:
        hours_remaining = (window_end - now).total_seconds() / 3600
        return {
            'status': 'pending',
            'hours_remaining': round(hours_remaining, 1),
        }

    # ─── Step 3: Fetch verification photos ────────────────────────────────────
    verification_photos = list(
        db.collection('photos')
        .where('campaign_id', '==', campaign_id)
        .where('type', '==', 'verification')
        .stream()
    )

    # Get original photo for comparison
    original_photo = None
    try:
        original_photos = list(
            db.collection('photos')
            .where('campaign_id', '==', campaign_id)
            .where('type', '!=', 'verification')
            .limit(1)
            .stream()
        )
        if original_photos:
            original_photo = original_photos[0].to_dict()
    except Exception:
        pass

    # Get campaign location for GPS proximity check
    campaign_loc = campaign_data.get('location', {})
    campaign_lat = float(campaign_loc.get('lat', 0))
    campaign_lng = float(campaign_loc.get('lng', 0))

    # ─── Steps 4-6: Weighted voting ───────────────────────────────────────────
    total_weighted_score = 0.0
    max_possible_score = 0.0
    total_verifications = 0

    for photo_doc in verification_photos:
        photo_data = photo_doc.to_dict()
        uploader_id = photo_data.get('uploader_id', '')
        photo_lat = float(photo_data.get('gps_lat', 0))
        photo_lng = float(photo_data.get('gps_lng', 0))

        # GPS proximity check: within 50 meters
        if photo_lat and photo_lng and campaign_lat and campaign_lng:
            dist = _haversine_distance(campaign_lat, campaign_lng, photo_lat, photo_lng)
            if dist > 50:
                logger.info(
                    'AUDIT verification_gps_rejected photo=%s dist=%.1fm campaign=%s',
                    photo_doc.id, dist, campaign_id
                )
                continue  # Reject: GPS too far from campaign location

        # Get civic reputation for weighting
        reputation = 0
        try:
            user_doc = db.collection('users').document(uploader_id).get()
            if user_doc.exists:
                reputation = user_doc.to_dict().get('civic_reputation', 0)
        except Exception:
            pass

        weight = _weight_for_reputation(reputation)
        max_possible_score += weight
        total_verifications += 1

        # Gemini Vision: compare before and after
        is_fixed = False
        if original_photo and original_photo.get('storagePath'):
            comparison = _compare_photos_with_gemini(
                original_photo['storagePath'],
                photo_data.get('storagePath', photo_data.get('storage_path', '')),
                project_id,
            )
            is_fixed = comparison['is_fixed']
        else:
            # No original photo for comparison — treat as verified (benefit of doubt)
            is_fixed = True

        if is_fixed:
            total_weighted_score += weight

    # Members who didn't verify count as abstaining (add minimum weight with 0 vote)
    members_count = len(list(
        db.collection('campaigns').document(campaign_id).collection('members').stream()
    ))
    abstaining = max(0, members_count - total_verifications)
    if abstaining > 0:
        # Minimum weight for abstaining members (0.4 = < 100 reputation)
        max_possible_score += abstaining * 0.4

    approval_rate = (
        total_weighted_score / max_possible_score
        if max_possible_score > 0
        else 0.0
    )

    logger.info(
        'AUDIT verification campaign=%s rate=%.2f score=%.2f max=%.2f verifications=%d',
        campaign_id, approval_rate, total_weighted_score, max_possible_score, total_verifications
    )

    now_iso = now.isoformat()

    # ─── Steps 7-9: Close or reopen ───────────────────────────────────────────
    if approval_rate >= APPROVAL_THRESHOLD:
        # CLOSE: approval rate >= 60%
        campaign_ref.update({
            'status': 'closed',
            'closed_at': firestore.SERVER_TIMESTAMP,
            'approval_rate': approval_rate,
            'timeline': firestore.ArrayUnion([{
                'action': 'verified_and_closed',
                'actor': 'system',
                'timestamp': now_iso,
                'notes': f'Citizen verification passed. Approval rate: {approval_rate:.0%}. Campaign closed.',
            }]),
        })

        # Award +25 civic reputation points to each verifier
        for photo_doc in verification_photos:
            uploader_id = photo_doc.to_dict().get('uploader_id', '')
            if uploader_id:
                try:
                    db.collection('users').document(uploader_id).update({
                        'civic_reputation': firestore.Increment(25),
                        'total_points': firestore.Increment(25),
                        'verified_reports': firestore.Increment(1),
                    })
                except Exception:
                    pass

        # Update ward_scores: increment resolved_issues
        ward_id = campaign_data.get('ward_id', '')
        if ward_id:
            try:
                db.collection('ward_scores').document(ward_id).set({
                    'resolved_issues': firestore.Increment(1),
                }, merge=True)
            except Exception:
                pass

        final_status = 'closed'

    else:
        # REOPEN: approval rate < 60%
        false_closure_count = campaign_data.get('false_closure_count', 0) + 1
        next_level = min(campaign_data.get('current_level', 1) + 1, 4)

        campaign_ref.update({
            'status': 'reopened',
            'false_closure_count': false_closure_count,
            'current_level': next_level,
            'timeline': firestore.ArrayUnion([{
                'action': 'verification_failed',
                'actor': 'system',
                'timestamp': now_iso,
                'notes': f'Citizen verification failed. Approval rate: {approval_rate:.0%}. Reopened and escalated.',
            }]),
        })

        # Flag the official: increment false_closures
        assigned_to = campaign_data.get('assigned_to')
        if assigned_to:
            try:
                db.collection('officials').document(assigned_to).update({
                    'false_closures': firestore.Increment(1),
                })
            except Exception:
                pass

        final_status = 'reopened'

    # ─── Audit log ─────────────────────────────────────────────────────────────
    try:
        db.collection('audit_logs').add({
            'event': 'verification_completed',
            'campaign_id': campaign_id,
            'final_status': final_status,
            'approval_rate': approval_rate,
            'total_verifications': total_verifications,
            'actor': 'verification_agent',
            'timestamp': firestore.SERVER_TIMESTAMP,
        })
    except Exception:
        pass

    return {
        'status': final_status,
        'campaign_id': campaign_id,
        'approval_rate': round(approval_rate, 4),
        'weighted_score': round(total_weighted_score, 2),
        'max_possible_score': round(max_possible_score, 2),
        'total_verifications': total_verifications,
    }
