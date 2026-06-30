'use strict';

/**
 * WardWatch - Thread Master Trigger Cloud Function
 * Triggers on Firestore campaign document update.
 * - Fires only when citizen_count changes
 * - At count=3: sets status to acknowledged_pending, sets SLA deadline (7 days)
 * - At count=15: sets mass_issue flag
 * - When threshold met: drafts routing email and stores in escalation_log
 * - Does NOT send any emails
 */

const functions = require('firebase-functions/v2');
const admin = require('firebase-admin');

const db = admin.firestore();

const CITIZEN_THRESHOLD_LEVEL1 = 3;
const CITIZEN_THRESHOLD_MASS = 15;
const SLA_DAYS = 7;

// Approved SendGrid template IDs (5 total, as per spec)
const APPROVED_TEMPLATES = [
  'd-wardwatch-level1-001',
  'd-wardwatch-escalation-002',
  'd-wardwatch-verification-003',
  'd-wardwatch-closed-004',
  'd-wardwatch-digest-005',
];

exports.onCampaignUpdate = functions.firestore.onDocumentUpdated(
  'campaigns/{campaignId}',
  async (event) => {
    const campaignId = event.params.campaignId;
    const before = event.data.before.data();
    const after = event.data.after.data();

    // Only trigger when citizen_count changes
    if (before.citizen_count === after.citizen_count) {
      return null;
    }

    const newCount = after.citizen_count;
    const currentStatus = after.status;

    // ─── Threshold at 3: Set acknowledged_pending + SLA + routing draft ───
    if (
      newCount >= CITIZEN_THRESHOLD_LEVEL1 &&
      before.citizen_count < CITIZEN_THRESHOLD_LEVEL1 &&
      currentStatus === 'open'
    ) {
      const slaDeadline = new Date();
      slaDeadline.setDate(slaDeadline.getDate() + SLA_DAYS);

      const timelineEvent = {
        action: 'threshold_met',
        actor: 'system',
        timestamp: new Date().toISOString(),
        notes: `${CITIZEN_THRESHOLD_LEVEL1} citizens reached. SLA started.`,
      };

      try {
        await db.collection('campaigns').doc(campaignId).update({
          status: 'acknowledged_pending',
          sla_deadline: admin.firestore.Timestamp.fromDate(slaDeadline),
          current_level: 1,
          timeline: admin.firestore.FieldValue.arrayUnion(timelineEvent),
        });

        console.log(`Campaign ${campaignId}: threshold met, status set to acknowledged_pending`);

        // Audit log
        await db.collection('audit_logs').add({
          event: 'threshold_reached',
          campaign_id: campaignId,
          citizen_count: newCount,
          actor: 'thread_master_trigger',
          timestamp: admin.firestore.FieldValue.serverTimestamp(),
        });

        // Draft routing email (no send)
        await _draftRoutingEmail(campaignId, after);

      } catch (err) {
        console.error(`Failed to update campaign ${campaignId} on threshold:`, err.message);
      }
    }

    // ─── Threshold at 15: Set mass_issue flag ───
    if (
      newCount >= CITIZEN_THRESHOLD_MASS &&
      before.citizen_count < CITIZEN_THRESHOLD_MASS
    ) {
      const massTimelineEvent = {
        action: 'mass_issue_flagged',
        actor: 'system',
        timestamp: new Date().toISOString(),
        notes: `${CITIZEN_THRESHOLD_MASS} citizens reached. Flagged as mass issue.`,
      };

      try {
        await db.collection('campaigns').doc(campaignId).update({
          mass_issue: true,
          timeline: admin.firestore.FieldValue.arrayUnion(massTimelineEvent),
        });

        await db.collection('audit_logs').add({
          event: 'mass_issue_flagged',
          campaign_id: campaignId,
          citizen_count: newCount,
          actor: 'thread_master_trigger',
          timestamp: admin.firestore.FieldValue.serverTimestamp(),
        });

        console.log(`Campaign ${campaignId}: mass issue flag set at ${newCount} citizens`);
      } catch (err) {
        console.error(`Failed to set mass_issue flag for ${campaignId}:`, err.message);
      }
    }

    return null;
  }
);

/**
 * Draft a routing email and store it in escalation_log.
 * Does NOT send any email.
 */
async function _draftRoutingEmail(campaignId, campaignData) {
  try {
    // Fetch Level 1 official for this ward
    const wardId = campaignData.ward_id;
    const officialQuery = await db.collection('officials')
      .where('ward_id', '==', wardId)
      .where('level', '==', 1)
      .limit(1)
      .get();

    let officialId = null;
    let officialName = 'Ward Engineer';
    let officialEmail = `ward-engineer@${wardId}.gov.in`; // Placeholder

    if (!officialQuery.empty) {
      const officialDoc = officialQuery.docs[0];
      const officialData = officialDoc.data();
      officialId = officialDoc.id;
      officialName = officialData.name || officialName;
      officialEmail = officialData.email || officialEmail;
    }

    // Draft email data (using approved template ID)
    const templateData = {
      official_name: officialName,
      campaign_id: campaignId,
      issue_type: campaignData.issue_type,
      severity: campaignData.severity,
      ward_name: wardId,
      citizen_count: campaignData.citizen_count,
      days_open: 0,
      portal_url: `https://wardwatch-2c4fd.web.app/issues/${campaignId}`,
    };

    // Store draft in escalation_log (DO NOT SEND)
    const draftRef = await db.collection('escalation_log').add({
      campaign_id: campaignId,
      from_level: 0,
      to_level: 1,
      official_id: officialId,
      draft_data: {
        template_id: APPROVED_TEMPLATES[0], // d-wardwatch-level1-001
        template_data: templateData,
        to: officialEmail,
        cc: [],
      },
      status: 'draft',
      created_at: admin.firestore.FieldValue.serverTimestamp(),
    });

    // Update campaign: assign to official, add routing timeline event
    const updateData = {
      timeline: admin.firestore.FieldValue.arrayUnion({
        action: 'routing_drafted',
        actor: 'system',
        timestamp: new Date().toISOString(),
        notes: `Email draft created for Level 1 official: ${officialName}`,
      }),
    };
    if (officialId) {
      updateData.assigned_to = officialId;
    }

    await db.collection('campaigns').doc(campaignId).update(updateData);

    console.log(`Routing draft created: ${draftRef.id} for campaign ${campaignId}`);

    await db.collection('audit_logs').add({
      event: 'routing_drafted',
      campaign_id: campaignId,
      draft_id: draftRef.id,
      official_id: officialId,
      actor: 'thread_master_trigger',
      timestamp: admin.firestore.FieldValue.serverTimestamp(),
    });

  } catch (err) {
    console.error(`Failed to draft routing email for ${campaignId}:`, err.message);
    // Non-fatal: campaign update already succeeded
  }
}
