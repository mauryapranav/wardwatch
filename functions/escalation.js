'use strict';

/**
 * WardWatch - Escalation Cloud Function (Step 4.1)
 *
 * Triggered by Cloud Scheduler (HTTP) at POST /jobs/escalate.
 * Verifies User-Agent contains 'Google-Cloud-Scheduler'.
 * Queries all campaigns with breached SLA (not closed, not verifying).
 * For each: looks up next-level official, drafts escalation email in escalation_log.
 * Updates campaign: current_level++, assigned_to = new official, new SLA deadline.
 * Does NOT send any emails. Only drafts and logs.
 * Returns 200 with count of escalated campaigns.
 */

const functions = require('firebase-functions/v2');
const admin = require('firebase-admin');

const db = admin.firestore();

// Official hierarchy levels
const LEVEL_ROLES = {
  1: 'ward_engineer',
  2: 'zonal_officer',
  3: 'municipal_commissioner',
  4: 'district_collector',
};

// SLA days by escalation level (shorter at higher severity)
const SLA_DAYS_BY_LEVEL = {
  1: 7,
  2: 5,
  3: 3,
  4: 2,
};

// Approved SendGrid template IDs (must match send_agent.py)
const APPROVED_TEMPLATES = [
  'd-wardwatch-level1-001',
  'd-wardwatch-escalation-002',
  'd-wardwatch-verification-003',
  'd-wardwatch-closed-004',
  'd-wardwatch-digest-005',
];

/**
 * HTTP function triggered by Cloud Scheduler.
 * Cloud Scheduler sets User-Agent header to 'Google-Cloud-Scheduler'.
 */
exports.escalateCampaigns = functions.https.onRequest(
  { timeoutSeconds: 300, memory: '512MiB' },
  async (req, res) => {
    // Verify this request comes from Cloud Scheduler
    const userAgent = req.headers['user-agent'] || '';
    if (!userAgent.includes('Google-Cloud-Scheduler')) {
      console.warn('Rejected non-scheduler request. User-Agent:', userAgent);
      return res.status(403).json({ error: 'Forbidden' });
    }

    const now = new Date();
    let escalatedCount = 0;
    let errorCount = 0;
    const errors = [];

    try {
      // Query all campaigns with breached SLA
      // Exclude: closed (done), verifying (in citizen verification window)
      const breachedQuery = await db.collection('campaigns')
        .where('sla_deadline', '<', now)
        .where('status', 'not-in', ['closed', 'verifying'])
        .limit(100)
        .get();

      console.log(`Found ${breachedQuery.size} breached campaigns.`);

      for (const doc of breachedQuery.docs) {
        try {
          await _escalateCampaign(doc.id, doc.data(), now);
          escalatedCount++;
        } catch (err) {
          console.error(`Failed to escalate campaign ${doc.id}:`, err.message);
          errorCount++;
          errors.push({ campaign_id: doc.id, error: err.message });
        }
      }

      // Audit log
      await db.collection('audit_logs').add({
        event: 'escalation_run',
        escalated: escalatedCount,
        errors: errorCount,
        actor: 'escalation_function',
        timestamp: admin.firestore.FieldValue.serverTimestamp(),
      });

      console.log(`Escalation complete: ${escalatedCount} escalated, ${errorCount} errors.`);
      return res.status(200).json({
        escalated: escalatedCount,
        errors: errorCount,
        timestamp: now.toISOString(),
      });

    } catch (err) {
      console.error('Escalation function fatal error:', err.message);
      return res.status(500).json({ error: 'Escalation run failed.' });
    }
  }
);


/**
 * Escalate a single campaign to the next level official.
 * - Finds next level official for the campaign's ward
 * - Drafts escalation email in escalation_log (status='draft')
 * - Updates campaign: current_level, assigned_to, sla_deadline, timeline
 * - Does NOT send any email
 */
async function _escalateCampaign(campaignId, campaignData, now) {
  const currentLevel = campaignData.current_level || 1;
  const nextLevel = currentLevel + 1;
  const wardId = campaignData.ward_id;
  const isMassIssue = campaignData.mass_issue || false;

  // Max escalation: already at Level 4
  if (currentLevel >= 4) {
    console.log(`Campaign ${campaignId} already at max escalation (Level 4). Logging.`);
    await db.collection('audit_logs').add({
      event: 'max_escalation_reached',
      campaign_id: campaignId,
      current_level: currentLevel,
      actor: 'escalation_function',
      timestamp: admin.firestore.FieldValue.serverTimestamp(),
    });
    return;
  }

  // Find next-level official for this ward
  let nextOfficialId = null;
  let nextOfficialName = `Level ${nextLevel} Official`;
  let nextOfficialEmail = `level${nextLevel}-official@${wardId || 'ward'}.gov.in`;
  let currentOfficialEmail = null;

  try {
    const nextOfficialQuery = await db.collection('officials')
      .where('ward_id', '==', wardId)
      .where('level', '==', nextLevel)
      .limit(1)
      .get();

    if (!nextOfficialQuery.empty) {
      const officialDoc = nextOfficialQuery.docs[0];
      const officialData = officialDoc.data();
      nextOfficialId = officialDoc.id;
      nextOfficialName = officialData.name || nextOfficialName;
      nextOfficialEmail = officialData.email || nextOfficialEmail;
    } else {
      console.warn(`No Level ${nextLevel} official found for ward ${wardId}. Using placeholder.`);
    }

    // Get current official email for CC (if mass issue)
    if (campaignData.assigned_to) {
      const currentDoc = await db.collection('officials').doc(campaignData.assigned_to).get();
      if (currentDoc.exists) {
        currentOfficialEmail = currentDoc.data().email || null;
      }
    }
  } catch (err) {
    console.error(`Failed to fetch officials for campaign ${campaignId}:`, err.message);
    // Continue with placeholders
  }

  // Calculate days campaign has been open
  const createdAt = campaignData.created_at?.toDate?.() || now;
  const daysOpen = Math.max(0, Math.floor((now - createdAt) / (1000 * 60 * 60 * 24)));

  // Build email template data (no PII beyond official name/email)
  const templateData = {
    official_name: nextOfficialName,
    campaign_id: campaignId,
    issue_type: campaignData.issue_type || 'other',
    severity: campaignData.severity || 1,
    ward_name: wardId || 'Unknown Ward',
    citizen_count: campaignData.citizen_count || 0,
    days_open: daysOpen,
    portal_url: `https://wardwatch-2c4fd.web.app/issues/${campaignId}`,
    current_level: currentLevel,
    next_level: nextLevel,
    level_role: LEVEL_ROLES[nextLevel] || 'Official',
  };

  // CC logic: if mass issue, CC the current level official
  const ccList = [];
  if (isMassIssue && currentOfficialEmail) {
    ccList.push(currentOfficialEmail);
  }

  // Store draft in escalation_log (DO NOT SEND)
  const draftRef = await db.collection('escalation_log').add({
    campaign_id: campaignId,
    from_level: currentLevel,
    to_level: nextLevel,
    official_id: nextOfficialId,
    draft_data: {
      template_id: APPROVED_TEMPLATES[1],  // d-wardwatch-escalation-002
      template_data: templateData,
      to: nextOfficialEmail,
      cc: ccList,
    },
    status: 'draft',
    created_at: admin.firestore.FieldValue.serverTimestamp(),
  });

  // Calculate new SLA deadline (shorter for higher levels)
  const slaDays = SLA_DAYS_BY_LEVEL[nextLevel] || 7;
  const newSlaDeadline = new Date(now);
  newSlaDeadline.setDate(newSlaDeadline.getDate() + slaDays);

  // Update campaign document
  const updateData = {
    current_level: nextLevel,
    sla_deadline: admin.firestore.Timestamp.fromDate(newSlaDeadline),
    timeline: admin.firestore.FieldValue.arrayUnion({
      action: 'escalated',
      actor: 'system',
      timestamp: now.toISOString(),
      notes: `SLA breached. Escalated from Level ${currentLevel} (${LEVEL_ROLES[currentLevel]}) to Level ${nextLevel} (${LEVEL_ROLES[nextLevel] || 'Unknown'}).`,
    }),
  };

  // Assign to next official if found
  if (nextOfficialId) {
    updateData.assigned_to = nextOfficialId;
  }

  await db.collection('campaigns').doc(campaignId).update(updateData);

  // Audit log
  await db.collection('audit_logs').add({
    event: 'campaign_escalated',
    campaign_id: campaignId,
    from_level: currentLevel,
    to_level: nextLevel,
    draft_id: draftRef[1]?.id || draftRef.id,
    official_id: nextOfficialId,
    actor: 'escalation_function',
    timestamp: admin.firestore.FieldValue.serverTimestamp(),
  });

  console.log(`Campaign ${campaignId} escalated: Level ${currentLevel} → ${nextLevel} (${LEVEL_ROLES[nextLevel]}).`);
}
