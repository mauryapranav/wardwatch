'use strict';

/**
 * WardWatch - Phone Verification Cloud Function
 * Callable function: verifyPhoneAndUpgradeRole
 * Called after successful Firebase Phone OTP verification.
 * Sets custom claims: phone_verified=true, role='citizen'
 */

const functions = require('firebase-functions/v2');
const admin = require('firebase-admin');

/**
 * Callable Cloud Function to set phone_verified custom claim.
 * Called from Flutter after successful OTP verification.
 */
exports.verifyPhoneAndUpgradeRole = functions.https.onCall(
  { enforceAppCheck: true },
  async (request) => {
    if (!request.auth) {
      throw new functions.https.HttpsError(
        'unauthenticated',
        'Authentication required.'
      );
    }

    const uid = request.auth.uid;

    try {
      // Set custom claims: phone_verified and role
      await admin.auth().setCustomUserClaims(uid, {
        phone_verified: true,
        role: 'citizen',
        ...request.auth.token, // Preserve existing claims
        // Explicitly set these to ensure they're present
        phone_verified: true,
        role: 'citizen',
      });

      // Create/update user document in Firestore
      await admin.firestore().collection('users').doc(uid).set({
        role: 'citizen',
        phone_verified: true,
        updated_at: admin.firestore.FieldValue.serverTimestamp(),
      }, { merge: true });

      // Audit log
      await admin.firestore().collection('audit_logs').add({
        event: 'phone_verified',
        actor: uid,
        timestamp: admin.firestore.FieldValue.serverTimestamp(),
      });

      console.log(`Phone verified for user: ${uid}`);
      return { status: 'success', role: 'citizen' };

    } catch (err) {
      console.error(`Failed to set phone_verified claim for ${uid}:`, err.message);
      throw new functions.https.HttpsError(
        'internal',
        'Verification failed. Please try again.'
      );
    }
  }
);
