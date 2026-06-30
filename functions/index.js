'use strict';

/**
 * WardWatch Firebase Cloud Functions - Entry Point
 * Individual function modules are imported here.
 */

const admin = require('firebase-admin');

// Initialize Firebase Admin SDK (only once)
if (!admin.apps.length) {
  admin.initializeApp();
}

// Export individual function modules
exports.verifyAppCheck = require('./verify_app_check');
exports.photoProcessor = require('./photo_processor');
exports.verifyPhone = require('./verify_phone');
exports.verifyOfficial = require('./verify_official');
exports.threadMasterTrigger = require('./thread_master_trigger');
exports.authHooks = require('./auth_hooks');
exports.cleanup = require('./cleanup');
exports.escalation = require('./escalation');
exports.notification = require('./notification');
exports.leaderboardUpdate = require('./leaderboard_update');
