'use strict';

const { initializeApp } = require('firebase-admin/app');
const { getFunctions } = require('firebase-admin/functions');
const admin = require('firebase-admin');

/**
 * Firebase App Check token verification middleware.
 * Call verifyAppCheck(req) in any callable/HTTP Cloud Function
 * before processing the request.
 */

/**
 * Verifies the App Check token on an HTTPS Callable request.
 * Throws an HttpsError if the token is missing or invalid.
 * @param {object} context - The callable function context
 */
async function verifyAppCheckCallable(context) {
  if (context.app == undefined) {
    throw new Error(
      'App Check token missing or invalid. Request rejected.'
    );
  }
  // If App Check is in debug mode during development, context.app.token
  // will still be present but with limited claims.
  // In production enforcement mode, Firebase automatically rejects
  // requests without a valid App Check token before reaching this function.
}

/**
 * Verifies the App Check token on an HTTPS Request (non-callable).
 * Returns true if valid, false if invalid.
 * @param {object} req - Express-style request object
 * @param {object} res - Express-style response object
 * @returns {boolean}
 */
async function verifyAppCheckHTTP(req, res) {
  const appCheckToken = req.header('X-Firebase-AppCheck');
  if (!appCheckToken) {
    res.status(401).json({ error: 'Unauthorized: App Check token missing' });
    return false;
  }
  try {
    await admin.appCheck().verifyToken(appCheckToken);
    return true;
  } catch (err) {
    // Do not expose internal error details
    res.status(401).json({ error: 'Unauthorized: App Check token invalid' });
    return false;
  }
}

module.exports = { verifyAppCheckCallable, verifyAppCheckHTTP };
