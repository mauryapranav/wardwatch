'use strict';

/**
 * WardWatch - Firebase Auth Hooks
 * Handles user creation events to set up initial user documents.
 */

const functions = require('firebase-functions/v2');
const admin = require('firebase-admin');

/**
 * On new user creation: Create the user document in Firestore.
 */
exports.onUserCreated = functions.auth.onUserCreated(async (user) => {
  const uid = user.uid;

  try {
    await admin.firestore().collection('users').doc(uid).set({
      uid: uid,
      email: user.email || null,
      phone_number: user.phoneNumber || null,
      display_name: user.displayName || null,
      role: 'anonymous',
      phone_verified: false,
      civic_reputation: 0,
      total_points: 0,
      streak_days: 0,
      verified_reports: 0,
      created_at: admin.firestore.FieldValue.serverTimestamp(),
    }, { merge: true });

    console.log(`User document created for: ${uid}`);
  } catch (err) {
    console.error(`Failed to create user document for ${uid}:`, err.message);
  }
});

/**
 * On user deletion: Anonymize the user data (DPDP compliance).
 */
exports.onUserDeleted = functions.auth.onUserDeleted(async (user) => {
  const uid = user.uid;

  try {
    // Anonymize user document (do not delete — preserve civic history)
    await admin.firestore().collection('users').doc(uid).set({
      email: null,
      phone_number: null,
      display_name: 'Deleted User',
      deleted_at: admin.firestore.FieldValue.serverTimestamp(),
      is_deleted: true,
    }, { merge: true });

    // Audit log
    await admin.firestore().collection('audit_logs').add({
      event: 'user_deleted_anonymized',
      actor: uid,
      timestamp: admin.firestore.FieldValue.serverTimestamp(),
    });

    console.log(`User anonymized: ${uid}`);
  } catch (err) {
    console.error(`Failed to anonymize user ${uid}:`, err.message);
  }
});
