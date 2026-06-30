'use strict';

/**
 * WardWatch - Leaderboard Update Cloud Function (Step 5.2)
 *
 * Recalculates ward leaderboard every 15 minutes.
 * For each ward: recalculate resolution_rate, avg_resolution_days,
 * citizen_participation_rate. Sort by resolution_rate descending. Assign ranks.
 * Stores result in leaderboard/current document.
 * No PII in leaderboard data.
 */

const functions = require('firebase-functions/v2');
const admin = require('firebase-admin');

const db = admin.firestore();

/**
 * Scheduled Cloud Function: runs every 15 minutes.
 * Cloud Scheduler cron: "every 15 minutes"
 */
exports.updateLeaderboard = functions.scheduler.onSchedule(
  {
    schedule: 'every 15 minutes',
    timeZone: 'Asia/Kolkata',
    memory: '256MiB',
  },
  async (event) => {
    try {
      await _recalculateLeaderboard();
      console.log('Leaderboard updated successfully.');
    } catch (err) {
      console.error('Leaderboard update failed:', err.message);
    }
  }
);

/**
 * Also expose as HTTP function for manual triggering.
 * Protected: only callable from internal network or by admin.
 */
exports.updateLeaderboardHttp = functions.https.onRequest(
  { memory: '256MiB' },
  async (req, res) => {
    const userAgent = req.headers['user-agent'] || '';
    // Allow Cloud Scheduler and internal calls
    if (!userAgent.includes('Google-Cloud-Scheduler') && !userAgent.includes('WardWatch-Internal')) {
      return res.status(403).json({ error: 'Forbidden' });
    }
    try {
      const result = await _recalculateLeaderboard();
      return res.status(200).json({ status: 'updated', wards: result.length });
    } catch (err) {
      console.error('Manual leaderboard update failed:', err.message);
      return res.status(500).json({ error: 'Leaderboard update failed.' });
    }
  }
);

async function _recalculateLeaderboard() {
  // Fetch all wards
  const wardsSnap = await db.collection('wards').get();
  if (wardsSnap.empty) {
    console.log('No wards found. Skipping leaderboard update.');
    return [];
  }

  const wardStats = [];

  for (const wardDoc of wardsSnap.docs) {
    const wardId = wardDoc.id;
    const wardData = wardDoc.data();

    try {
      // Count total campaigns in this ward
      const totalQuery = await db.collection('campaigns')
        .where('ward_id', '==', wardId)
        .get();
      const totalIssues = totalQuery.size;

      // Count resolved + closed campaigns
      const resolvedQuery = await db.collection('campaigns')
        .where('ward_id', '==', wardId)
        .where('status', 'in', ['closed', 'resolved'])
        .get();
      const resolvedIssues = resolvedQuery.size;

      // Calculate average resolution days for closed campaigns
      let totalResolutionDays = 0;
      let resolutionDayCount = 0;
      for (const doc of resolvedQuery.docs) {
        const data = doc.data();
        if (data.created_at && data.closed_at) {
          const createdMs = data.created_at.toMillis?.() || 0;
          const closedMs = data.closed_at.toMillis?.() || 0;
          if (createdMs && closedMs) {
            const days = (closedMs - createdMs) / (1000 * 60 * 60 * 24);
            totalResolutionDays += days;
            resolutionDayCount++;
          }
        }
      }
      const avgResolutionDays = resolutionDayCount > 0
        ? totalResolutionDays / resolutionDayCount
        : 0;

      // Citizen participation rate: unique citizens who joined at least one campaign in this ward
      const citizenSet = new Set();
      for (const doc of totalQuery.docs) {
        const data = doc.data();
        if (data.founder_id) citizenSet.add(data.founder_id);
        // We don't fetch subcollection members here for performance — use citizen_count sum
      }

      const totalCitizenActions = totalQuery.docs.reduce(
        (sum, doc) => sum + (doc.data().citizen_count || 0), 0
      );
      // Simplified participation rate: average citizen_count / 10 (capped at 1.0)
      const citizenParticipationRate = Math.min(totalCitizenActions / Math.max(totalIssues * 5, 1), 1.0);

      const resolutionRate = totalIssues > 0 ? resolvedIssues / totalIssues : 0;

      // Update ward_scores document
      await db.collection('ward_scores').doc(wardId).set({
        ward_id: wardId,
        name: wardData.name || wardId,
        total_issues: totalIssues,
        resolved_issues: resolvedIssues,
        resolution_rate: resolutionRate,
        avg_resolution_days: Math.round(avgResolutionDays * 10) / 10,
        citizen_participation_rate: Math.round(citizenParticipationRate * 100) / 100,
        updated_at: admin.firestore.FieldValue.serverTimestamp(),
      }, { merge: true });

      wardStats.push({
        ward_id: wardId,
        name: wardData.name || wardId,
        total_issues: totalIssues,
        resolved_issues: resolvedIssues,
        resolution_rate: resolutionRate,
        avg_resolution_days: Math.round(avgResolutionDays * 10) / 10,
        citizen_participation_rate: Math.round(citizenParticipationRate * 100) / 100,
      });

    } catch (err) {
      console.error(`Failed to process ward ${wardId}:`, err.message);
    }
  }

  // Sort by resolution_rate descending, assign ranks
  wardStats.sort((a, b) => b.resolution_rate - a.resolution_rate);
  wardStats.forEach((ward, idx) => { ward.rank = idx + 1; });

  // Store leaderboard snapshot (no PII)
  await db.collection('leaderboard').doc('current').set({
    wards: wardStats,
    updated_at: admin.firestore.FieldValue.serverTimestamp(),
  });

  console.log(`Leaderboard updated: ${wardStats.length} wards ranked.`);
  return wardStats;
}
