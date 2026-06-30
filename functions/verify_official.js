'use strict';

/**
 * WardWatch - Official Account Verification Cloud Function
 * Callable function: verifyOfficialAccount
 * Admin-only: Sets official role and ward custom claims.
 */

const functions = require('firebase-functions/v2');
const admin = require('firebase-admin');

const VALID_ROLES = [
  'ward_engineer',
  'zonal_officer',
  'municipal_commissioner',
  'district_collector',
];

// Role hierarchy levels
const ROLE_LEVELS = {
  ward_engineer: 1,
  zonal_officer: 2,
  municipal_commissioner: 3,
  district_collector: 4,
};

/**
 * Admin-only callable function to verify an official account.
 * Sets custom claims: role, ward_id, verified_at, level
 */
exports.verifyOfficialAccount = functions.https.onCall(
  { enforceAppCheck: true },
  async (request) => {
    if (!request.auth) {
      throw new functions.https.HttpsError(
        'unauthenticated',
        'Authentication required.'
      );
    }

    // Only admins can verify officials
    if (!request.auth.token.admin) {
      throw new functions.https.HttpsError(
        'permission-denied',
        'Admin access required.'
      );
    }

    const { official_id, ward_id, role, name, email } = request.data;

    // Validate inputs
    if (!official_id || !ward_id || !role) {
      throw new functions.https.HttpsError(
        'invalid-argument',
        'official_id, ward_id, and role are required.'
      );
    }

    if (!VALID_ROLES.includes(role)) {
      throw new functions.https.HttpsError(
        'invalid-argument',
        `role must be one of: ${VALID_ROLES.join(', ')}`
      );
    }

    try {
      const level = ROLE_LEVELS[role];
      const verifiedAt = new Date().toISOString();

      // Set custom claims on the official's Firebase Auth account
      await admin.auth().setCustomUserClaims(official_id, {
        role: 'official',
        official_role: role,
        ward_id: ward_id,
        level: level,
        verified_at: verifiedAt,
      });

      // Create official document in Firestore
      await admin.firestore().collection('officials').doc(official_id).set({
        name: name || '',
        email: email || '',
        role: role,
        official_role: role,
        ward_id: ward_id,
        level: level,
        verified_at: verifiedAt,
        created_at: admin.firestore.FieldValue.serverTimestamp(),
        active_issues: 0,
        false_closures: 0,
        resolution_rate: 0.0,
      }, { merge: true });

      // Audit log
      await admin.firestore().collection('audit_logs').add({
        event: 'official_verified',
        official_id: official_id,
        role: role,
        ward_id: ward_id,
        actor: request.auth.uid,
        timestamp: admin.firestore.FieldValue.serverTimestamp(),
      });

      console.log(`Official verified: ${official_id} as ${role} for ward ${ward_id}`);
      return { status: 'success', role: role };

    } catch (err) {
      console.error(`Failed to verify official ${official_id}:`, err.message);
      throw new functions.https.HttpsError(
        'internal',
        'Verification failed. Please try again.'
      );
    }
  }
);
