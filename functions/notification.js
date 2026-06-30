'use strict';

/**
 * WardWatch - FCM Notification Cloud Function (Step 4.3)
 *
 * Triggers on Firestore campaign document update.
 * When status changes, sends FCM push notification to all campaign members.
 * Does NOT include sensitive data (addresses, GPS, citizen names) in notification body.
 * Handles batch sends (up to 500 members).
 * Invalid/missing FCM tokens are logged and skipped (don't fail other notifications).
 * Also exports Flutter FCM setup notes.
 */

const functions = require('firebase-functions/v2');
const admin = require('firebase-admin');

const db = admin.firestore();

exports.onCampaignStatusChange = functions.firestore.onDocumentUpdated(
  'campaigns/{campaignId}',
  async (event) => {
    const campaignId = event.params.campaignId;
    const before = event.data.before.data();
    const after = event.data.after.data();

    // Only trigger when status changes
    if (before.status === after.status) {
      return null;
    }

    const newStatus = after.status;
    // Use campaign title for notification — NOT address, GPS, or citizen names
    const campaignTitle = after.title || 'Campaign';

    // Fetch all member documents from subcollection
    const membersRef = db.collection('campaigns').doc(campaignId).collection('members');
    const membersSnap = await membersRef.get();

    if (membersSnap.empty) {
      console.log(`No members for campaign ${campaignId}.`);
      return null;
    }

    // Collect FCM tokens from all members
    const BATCH_SIZE = 500;  // FCM multicast limit
    const tokens = [];
    let missingTokenCount = 0;

    for (const memberDoc of membersSnap.docs) {
      const memberData = memberDoc.data();
      const userId = memberData.user_id || memberDoc.id;
      try {
        const userDoc = await db.collection('users').doc(userId).get();
        if (userDoc.exists) {
          const fcmToken = userDoc.data().fcm_token;
          if (fcmToken) {
            tokens.push({ token: fcmToken, userId });
          } else {
            missingTokenCount++;
          }
        }
      } catch (err) {
        // Log and continue — don't fail other notifications
        console.error(`Failed to get FCM token for user ${userId}:`, err.message);
        missingTokenCount++;
      }
    }

    if (tokens.length === 0) {
      console.log(`No valid FCM tokens for campaign ${campaignId}. Missing: ${missingTokenCount}.`);
      return null;
    }

    let totalSent = 0;
    let totalFailed = 0;

    // Send in batches of BATCH_SIZE
    for (let i = 0; i < tokens.length; i += BATCH_SIZE) {
      const batch = tokens.slice(i, i + BATCH_SIZE);
      const tokenStrings = batch.map(t => t.token);

      // Notification body: generic status message ONLY
      // NO addresses, NO exact GPS, NO citizen names (other than recipient's own name which is not included)
      const message = {
        notification: {
          title: `Campaign Update: ${campaignTitle.substring(0, 50)}`,
          body: `Status changed to ${newStatus.replace(/_/g, ' ')}.`,
        },
        data: {
          campaign_id: campaignId,
          action: 'status_change',
          status: newStatus,
          // No addresses, no GPS, no PII
        },
        tokens: tokenStrings,
      };

      try {
        const response = await admin.messaging().sendEachForMulticast(message);
        totalSent += response.successCount;
        totalFailed += response.failureCount;

        // Log failed tokens (for cleanup purposes — invalid/expired tokens)
        if (response.failureCount > 0) {
          response.responses.forEach((resp, idx) => {
            if (!resp.success) {
              // Do not log the actual token (privacy)
              console.warn(
                `FCM send failed for campaign ${campaignId}. Error code: ${resp.error?.code}`
              );
            }
          });
        }
      } catch (err) {
        console.error(`FCM batch send failed for campaign ${campaignId}:`, err.message);
        totalFailed += batch.length;
      }
    }

    // Audit log (no sensitive data)
    try {
      await db.collection('audit_logs').add({
        event: 'fcm_notifications_sent',
        campaign_id: campaignId,
        new_status: newStatus,
        tokens_found: tokens.length,
        tokens_missing: missingTokenCount,
        sent: totalSent,
        failed: totalFailed,
        actor: 'notification_function',
        timestamp: admin.firestore.FieldValue.serverTimestamp(),
      });
    } catch (err) {
      console.error('Failed to write audit log:', err.message);
    }

    console.log(
      `Notifications for campaign ${campaignId}: sent=${totalSent}, failed=${totalFailed}, missing_tokens=${missingTokenCount}`
    );
    return null;
  }
);

/*
 * ─── Flutter FCM Setup Reference ──────────────────────────────────────────────
 *
 * The Flutter FCM initialization is in:
 *   mobile/lib/services/notification_service.dart
 *
 * Key setup steps:
 * 1. Initialize Firebase Messaging in main.dart (already done)
 * 2. NotificationService.initialize():
 *    - Requests notification permission (iOS + Android 13+)
 *    - Gets FCM token and stores in Firestore users/{uid}/fcm_token
 *    - Handles foreground messages (shows local notification)
 *    - Handles background/terminated messages via onBackgroundMessage
 *    - On notification tap: navigates to CampaignDetailScreen
 * 3. FCM token refresh: FirebaseMessaging.onTokenRefresh updates Firestore
 *
 * See mobile/lib/services/notification_service.dart for full implementation.
 */
