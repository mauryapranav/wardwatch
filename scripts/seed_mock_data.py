#!/usr/bin/env python3
"""
WardWatch - Mock Data Seeding Script (Step 5.4)

Populates Firestore with realistic demo data for the hackathon demo.
All data is synthetic. No real PII.

Usage:
    export PROJECT_ID=wardwatch-2c4fd
    python scripts/seed_mock_data.py

The script is idempotent: re-running updates existing documents.

Data created:
- 3 wards (Andheri Ward 12, Bandra Ward 8, Juhu Ward 15)
- 2 officials per ward (Ward Engineer Level 1, Zonal Officer Level 2)
- 10 campaigns with realistic Mumbai civic issues
- Members for each campaign (1-5 per campaign)
- Timeline events per campaign
- Ward score documents
- Leaderboard document

NO real API keys or PII. All phone numbers use +9198765XXXXX pattern.
"""
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

from google.cloud import firestore

PROJECT_ID = os.environ.get("PROJECT_ID", "wardwatch-2c4fd")
db = firestore.Client(project=PROJECT_ID)

# ─── Wards ────────────────────────────────────────────────────────────────────

WARDS = [
    {
        "id": "ward-12",
        "name": "Ward 12 — Andheri East",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400069",
        "boundary_center": {"lat": 19.1136, "lng": 72.8697},
    },
    {
        "id": "ward-8",
        "name": "Ward 8 — Bandra West",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400050",
        "boundary_center": {"lat": 19.0596, "lng": 72.8295},
    },
    {
        "id": "ward-15",
        "name": "Ward 15 — Juhu",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400049",
        "boundary_center": {"lat": 19.0988, "lng": 72.8261},
    },
]

# ─── Officials ────────────────────────────────────────────────────────────────

OFFICIALS = [
    # Ward 12 officials
    {
        "id": "official-ward12-l1",
        "name": "Suresh Patil",
        "email": "s.patil@mcgm.gov.in",
        "role": "ward_engineer",
        "level": 1,
        "ward_id": "ward-12",
        "active_issues": 3,
        "false_closures": 0,
    },
    {
        "id": "official-ward12-l2",
        "name": "Anita Joshi",
        "email": "a.joshi@mcgm.gov.in",
        "role": "zonal_officer",
        "level": 2,
        "ward_id": "ward-12",
        "active_issues": 1,
        "false_closures": 0,
    },
    # Ward 8 officials
    {
        "id": "official-ward8-l1",
        "name": "Rajesh Sharma",
        "email": "r.sharma@mcgm.gov.in",
        "role": "ward_engineer",
        "level": 1,
        "ward_id": "ward-8",
        "active_issues": 2,
        "false_closures": 1,
    },
    {
        "id": "official-ward8-l2",
        "name": "Meera Kulkarni",
        "email": "m.kulkarni@mcgm.gov.in",
        "role": "zonal_officer",
        "level": 2,
        "ward_id": "ward-8",
        "active_issues": 0,
        "false_closures": 0,
    },
    # Ward 15 officials
    {
        "id": "official-ward15-l1",
        "name": "Vijay Desai",
        "email": "v.desai@mcgm.gov.in",
        "role": "ward_engineer",
        "level": 1,
        "ward_id": "ward-15",
        "active_issues": 4,
        "false_closures": 0,
    },
    {
        "id": "official-ward15-l2",
        "name": "Sunita Reddy",
        "email": "s.reddy@mcgm.gov.in",
        "role": "zonal_officer",
        "level": 2,
        "ward_id": "ward-15",
        "active_issues": 1,
        "false_closures": 0,
    },
]

# ─── Mock Citizens ────────────────────────────────────────────────────────────

CITIZENS = [
    {"id": "citizen-priya", "name": "Priya Sharma", "phone": "+919876500001", "civic_reputation": 65, "streak_days": 2},
    {"id": "citizen-rahul", "name": "Rahul Gupta", "phone": "+919876500002", "civic_reputation": 40, "streak_days": 1},
    {"id": "citizen-aisha", "name": "Aisha Khan", "phone": "+919876500003", "civic_reputation": 80, "streak_days": 3},
    {"id": "citizen-vikram", "name": "Vikram Singh", "phone": "+919876500004", "civic_reputation": 220, "streak_days": 5},
    {"id": "citizen-kavya", "name": "Kavya Nair", "phone": "+919876500005", "civic_reputation": 510, "streak_days": 10},
    {"id": "citizen-mohit", "name": "Mohit Verma", "phone": "+919876500006", "civic_reputation": 150, "streak_days": 0},
    {"id": "citizen-divya", "name": "Divya Pillai", "phone": "+919876500007", "civic_reputation": 30, "streak_days": 0},
    {"id": "citizen-arjun", "name": "Arjun Menon", "phone": "+919876500008", "civic_reputation": 1050, "streak_days": 15},
]

# ─── Campaigns ────────────────────────────────────────────────────────────────

now = datetime.now(timezone.utc)

CAMPAIGNS = [
    # Ward 12 — Andheri East
    {
        "id": "campaign-4421",
        "title": "Deep Pothole Near Andheri Station Entrance",
        "description": "Large pothole (approx. 2ft wide) near the West exit of Andheri station. Causing accidents during rain.",
        "issue_type": "pothole",
        "severity": 4,
        "ward_id": "ward-12",
        "address": "Andheri Station Road, Andheri East, Mumbai 400069",
        "location": {"lat": 19.1197, "lng": 72.8471},
        "status": "acknowledged_pending",
        "founder_id": "citizen-priya",
        "citizen_count": 5,
        "current_level": 1,
        "assigned_to": "official-ward12-l1",
        "sla_deadline": now + timedelta(days=6),
        "created_at": now - timedelta(days=1),
        "mass_issue": False,
        "members": ["citizen-priya", "citizen-rahul", "citizen-aisha", "citizen-vikram", "citizen-kavya"],
        "photos": [
            {"storage_path": "campaigns/campaign-4421/photo-001.jpg", "type": "original", "uploader": "citizen-priya"},
        ],
        "timeline": [
            {"action": "created", "actor": "citizen-priya", "ts": now - timedelta(days=1), "notes": "Campaign created."},
            {"action": "citizen_joined", "actor": "citizen-rahul", "ts": now - timedelta(hours=20), "notes": ""},
            {"action": "citizen_joined", "actor": "citizen-aisha", "ts": now - timedelta(hours=18), "notes": ""},
            {"action": "citizen_joined", "actor": "citizen-vikram", "ts": now - timedelta(hours=16), "notes": ""},
            {"action": "threshold_met", "actor": "system", "ts": now - timedelta(hours=16), "notes": "3 citizens reached. SLA started."},
            {"action": "routing_drafted", "actor": "system", "ts": now - timedelta(hours=15), "notes": "Routing draft created for Ward Engineer Suresh Patil."},
            {"action": "citizen_joined", "actor": "citizen-kavya", "ts": now - timedelta(hours=10), "notes": ""},
        ],
    },
    {
        "id": "campaign-3312",
        "title": "Streetlight Out on Saki Naka Junction",
        "description": "3 consecutive streetlights not working on Saki Naka junction since past 2 weeks. Dangerous at night.",
        "issue_type": "streetlight",
        "severity": 3,
        "ward_id": "ward-12",
        "address": "Saki Naka Junction, Andheri East, Mumbai 400072",
        "location": {"lat": 19.0975, "lng": 72.8849},
        "status": "in_progress",
        "founder_id": "citizen-vikram",
        "citizen_count": 8,
        "current_level": 1,
        "assigned_to": "official-ward12-l1",
        "sla_deadline": now + timedelta(days=2),
        "created_at": now - timedelta(days=5),
        "mass_issue": False,
        "members": ["citizen-vikram", "citizen-kavya", "citizen-arjun", "citizen-divya", "citizen-mohit", "citizen-rahul", "citizen-aisha", "citizen-priya"],
        "photos": [
            {"storage_path": "campaigns/campaign-3312/photo-001.jpg", "type": "original", "uploader": "citizen-vikram"},
        ],
        "timeline": [
            {"action": "created", "actor": "citizen-vikram", "ts": now - timedelta(days=5), "notes": "Campaign created."},
            {"action": "threshold_met", "actor": "system", "ts": now - timedelta(days=5), "notes": "3 citizens reached."},
            {"action": "routing_drafted", "actor": "system", "ts": now - timedelta(days=5), "notes": "Assigned to Ward Engineer."},
            {"action": "status_updated", "actor": "official-ward12-l1", "ts": now - timedelta(days=3), "notes": "Work order issued. Electrician team deployed."},
        ],
    },
    {
        "id": "campaign-2201",
        "title": "Water Pipe Burst — Marol Naka",
        "description": "Underground water pipe burst. Road flooded. Water supply affected for 200 households.",
        "issue_type": "water",
        "severity": 5,
        "ward_id": "ward-12",
        "address": "Marol Naka, Andheri East, Mumbai 400059",
        "location": {"lat": 19.1100, "lng": 72.8781},
        "status": "closed",
        "founder_id": "citizen-arjun",
        "citizen_count": 15,
        "current_level": 1,
        "assigned_to": "official-ward12-l1",
        "sla_deadline": now - timedelta(days=2),
        "created_at": now - timedelta(days=12),
        "mass_issue": True,
        "closed_at": now - timedelta(days=1),
        "approval_rate": 0.87,
        "members": ["citizen-arjun", "citizen-kavya", "citizen-priya", "citizen-rahul", "citizen-aisha"],
        "photos": [
            {"storage_path": "campaigns/campaign-2201/photo-001.jpg", "type": "original", "uploader": "citizen-arjun"},
            {"storage_path": "campaigns/campaign-2201/verify-001.jpg", "type": "verification", "uploader": "citizen-kavya"},
        ],
        "timeline": [
            {"action": "created", "actor": "citizen-arjun", "ts": now - timedelta(days=12), "notes": "Campaign created."},
            {"action": "threshold_met", "actor": "system", "ts": now - timedelta(days=12), "notes": "Mass issue (15 citizens)."},
            {"action": "status_updated", "actor": "official-ward12-l1", "ts": now - timedelta(days=10), "notes": "Emergency repair team deployed."},
            {"action": "status_updated", "actor": "official-ward12-l1", "ts": now - timedelta(days=4), "notes": "Pipe repaired. Road restored. Water supply resumed."},
            {"action": "verified_and_closed", "actor": "system", "ts": now - timedelta(days=1), "notes": "Citizen verification passed. Approval rate: 87%. Campaign closed."},
        ],
    },
    # Ward 8 — Bandra West
    {
        "id": "campaign-5501",
        "title": "Garbage Overflowing at Hill Road Market",
        "description": "Municipal bins at Hill Road market not collected for 4 days. Severe stench. Health hazard.",
        "issue_type": "garbage",
        "severity": 4,
        "ward_id": "ward-8",
        "address": "Hill Road Market, Bandra West, Mumbai 400050",
        "location": {"lat": 19.0561, "lng": 72.8298},
        "status": "open",
        "founder_id": "citizen-kavya",
        "citizen_count": 2,
        "current_level": 0,
        "assigned_to": None,
        "sla_deadline": None,
        "created_at": now - timedelta(hours=6),
        "mass_issue": False,
        "members": ["citizen-kavya", "citizen-divya"],
        "photos": [
            {"storage_path": "campaigns/campaign-5501/photo-001.jpg", "type": "original", "uploader": "citizen-kavya"},
        ],
        "timeline": [
            {"action": "created", "actor": "citizen-kavya", "ts": now - timedelta(hours=6), "notes": "Campaign created."},
            {"action": "citizen_joined", "actor": "citizen-divya", "ts": now - timedelta(hours=4), "notes": ""},
        ],
    },
    {
        "id": "campaign-4890",
        "title": "Broken Sidewalk — Linking Road",
        "description": "Sidewalk tiles broken and uplifted near Linking Road. Elderly and differently-abled citizens at risk.",
        "issue_type": "sidewalk",
        "severity": 3,
        "ward_id": "ward-8",
        "address": "Linking Road, Bandra West, Mumbai 400050",
        "location": {"lat": 19.0607, "lng": 72.8354},
        "status": "acknowledged",
        "founder_id": "citizen-mohit",
        "citizen_count": 4,
        "current_level": 1,
        "assigned_to": "official-ward8-l1",
        "sla_deadline": now + timedelta(days=4),
        "created_at": now - timedelta(days=3),
        "mass_issue": False,
        "members": ["citizen-mohit", "citizen-aisha", "citizen-vikram", "citizen-priya"],
        "photos": [
            {"storage_path": "campaigns/campaign-4890/photo-001.jpg", "type": "original", "uploader": "citizen-mohit"},
        ],
        "timeline": [
            {"action": "created", "actor": "citizen-mohit", "ts": now - timedelta(days=3), "notes": "Campaign created."},
            {"action": "threshold_met", "actor": "system", "ts": now - timedelta(days=3), "notes": "3+ citizens joined."},
            {"action": "status_updated", "actor": "official-ward8-l1", "ts": now - timedelta(days=1), "notes": "Issue logged. Repair scheduled for next week."},
        ],
    },
    {
        "id": "campaign-6600",
        "title": "Pothole Crater on Turner Road",
        "description": "Massive pothole on Turner Road that has claimed two bicycles and caused vehicle damage.",
        "issue_type": "pothole",
        "severity": 5,
        "ward_id": "ward-8",
        "address": "Turner Road, Bandra West, Mumbai 400050",
        "location": {"lat": 19.0531, "lng": 72.8268},
        "status": "escalated",
        "founder_id": "citizen-rahul",
        "citizen_count": 20,
        "current_level": 2,
        "assigned_to": "official-ward8-l2",
        "sla_deadline": now + timedelta(days=1, hours=3),
        "created_at": now - timedelta(days=16),
        "mass_issue": True,
        "members": ["citizen-rahul", "citizen-priya", "citizen-arjun", "citizen-kavya", "citizen-vikram"],
        "photos": [
            {"storage_path": "campaigns/campaign-6600/photo-001.jpg", "type": "original", "uploader": "citizen-rahul"},
        ],
        "timeline": [
            {"action": "created", "actor": "citizen-rahul", "ts": now - timedelta(days=16), "notes": "Campaign created."},
            {"action": "threshold_met", "actor": "system", "ts": now - timedelta(days=16), "notes": "Threshold met."},
            {"action": "routing_drafted", "actor": "system", "ts": now - timedelta(days=15), "notes": "Assigned to Ward Engineer Rajesh Sharma."},
            {"action": "mass_issue_flagged", "actor": "system", "ts": now - timedelta(days=14), "notes": "20 citizens reached. Mass issue."},
            {"action": "escalated", "actor": "system", "ts": now - timedelta(days=9), "notes": "SLA breached. Escalated from Level 1 (Ward Engineer) to Level 2 (Zonal Officer)."},
        ],
    },
    # Ward 15 — Juhu
    {
        "id": "campaign-7701",
        "title": "Streetlight Failure — Juhu Beach Road",
        "description": "8 streetlights non-functional on Juhu Beach Road. Dark road attracts anti-social activity.",
        "issue_type": "streetlight",
        "severity": 3,
        "ward_id": "ward-15",
        "address": "Juhu Beach Road, Juhu, Mumbai 400049",
        "location": {"lat": 19.0927, "lng": 72.8264},
        "status": "verifying",
        "founder_id": "citizen-aisha",
        "citizen_count": 6,
        "current_level": 1,
        "assigned_to": "official-ward15-l1",
        "sla_deadline": now - timedelta(hours=2),
        "created_at": now - timedelta(days=10),
        "mass_issue": False,
        "members": ["citizen-aisha", "citizen-priya", "citizen-vikram", "citizen-mohit", "citizen-rahul", "citizen-divya"],
        "photos": [
            {"storage_path": "campaigns/campaign-7701/photo-001.jpg", "type": "original", "uploader": "citizen-aisha"},
        ],
        "timeline": [
            {"action": "created", "actor": "citizen-aisha", "ts": now - timedelta(days=10), "notes": "Campaign created."},
            {"action": "threshold_met", "actor": "system", "ts": now - timedelta(days=10), "notes": "Threshold met."},
            {"action": "status_updated", "actor": "official-ward15-l1", "ts": now - timedelta(days=5), "notes": "Lights repaired. Verification requested."},
            {"action": "status_updated", "actor": "official-ward15-l1", "ts": now - timedelta(days=5), "notes": "Status changed to verifying."},
        ],
    },
    {
        "id": "campaign-8801",
        "title": "Illegal Dumping at JVPD Scheme",
        "description": "Construction debris illegally dumped in JVPD Scheme park area. Blocking pedestrian access.",
        "issue_type": "garbage",
        "severity": 2,
        "ward_id": "ward-15",
        "address": "JVPD Scheme, Juhu, Mumbai 400049",
        "location": {"lat": 19.1018, "lng": 72.8304},
        "status": "open",
        "founder_id": "citizen-divya",
        "citizen_count": 1,
        "current_level": 0,
        "assigned_to": None,
        "sla_deadline": None,
        "created_at": now - timedelta(hours=2),
        "mass_issue": False,
        "members": ["citizen-divya"],
        "photos": [
            {"storage_path": "campaigns/campaign-8801/photo-001.jpg", "type": "original", "uploader": "citizen-divya"},
        ],
        "timeline": [
            {"action": "created", "actor": "citizen-divya", "ts": now - timedelta(hours=2), "notes": "Campaign created."},
        ],
    },
    {
        "id": "campaign-9910",
        "title": "Burst Water Pipe — Gulmohar Road",
        "description": "Burst pipe flooding the road. 3 lanes blocked. Over 500 households without water.",
        "issue_type": "water",
        "severity": 5,
        "ward_id": "ward-15",
        "address": "Gulmohar Road, Juhu, Mumbai 400049",
        "location": {"lat": 19.0893, "lng": 72.8276},
        "status": "in_progress",
        "founder_id": "citizen-arjun",
        "citizen_count": 12,
        "current_level": 1,
        "assigned_to": "official-ward15-l1",
        "sla_deadline": now + timedelta(days=3),
        "created_at": now - timedelta(days=4),
        "mass_issue": True,
        "members": ["citizen-arjun", "citizen-kavya", "citizen-priya", "citizen-mohit"],
        "photos": [
            {"storage_path": "campaigns/campaign-9910/photo-001.jpg", "type": "original", "uploader": "citizen-arjun"},
        ],
        "timeline": [
            {"action": "created", "actor": "citizen-arjun", "ts": now - timedelta(days=4), "notes": "Campaign created."},
            {"action": "threshold_met", "actor": "system", "ts": now - timedelta(days=4), "notes": "3 citizens reached."},
            {"action": "mass_issue_flagged", "actor": "system", "ts": now - timedelta(days=3), "notes": "12 citizens — flagged as mass issue."},
            {"action": "status_updated", "actor": "official-ward15-l1", "ts": now - timedelta(days=2), "notes": "Hydraulic team deployed. Expected resolution in 2 days."},
        ],
    },
    {
        "id": "campaign-0011",
        "title": "Pothole Cluster — Versova Road",
        "description": "Cluster of 5-6 potholes on Versova Road near fishing village. Motorcyclists are injured frequently.",
        "issue_type": "pothole",
        "severity": 4,
        "ward_id": "ward-15",
        "address": "Versova Road, Juhu, Mumbai 400061",
        "location": {"lat": 19.1218, "lng": 72.8111},
        "status": "reopened",
        "founder_id": "citizen-mohit",
        "citizen_count": 7,
        "current_level": 2,
        "assigned_to": "official-ward15-l2",
        "sla_deadline": now + timedelta(hours=18),
        "created_at": now - timedelta(days=21),
        "mass_issue": False,
        "false_closure_count": 1,
        "members": ["citizen-mohit", "citizen-rahul", "citizen-vikram", "citizen-aisha"],
        "photos": [
            {"storage_path": "campaigns/campaign-0011/photo-001.jpg", "type": "original", "uploader": "citizen-mohit"},
        ],
        "timeline": [
            {"action": "created", "actor": "citizen-mohit", "ts": now - timedelta(days=21), "notes": "Campaign created."},
            {"action": "threshold_met", "actor": "system", "ts": now - timedelta(days=21), "notes": "Threshold met."},
            {"action": "status_updated", "actor": "official-ward15-l1", "ts": now - timedelta(days=15), "notes": "Temporary patch applied."},
            {"action": "status_updated", "actor": "official-ward15-l1", "ts": now - timedelta(days=10), "notes": "Marked resolved."},
            {"action": "verification_failed", "actor": "system", "ts": now - timedelta(days=7), "notes": "Citizen verification failed. Approval rate: 28%. Reopened."},
            {"action": "escalated", "actor": "system", "ts": now - timedelta(days=7), "notes": "Escalated to Level 2: Zonal Officer Sunita Reddy."},
        ],
    },
]

# ─── Ward Scores ──────────────────────────────────────────────────────────────

WARD_SCORES = [
    {
        "id": "ward-12",
        "name": "Ward 12 — Andheri East",
        "total_issues": 3,
        "resolved_issues": 1,
        "resolution_rate": 0.33,
        "avg_resolution_days": 8.0,
        "citizen_participation_rate": 0.62,
    },
    {
        "id": "ward-8",
        "name": "Ward 8 — Bandra West",
        "total_issues": 3,
        "resolved_issues": 0,
        "resolution_rate": 0.0,
        "avg_resolution_days": 0.0,
        "citizen_participation_rate": 0.45,
    },
    {
        "id": "ward-15",
        "name": "Ward 15 — Juhu",
        "total_issues": 4,
        "resolved_issues": 0,
        "resolution_rate": 0.0,
        "avg_resolution_days": 0.0,
        "citizen_participation_rate": 0.38,
    },
]


def _ts(dt: datetime):
    """Convert datetime to Firestore Timestamp."""
    return dt


def seed():
    print(f"\nSeeding mock data for project: {PROJECT_ID}")
    print("=" * 60)

    # ─── Wards ───────────────────────────────────────────────────────────────
    print("\n[1/7] Seeding wards...")
    for ward in WARDS:
        db.collection("wards").document(ward["id"]).set(ward, merge=True)
        print(f"  ✓ {ward['name']}")

    # ─── Officials ───────────────────────────────────────────────────────────
    print("\n[2/7] Seeding officials...")
    for official in OFFICIALS:
        doc_data = {**official, "created_at": now - timedelta(days=30)}
        db.collection("officials").document(official["id"]).set(doc_data, merge=True)
        print(f"  ✓ {official['name']} ({official['role']}, {official['ward_id']})")

    # ─── Citizens ────────────────────────────────────────────────────────────
    print("\n[3/7] Seeding citizens...")
    for citizen in CITIZENS:
        doc_data = {
            **citizen,
            "total_points": citizen["civic_reputation"],
            "verified_reports": max(0, citizen["civic_reputation"] // 50),
            "phone_verified": True,
            "role": "citizen",
            "created_at": now - timedelta(days=60),
            "age_category": "adult",
        }
        db.collection("users").document(citizen["id"]).set(doc_data, merge=True)
        print(f"  ✓ {citizen['name']} (reputation: {citizen['civic_reputation']})")

    # ─── Campaigns ───────────────────────────────────────────────────────────
    print("\n[4/7] Seeding campaigns + members + photos...")
    for campaign in CAMPAIGNS:
        members = campaign.pop("members", [])
        photos = campaign.pop("photos", [])
        timeline = campaign.pop("timeline", [])

        # Build timeline with proper format
        formatted_timeline = []
        for event in timeline:
            formatted_timeline.append({
                "action": event["action"],
                "actor": event["actor"],
                "timestamp": event["ts"].isoformat(),
                "notes": event.get("notes", ""),
            })

        # Build campaign document
        campaign_doc = {
            **campaign,
            "timeline": formatted_timeline,
            "created_at": campaign["created_at"],
            "sla_deadline": campaign.get("sla_deadline"),
            "closed_at": campaign.get("closed_at"),
            "approval_rate": campaign.get("approval_rate"),
            "false_closure_count": campaign.get("false_closure_count", 0),
        }

        campaign_ref = db.collection("campaigns").document(campaign["id"])
        campaign_ref.set(campaign_doc, merge=True)

        # Members subcollection
        for idx, member_id in enumerate(members):
            role = "founder" if member_id == campaign["founder_id"] else "member"
            campaign_ref.collection("members").document(member_id).set({
                "user_id": member_id,
                "role": role,
                "joined_at": now - timedelta(hours=idx * 3),
            }, merge=True)

        # Photos collection
        for photo in photos:
            photo_id = f"photo-{campaign['id']}-{photo['storage_path'].split('/')[-1].split('.')[0]}"
            db.collection("photos").document(photo_id).set({
                "campaign_id": campaign["id"],
                "storage_path": photo["storage_path"],
                "storagePath": photo["storage_path"],
                "type": photo.get("type", "original"),
                "uploader_id": photo["uploader"],
                "uploaded_at": now - timedelta(hours=12),
                "exif_stripped": True,
                "processed_at": now - timedelta(hours=11),
            }, merge=True)

        print(f"  ✓ {campaign['id']}: {campaign['title'][:50]} ({campaign['status']})")

    # ─── Ward Scores ─────────────────────────────────────────────────────────
    print("\n[5/7] Seeding ward scores...")
    for score in WARD_SCORES:
        db.collection("ward_scores").document(score["id"]).set({
            **score,
            "ward_id": score["id"],
            "updated_at": now,
        }, merge=True)
        print(f"  ✓ {score['name']}: resolution_rate={score['resolution_rate']:.0%}")

    # ─── Leaderboard ─────────────────────────────────────────────────────────
    print("\n[6/7] Seeding leaderboard...")
    leaderboard_wards = sorted(
        [{"ward_id": s["id"], **s} for s in WARD_SCORES],
        key=lambda w: w["resolution_rate"],
        reverse=True,
    )
    for idx, ward in enumerate(leaderboard_wards):
        ward["rank"] = idx + 1

    db.collection("leaderboard").document("current").set({
        "wards": leaderboard_wards,
        "updated_at": now,
    }, merge=True)
    print(f"  ✓ Leaderboard created with {len(leaderboard_wards)} wards")

    # ─── Escalation log draft for campaign-4421 ──────────────────────────────
    print("\n[7/7] Seeding escalation log drafts...")
    db.collection("escalation_log").document("draft-4421-001").set({
        "campaign_id": "campaign-4421",
        "from_level": 0,
        "to_level": 1,
        "official_id": "official-ward12-l1",
        "draft_data": {
            "template_id": "d-wardwatch-level1-001",
            "template_data": {
                "official_name": "Suresh Patil",
                "campaign_id": "campaign-4421",
                "issue_type": "pothole",
                "severity": 4,
                "ward_name": "Ward 12 — Andheri East",
                "citizen_count": 5,
                "days_open": 1,
                "portal_url": "https://wardwatch-2c4fd.web.app/issues/campaign-4421",
            },
            "to": "s.patil@mcgm.gov.in",
            "cc": [],
        },
        "status": "draft",
        "created_at": now - timedelta(hours=15),
    }, merge=True)
    print("  ✓ Escalation draft for campaign-4421")

    print("\n" + "=" * 60)
    print("✅ Mock data seeding complete!")
    print(f"   Wards: {len(WARDS)}")
    print(f"   Officials: {len(OFFICIALS)}")
    print(f"   Citizens: {len(CITIZENS)}")
    print(f"   Campaigns: {len(CAMPAIGNS)}")
    print(f"\nUsage: deploy to project '{PROJECT_ID}' and run the demo script.")
    print("See DEMO_SCRIPT.md for the full demo flow.\n")


if __name__ == "__main__":
    seed()
