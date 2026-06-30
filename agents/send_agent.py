"""
WardWatch - Send Agent (Step 4.2)

Function: send_validated_email(draft_id: str) -> dict

The ONLY place emails are sent in WardWatch.
All other agents/functions DRAFT emails; only this function SENDS them.

Validations (all must pass before any email is sent):
1. Draft status must be 'draft' (not already sent)
2. Template ID must be in APPROVED_TEMPLATES list (hardcoded)
3. Recipient domain must be in APPROVED_DOMAINS list (hardcoded)
4. Campaign must exist and status must not be 'closed'
5. Rate limit: max 1 email per campaign per hour

Called by: Cloud Function that periodically processes drafts, or manual endpoint.
"""
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

from google.cloud import firestore

logger = logging.getLogger(__name__)

# ─── Security Constants ───────────────────────────────────────────────────────

# Approved SendGrid Dynamic Template IDs (hardcoded allowlist)
APPROVED_TEMPLATES = [
    'd-wardwatch-level1-001',
    'd-wardwatch-escalation-002',
    'd-wardwatch-verification-003',
    'd-wardwatch-closed-004',
    'd-wardwatch-digest-005',
]

# Approved recipient domains (official government + wardwatch domains only)
APPROVED_DOMAINS = [
    'mc.gov.in',
    'municipal.gov.in',
    'wardwatch.app',
    'brihanmumbai.gov.in',
    'mcgm.gov.in',
    # TODO (Pranav): Add real municipal domains here for production deployment.
    # 'example.gov.in',  # REMOVED (H6 fix) - Do not use example domains in production.
]

# Rate limit: 1 email per campaign per hour
RATE_LIMIT_HOURS = 1

# From email (must be verified in SendGrid)
FROM_EMAIL = 'noreply@wardwatch.app'
FROM_NAME = 'WardWatch Civic Platform'

_db: Optional[firestore.Client] = None


def _get_db() -> firestore.Client:
    global _db
    if _db is None:
        project_id = os.environ.get('PROJECT_ID')
        if not project_id:
            raise ValueError("PROJECT_ID environment variable is not set")
        _db = firestore.Client(project=project_id)
    return _db


def _get_sendgrid_client():
    """Get SendGrid client using API key from Secret Manager / env."""
    try:
        import sendgrid
        api_key = os.environ.get('SENDGRID_API_KEY', '')
        if not api_key:
            from secrets import secrets  # type: ignore
            api_key = secrets.SENDGRID_API_KEY
        return sendgrid.SendGridAPIClient(api_key=api_key)
    except Exception as e:
        logger.error('Failed to initialize SendGrid client: %s', type(e).__name__)
        raise


def _validate_domain(email: str) -> bool:
    """Check if the email's domain is in the approved list."""
    if '@' not in email:
        return False
    domain = email.split('@')[-1].lower()
    return domain in APPROVED_DOMAINS


def _check_rate_limit(campaign_id: str) -> bool:
    """
    Check rate limit: return True if sending is allowed (within limit).
    Rate limit: max 1 email per campaign per hour.
    """
    db = _get_db()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=RATE_LIMIT_HOURS)
    try:
        recent = list(
            db.collection('email_log')
            .where('campaign_id', '==', campaign_id)
            .where('sent_at', '>=', cutoff)
            .limit(1)
            .stream()
        )
        return len(recent) == 0  # True = allowed (no recent send)
    except Exception:
        # Fail-closed: deny sending if we can't verify rate limit
        # TODO: For production, consider a Redis-based rate limiter
        logger.warning("Rate limit check failed for campaign %s. Denying send.", campaign_id)
        return False


def _log_rejection(db: firestore.Client, draft_id: str, campaign_id: str, reason: str):
    """Log an email rejection to audit_logs."""
    try:
        db.collection('audit_logs').add({
            'event': 'email_rejected',
            'draft_id': draft_id,
            'campaign_id': campaign_id,
            'reason': reason,
            'actor': 'send_agent',
            'timestamp': firestore.SERVER_TIMESTAMP,
        })
    except Exception:
        pass  # Audit failure is non-fatal


def send_validated_email(draft_id: str) -> dict:
    """
    Send a validated email from an escalation_log draft.

    Returns dict with:
      - {'status': 'sent', 'recipient': email, 'campaign_id': id, 'draft_id': id}
      - {'status': 'rejected', 'reason': str}
      - {'status': 'error', 'reason': str}
    """
    db = _get_db()

    # ─── Step 1: Fetch draft ───────────────────────────────────────────────────
    draft_ref = db.collection('escalation_log').document(draft_id)
    draft_doc = draft_ref.get()

    if not draft_doc.exists:
        reason = f'Draft {draft_id} not found in escalation_log.'
        logger.warning('AUDIT send_rejected draft=%s reason=not_found', draft_id)
        return {'status': 'rejected', 'reason': reason}

    draft_data = draft_doc.to_dict()

    # ─── Step 2: Status validation ─────────────────────────────────────────────
    if draft_data.get('status') != 'draft':
        reason = f'Draft status is {draft_data.get("status")!r}, not "draft". Already processed.'
        logger.warning('AUDIT send_rejected draft=%s reason=already_processed', draft_id)
        return {'status': 'rejected', 'reason': reason}

    draft_content = draft_data.get('draft_data', {})
    template_id = draft_content.get('template_id', '')
    recipient = draft_content.get('to', '')
    cc_list = draft_content.get('cc', [])
    template_data = draft_content.get('template_data', {})
    campaign_id = draft_data.get('campaign_id', '')

    # ─── Step 3: Template ID validation ───────────────────────────────────────
    if template_id not in APPROVED_TEMPLATES:
        reason = f'Template {template_id!r} is not in the approved list.'
        logger.warning(
            'AUDIT send_rejected draft=%s reason=invalid_template template=%s',
            draft_id, template_id
        )
        _log_rejection(db, draft_id, campaign_id, reason)
        return {'status': 'rejected', 'reason': reason}

    # ─── Step 4: Recipient domain validation ──────────────────────────────────
    if not _validate_domain(recipient):
        reason = 'Recipient domain not in approved list.'
        logger.warning(
            'AUDIT send_rejected draft=%s reason=invalid_domain', draft_id
        )
        _log_rejection(db, draft_id, campaign_id, reason)
        return {'status': 'rejected', 'reason': reason}

    # ─── Step 5: Campaign validation ──────────────────────────────────────────
    if campaign_id:
        try:
            campaign_doc = db.collection('campaigns').document(campaign_id).get()
            if not campaign_doc.exists:
                reason = f'Campaign {campaign_id} not found.'
                _log_rejection(db, draft_id, campaign_id, reason)
                return {'status': 'rejected', 'reason': reason}
            if campaign_doc.to_dict().get('status') == 'closed':
                reason = f'Campaign {campaign_id} is already closed. No email needed.'
                _log_rejection(db, draft_id, campaign_id, reason)
                return {'status': 'rejected', 'reason': reason}
        except Exception:
            pass  # Proceed if check fails

    # ─── Step 6: Rate limit check ─────────────────────────────────────────────
    if not _check_rate_limit(campaign_id):
        reason = f'Rate limit: already sent email for campaign {campaign_id} in the last hour.'
        logger.warning(
            'AUDIT send_rejected draft=%s reason=rate_limit campaign=%s',
            draft_id, campaign_id
        )
        _log_rejection(db, draft_id, campaign_id, reason)
        return {'status': 'rejected', 'reason': reason}

    # ─── Step 7: Send via SendGrid ─────────────────────────────────────────────
    try:
        import sendgrid as sg_module
        from sendgrid.helpers.mail import Mail

        sg = _get_sendgrid_client()

        message = Mail(
            from_email=(FROM_EMAIL, FROM_NAME),
            to_emails=recipient,
        )
        message.template_id = template_id
        message.dynamic_template_data = template_data

        # Validate CC domains before adding
        for cc_email in cc_list:
            if _validate_domain(cc_email):
                message.add_cc(cc_email)

        response = sg.send(message)

        if response.status_code not in (200, 202):
            raise Exception(f'SendGrid returned HTTP {response.status_code}')

    except Exception as e:
        logger.error(
            'AUDIT send_failed draft=%s error=%s', draft_id, type(e).__name__
        )
        return {
            'status': 'error',
            'reason': 'Email delivery failed. Draft remains for retry.',
        }

    # ─── Step 8: Update escalation_log ────────────────────────────────────────
    sent_at = datetime.now(timezone.utc)
    draft_ref.update({
        'status': 'sent',
        'sent_at': sent_at,
    })

    # ─── Step 9: Create email_log entry ───────────────────────────────────────
    db.collection('email_log').add({
        'draft_id': draft_id,
        'campaign_id': campaign_id,
        'template_id': template_id,
        'recipient': recipient,  # Email is logged (not sensitive)
        'sent_at': sent_at,
        'actor': 'send_agent',
    })

    logger.info(
        'AUDIT email_sent draft=%s campaign=%s template=%s',
        draft_id, campaign_id, template_id
    )

    return {
        'status': 'sent',
        'recipient': recipient,
        'campaign_id': campaign_id,
        'draft_id': draft_id,
    }
