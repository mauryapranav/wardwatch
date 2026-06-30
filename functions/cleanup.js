'use strict';

/**
 * WardWatch - Cleanup Cloud Function
 * Periodic cleanup jobs for data retention compliance.
 */

const functions = require('firebase-functions/v2');
const admin = require('firebase-admin');

/**
 * Daily cleanup: Remove expired temp upload files.
 * Scheduled to run every 24 hours.
 */
exports.cleanupTempUploads = functions.scheduler.onSchedule(
  '0 2 * * *', // 2 AM daily
  async () => {
    const { Storage } = require('@google-cloud/storage');
    const gcs = new Storage();
    const db = admin.firestore();

    // Get bucket name from environment
    const bucketName = process.env.STORAGE_BUCKET || `${process.env.PROJECT_ID}.appspot.com`;
    const bucket = gcs.bucket(bucketName);

    try {
      const oneDayAgo = new Date();
      oneDayAgo.setDate(oneDayAgo.getDate() - 1);

      // List files in campaigns/temp/
      const [files] = await bucket.getFiles({ prefix: 'campaigns/temp/' });

      let deleted = 0;
      for (const file of files) {
        const [metadata] = await file.getMetadata();
        const updated = new Date(metadata.updated);
        if (updated < oneDayAgo) {
          await file.delete();
          deleted++;
        }
      }

      await db.collection('audit_logs').add({
        event: 'temp_files_cleaned',
        deleted_count: deleted,
        actor: 'cleanup_function',
        timestamp: admin.firestore.FieldValue.serverTimestamp(),
      });

      console.log(`Cleanup complete: ${deleted} temp files deleted.`);
    } catch (err) {
      console.error('Cleanup failed:', err.message);
    }
  }
);
