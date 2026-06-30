'use strict';

/**
 * WardWatch - Photo Processor Cloud Function
 * Triggers on Cloud Storage object finalize.
 * - Only processes files under campaigns/ path
 * - Validates the file is a real image using sharp
 * - Strips ALL EXIF metadata (GPS, camera info, timestamps)
 * - Generates 800x600 max thumbnail at 75% JPEG quality
 * - Saves clean image back to original path
 * - Saves thumbnail to campaigns/{campaign_id}/thumbnails/{filename}
 * - Updates Firestore /photos/{photo_id} document
 * - Logs all actions for audit
 * - Deletes non-image files and logs as security event
 */

const functions = require('firebase-functions/v2');
const admin = require('firebase-admin');
const { Storage } = require('@google-cloud/storage');
const sharp = require('sharp');
const path = require('path');

const gcs = new Storage();
const db = admin.firestore();

// Only process files under campaigns/ path
const CAMPAIGNS_PATH_PREFIX = 'campaigns/';
// Exclude thumbnails subfolder to avoid infinite loops
const EXCLUDED_PATHS = ['campaigns/temp/', 'thumbnails/'];

/**
 * Triggered when a new file is uploaded to Cloud Storage.
 */
exports.processPhoto = functions.storage.onObjectFinalized(
  { timeoutSeconds: 120, memory: '512MiB' },
  async (event) => {
    const object = event.data;
    const filePath = object.name;
    const contentType = object.contentType;
    const bucketName = object.bucket;

    // Only process files under campaigns/ (not thumbnails or other paths)
    if (!filePath.startsWith(CAMPAIGNS_PATH_PREFIX)) {
      console.log(`Skipping non-campaign file: ${filePath}`);
      return null;
    }

    // Skip if this is already a thumbnail or temp file being reprocessed
    for (const excluded of EXCLUDED_PATHS) {
      if (filePath.includes(excluded) && filePath !== filePath.replace(excluded, CAMPAIGNS_PATH_PREFIX)) {
        // More precise check: skip thumbnails subfolder
        if (filePath.includes('/thumbnails/')) {
          console.log(`Skipping thumbnail file: ${filePath}`);
          return null;
        }
      }
    }

    const bucket = gcs.bucket(bucketName);
    const fileName = path.basename(filePath);
    const dirName = path.dirname(filePath);

    // Download the image into memory
    let imageBuffer;
    try {
      const [buffer] = await bucket.file(filePath).download();
      imageBuffer = buffer;
    } catch (err) {
      console.error(`Failed to download file ${filePath}:`, err.message);
      return null;
    }

    // Validate it's a real image using sharp
    let sharpInstance;
    try {
      sharpInstance = sharp(imageBuffer);
      await sharpInstance.metadata(); // Will throw if not a valid image
    } catch (err) {
      // Not a valid image — delete immediately and log security event
      console.error(`SECURITY: Non-image file detected at ${filePath}. Deleting.`);
      await _logSecurityEvent(filePath, 'non_image_file_deleted');
      try {
        await bucket.file(filePath).delete();
        console.log(`Deleted non-image file: ${filePath}`);
      } catch (deleteErr) {
        console.error(`Failed to delete non-image file: ${deleteErr.message}`);
      }
      return null;
    }

    // Strip ALL EXIF metadata and save clean image
    let cleanImageBuffer;
    try {
      cleanImageBuffer = await sharp(imageBuffer)
        .rotate() // Auto-rotate based on EXIF orientation, then strip EXIF
        .withMetadata(false) // Remove ALL metadata (EXIF, GPS, ICC profiles, etc.)
        .toFormat('jpeg', { quality: 85 })
        .toBuffer();
    } catch (err) {
      console.error(`Failed to strip EXIF from ${filePath}:`, err.message);
      return null;
    }

    // Generate thumbnail (800x600 max, 75% JPEG quality)
    let thumbnailBuffer;
    try {
      thumbnailBuffer = await sharp(imageBuffer)
        .resize(800, 600, {
          fit: 'inside',
          withoutEnlargement: true,
        })
        .withMetadata(false) // Remove EXIF from thumbnail too
        .toFormat('jpeg', { quality: 75 })
        .toBuffer();
    } catch (err) {
      console.error(`Failed to generate thumbnail for ${filePath}:`, err.message);
      return null;
    }

    // Save clean image back to original path (overwrite)
    try {
      await bucket.file(filePath).save(cleanImageBuffer, {
        contentType: 'image/jpeg',
        metadata: {
          exifStripped: 'true',
          processedAt: new Date().toISOString(),
        },
      });
      console.log(`Clean image saved to: ${filePath}`);
    } catch (err) {
      console.error(`Failed to save clean image to ${filePath}:`, err.message);
      return null;
    }

    // Save thumbnail to campaigns/{campaign_id}/thumbnails/{filename}
    // Extract campaign_id from path: campaigns/{campaign_id}/...
    const pathParts = filePath.split('/');
    const campaignId = pathParts.length > 1 ? pathParts[1] : 'unknown';
    const thumbnailPath = `campaigns/${campaignId}/thumbnails/${fileName}`;

    try {
      await bucket.file(thumbnailPath).save(thumbnailBuffer, {
        contentType: 'image/jpeg',
        metadata: { type: 'thumbnail' },
      });
      console.log(`Thumbnail saved to: ${thumbnailPath}`);
    } catch (err) {
      console.error(`Failed to save thumbnail to ${thumbnailPath}:`, err.message);
      // Non-fatal: continue even if thumbnail fails
    }

    // Update Firestore /photos/{photo_id} document
    // photo_id is derived from the filename (without extension)
    const photoId = path.parse(fileName).name;
    const thumbnailUrl = thumbnailPath;

    try {
      const photoRef = db.collection('photos').doc(photoId);
      const photoDoc = await photoRef.get();

      const updateData = {
        exifStripped: true,
        processedAt: admin.firestore.FieldValue.serverTimestamp(),
        thumbnailUrl: thumbnailUrl,
        cleanImagePath: filePath,
      };

      if (photoDoc.exists) {
        await photoRef.update(updateData);
      } else {
        // Create the document if it doesn't exist yet
        await photoRef.set({
          ...updateData,
          storagePath: filePath,
          campaignId: campaignId === 'unknown' ? null : campaignId,
          createdAt: admin.firestore.FieldValue.serverTimestamp(),
        });
      }
      console.log(`Firestore photo document updated: ${photoId}`);
    } catch (err) {
      console.error(`Failed to update Firestore photo doc ${photoId}:`, err.message);
      // Non-fatal: log and continue
    }

    // Audit log
    await _logAuditEvent(filePath, photoId, thumbnailPath);

    console.log(`Photo processing complete for: ${filePath}`);
    return null;
  }
);

/**
 * Log a security event to Firestore audit_logs collection.
 */
async function _logSecurityEvent(filePath, eventType) {
  try {
    await db.collection('audit_logs').add({
      event: eventType,
      storagePath: filePath,
      actor: 'photo_processor_cloud_function',
      timestamp: admin.firestore.FieldValue.serverTimestamp(),
      severity: 'HIGH',
    });
  } catch (err) {
    console.error('Failed to write security audit log:', err.message);
  }
}

/**
 * Log a successful photo processing event to Firestore audit_logs.
 */
async function _logAuditEvent(filePath, photoId, thumbnailPath) {
  try {
    await db.collection('audit_logs').add({
      event: 'photo_processed',
      storagePath: filePath,
      photoId: photoId,
      thumbnailPath: thumbnailPath,
      actor: 'photo_processor_cloud_function',
      timestamp: admin.firestore.FieldValue.serverTimestamp(),
      severity: 'INFO',
    });
  } catch (err) {
    console.error('Failed to write audit log:', err.message);
  }
}
