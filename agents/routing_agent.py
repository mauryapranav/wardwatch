"""
WardWatch - Routing Agent

Function: route_campaign(campaign_id: str) -> dict

Fetches a campaign, finds the Level 1 official for its ward, drafts a routing
email using a SendGrid Dynamic Template, stores the draft in escalation_log,
updates the campaign timeline and assigned_to field.

Does NOT send any email. Does NOT have a send_email tool.
This is a DRAFT-ONLY function.

Called by: Thread Master trigger when citizen_count reaches threshold.
"""
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

# Allow imports from api/ when running standalone
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

from google.cloud import firestore

logger = logging.getLogger(__name__)

_db: Optional[firestore.Client] = None

# Approved SendGrid Dynamic Template IDs (must match send_agent.py)
APPROVED_TEMPLATES = [
    'd-wardwatch-level1-001',
    'd-wardwatch-escalation-002',
    'd-wardwatch-verification-003',
    'd-wardwatch-closed-004',
    'd-wardwatch-digest-005',
]

PORTAL_BASE_URL = 'https://wardwatch-2c4fd.web.app'


def _get_db() -> firestore.Client:
    global _db
    if _db is None:
        project_id = os.environ.get('PROJECT_ID')
        if not project_id:
            raise ValueError("PROJECT_ID environment variable is not set")
        _db = firestore.Client(project=project_id)
    return _db


def route_campaign(campaign_id: str) -> dict:
    """
    Draft routing email for a campaign that has met the citizen threshold.

    Steps:
    1. Fetch campaign from Firestore (must exist)
    2. Fetch Level 1 official for the campaign's ward_id
    3. Build email template data
    4. Store draft in escalation_log with status='draft'
    5. Update campaign: assigned_to, timeline event
    6. Audit log
    7. Return {draft_id, official_id, official_email, campaign_id}

    Does NOT send any email.
    Returns dict with status='error' and reason on failure.
    """
    db = _get_db()

    # ─── Step 1: Fetch campaign ────────────────────────────────────────────────
    campaign_ref = db.collection('campaigns').document(campaign_id)
    campaign_doc = campaign_ref.get()

    if not campaign_doc.exists:
        reason = f'Campaign {campaign_id} not found.'
        logger.error('AUDIT routing_failed campaign=%s reason=not_found', campaign_id)
        return {'status': 'error', 'reason': reason}

    campaign_data = campaign_doc.to_dict()
    ward_id = campaign_data.get('ward_id', '')
    issue_type = campaign_data.get('issue_type', 'other')
    severity = campaign_data.get('severity', 1)
    citizen_count = campaign_data.get('citizen_count', 0)
    title = campaign_data.get('title', '')

    # Calculate days open
    created_at = campaign_data.get('created_at')
    days_open = 0
    if created_at and hasattr(created_at, 'seconds'):
        created_dt = datetime.fromtimestamp(created_at.seconds, tz=timezone.utc)
        days_open = max(0, (datetime.now(timezone.utc) - created_dt).days)

    # ─── Step 2: Fetch Level 1 official for this ward ─────────────────────────
    official_id = None
    official_name = 'Ward Engineer'
    official_email = f'ward-engineer@{ward_id}.gov.in'  # Placeholder if not found

    if not ward_id:
        logger.warning(
            'AUDIT routing_no_ward campaign=%s', campaign_id
        )
    else:
        try:
            official_query = (
                db.collection('officials')
                .where('ward_id', '==', ward_id)
                .where('level', '==', 1)
                .limit(1)
                .stream()
            )
            for official_doc in official_query:
                official_data = official_doc.to_dict()
                official_id = official_doc.id
                official_name = official_data.get('name', official_name)
                official_email = official_data.get('email', official_email)
                break

            if not official_id:
                logger.warning(
                    'AUDIT routing_no_official ward=%s campaign=%s', ward_id, campaign_id
                )

        except Exception as e:
            logger.error(
                'AUDIT routing_official_fetch_failed campaign=%s error=%s',
                campaign_id, type(e).__name__
            )

    # ─── Step 3: Build email template data ────────────────────────────────────
    template_data = {
        'official_name': official_name,
        'campaign_id': campaign_id,
        'issue_type': issue_type,
        'severity': severity,
        'ward_name': ward_id,
        'citizen_count': citizen_count,
        'days_open': days_open,
        'portal_url': f'{PORTAL_BASE_URL}/issues/{campaign_id}',
    }

    # ─── Step 4: Store draft in escalation_log (DO NOT SEND) ─────────────────
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        draft_ref = db.collection('escalation_log').add({
            'campaign_id': campaign_id,
            'from_level': 0,
            'to_level': 1,
            'official_id': official_id,
            'draft_data': {
                'template_id': APPROVED_TEMPLATES[0],  # d-wardwatch-level1-001
                'template_data': template_data,
                'to': official_email,
                'cc': [],
            },
            'status': 'draft',
            'created_at': firestore.SERVER_TIMESTAMP,
        })
        draft_id = draft_ref[1].id

    except Exception as e:
        logger.error(
            'AUDIT routing_draft_failed campaign=%s error=%s',
            campaign_id, type(e).__name__
        )
        return {
            'status': 'error',
            'reason': 'Failed to create escalation log draft.',
        }

    # ─── Step 5: Update campaign timeline and assigned_to ─────────────────────
    try:
        update_data = {
            'timeline': firestore.ArrayUnion([{
                'action': 'routing_drafted',
                'actor': 'system',
                'timestamp': now_iso,
                'notes': f'Routing draft created. Assigned to Level 1 official: {official_name}.',
            }]),
        }
        if official_id:
            update_data['assigned_to'] = official_id

        campaign_ref.update(update_data)

    except Exception as e:
        logger.error(
            'AUDIT routing_campaign_update_failed campaign=%s error=%s',
            campaign_id, type(e).__name__
        )
        # Non-fatal: draft was already created

    # ─── Step 6: Audit log ────────────────────────────────────────────────────
    try:
        db.collection('audit_logs').add({
            'event': 'routing_drafted',
            'campaign_id': campaign_id,
            'draft_id': draft_id,
            'official_id': official_id,
            'official_email_domain': official_email.split('@')[-1] if '@' in official_email else '',
            'actor': 'routing_agent',
            'timestamp': firestore.SERVER_TIMESTAMP,
        })
    except Exception:
        pass  # Audit log failure is non-fatal

    logger.info(
        'AUDIT routing_completed campaign=%s draft=%s official=%s',
        campaign_id, draft_id, official_id
    )

    # ─── Step 7: Return result ─────────────────────────────────────────────────
    return {
        'status': 'drafted',
        'draft_id': draft_id,
        'official_id': official_id,
        'official_email': official_email,
        'campaign_id': campaign_id,
        'template_id': APPROVED_TEMPLATES[0],
    }
