import os
import random
from datetime import datetime, timezone, timedelta
import firebase_admin
from firebase_admin import credentials, firestore

# Ensure PROJECT_ID is set or use default for hackathon
project_id = os.environ.get('PROJECT_ID', 'wardwatch-2c4fd')

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    # Use emulator if set, otherwise default credentials
    firebase_admin.initialize_app(options={'projectId': project_id})

db = firestore.client()

def create_mock_data():
    print(f"--- Creating mock data for project {project_id} ---")

    # ─── 1. Create Users ──────────────────────────────────────────────────────────
    users = [
        {
            "id": "mock_citizen_1",
            "data": {
                "role": "citizen",
                "phone_verified": True,
                "name": "Arjun Patel",
                "email": "arjun@example.com",
                "civic_reputation": 250,
                "total_points": 250,
                "created_at": firestore.SERVER_TIMESTAMP
            }
        },
        {
            "id": "mock_official_1",
            "data": {
                "role": "official",
                "ward_id": "ward_12_andheri",
                "name": "Sunita Sharma",
                "email": "sunita@mc.gov.in",
                "created_at": firestore.SERVER_TIMESTAMP
            }
        },
        {
            "id": "mock_admin_1",
            "data": {
                "role": "admin",
                "admin": True,
                "name": "System Admin",
                "email": "admin@wardwatch.app",
                "created_at": firestore.SERVER_TIMESTAMP
            }
        }
    ]

    users_created = 0
    for u in users:
        doc_ref = db.collection("users").document(u["id"])
        if not doc_ref.get().exists:
            doc_ref.set(u["data"])
            users_created += 1
            if u["data"]["role"] == "citizen":
                # Create consent record
                db.collection("consent").document(u["id"]).set({
                    "terms_accepted": True,
                    "privacy_accepted": True,
                    "timestamp": firestore.SERVER_TIMESTAMP
                })
    print(f"Users created: {users_created}")

    # ─── 2. Create Officials ──────────────────────────────────────────────────────
    officials = [
        {
            "id": "mock_official_1",
            "data": {
                "name": "Sunita Sharma",
                "ward_id": "ward_12_andheri",
                "title": "Ward Officer - Andheri East",
                "active": True,
                "created_at": firestore.SERVER_TIMESTAMP
            }
        },
        {
            "id": "mock_official_2",
            "data": {
                "name": "Rajesh Kumar",
                "ward_id": "ward_8_bandra",
                "title": "Ward Officer - Bandra",
                "active": True,
                "created_at": firestore.SERVER_TIMESTAMP
            }
        }
    ]

    officials_created = 0
    for o in officials:
        doc_ref = db.collection("officials").document(o["id"])
        if not doc_ref.get().exists:
            doc_ref.set(o["data"])
            officials_created += 1
    print(f"Officials created: {officials_created}")

    # ─── 3. Create Campaigns ──────────────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    
    campaigns = [
        {
            "id": "mock_campaign_1",
            "data": {
                "title": "Massive pothole on SV Road",
                "description": "Deep pothole causing traffic slowdowns and vehicle damage.",
                "issue_type": "pothole",
                "severity": 4,
                "status": "open",
                "ward_id": "ward_12_andheri",
                "zone_id": "zone_3",
                "location": {"lat": 19.1170, "lng": 72.8450},
                "address": "SV Road, Andheri West, Mumbai",
                "founder_id": "mock_citizen_1",
                "citizen_count": 3,
                "created_at": now - timedelta(days=1),
                "timeline": [{"action": "created", "actor": "mock_citizen_1", "timestamp": (now - timedelta(days=1)).isoformat()}]
            },
            "members": 3
        },
        {
            "id": "mock_campaign_2",
            "data": {
                "title": "Streetlights not working on Carter Road",
                "description": "Entire stretch is pitch dark at night.",
                "issue_type": "streetlight",
                "severity": 3,
                "status": "acknowledged",
                "ward_id": "ward_8_bandra",
                "zone_id": "zone_3",
                "location": {"lat": 19.0650, "lng": 72.8250},
                "address": "Carter Road, Bandra West, Mumbai",
                "founder_id": "mock_citizen_1",
                "citizen_count": 5,
                "assigned_to": "mock_official_2",
                "created_at": now - timedelta(days=3),
                "timeline": [{"action": "created", "actor": "mock_citizen_1", "timestamp": (now - timedelta(days=3)).isoformat()}]
            },
            "members": 5
        },
        {
            "id": "mock_campaign_3",
            "data": {
                "title": "Water pipe burst near station",
                "description": "Continuous water wastage for 2 days.",
                "issue_type": "water",
                "severity": 5,
                "status": "in_progress",
                "ward_id": "ward_12_andheri",
                "zone_id": "zone_3",
                "location": {"lat": 19.1190, "lng": 72.8470},
                "address": "Andheri Station Road, Mumbai",
                "founder_id": "mock_citizen_1",
                "citizen_count": 8,
                "assigned_to": "mock_official_1",
                "created_at": now - timedelta(days=2),
                "timeline": [{"action": "created", "actor": "mock_citizen_1", "timestamp": (now - timedelta(days=2)).isoformat()}]
            },
            "members": 8
        },
        {
            "id": "mock_campaign_4",
            "data": {
                "title": "Garbage dump overflow",
                "description": "Bins haven't been cleared in a week.",
                "issue_type": "garbage",
                "severity": 3,
                "status": "verifying",
                "ward_id": "ward_15_juhu",
                "zone_id": "zone_3",
                "location": {"lat": 19.1050, "lng": 72.8260},
                "address": "Juhu Tara Road, Mumbai",
                "founder_id": "mock_citizen_1",
                "citizen_count": 2,
                "created_at": now - timedelta(days=5),
                "timeline": [{"action": "created", "actor": "mock_citizen_1", "timestamp": (now - timedelta(days=5)).isoformat()}]
            },
            "members": 2
        },
        {
            "id": "mock_campaign_5",
            "data": {
                "title": "Broken sidewalk tiles",
                "description": "Dangerous for senior citizens walking here.",
                "issue_type": "sidewalk",
                "severity": 2,
                "status": "closed",
                "ward_id": "ward_12_andheri",
                "zone_id": "zone_3",
                "location": {"lat": 19.1200, "lng": 72.8500},
                "address": "Mahakali Caves Road, Andheri East, Mumbai",
                "founder_id": "mock_citizen_1",
                "citizen_count": 10,
                "assigned_to": "mock_official_1",
                "created_at": now - timedelta(days=10),
                "timeline": [{"action": "created", "actor": "mock_citizen_1", "timestamp": (now - timedelta(days=10)).isoformat()}]
            },
            "members": 10
        }
    ]

    campaigns_created = 0
    members_created = 0
    for c in campaigns:
        doc_ref = db.collection("campaigns").document(c["id"])
        if not doc_ref.get().exists:
            doc_ref.set(c["data"])
            campaigns_created += 1
            
            # Create members
            for i in range(c["members"]):
                member_id = "mock_citizen_1" if i == 0 else f"mock_member_{i}"
                db.collection("campaigns").document(c["id"]).collection("members").document(member_id).set({
                    "user_id": member_id,
                    "role": "founder" if i == 0 else "supporter",
                    "joined_at": firestore.SERVER_TIMESTAMP
                })
                members_created += 1
                
            # Create photo reference
            db.collection("photos").add({
                "campaign_id": c["id"],
                "uploader_id": "mock_citizen_1",
                "url": "https://storage.googleapis.com/wardwatch-2c4fd.firebasestorage.app/public/mock_photo.jpg",
                "photo_type": "initial",
                "uploaded_at": firestore.SERVER_TIMESTAMP
            })
            
    print(f"Campaigns created: {campaigns_created}")
    print(f"Campaign members created: {members_created}")

    # ─── 4. Create Leaderboard Entries ────────────────────────────────────────────
    leaderboard_ref = db.collection("leaderboard").document("current_month")
    if not leaderboard_ref.get().exists:
        leaderboard_ref.set({
            "month": now.strftime("%Y-%m"),
            "top_citizens": [
                {"user_id": "mock_citizen_1", "name": "Arjun Patel", "score": 250},
                {"user_id": "mock_citizen_2", "name": "Riya Singh", "score": 180},
                {"user_id": "mock_citizen_3", "name": "Karan Shah", "score": 120},
            ],
            "updated_at": firestore.SERVER_TIMESTAMP
        })
        print("Leaderboard entries created: 1")

    print("--- Mock data creation complete ---")

if __name__ == "__main__":
    create_mock_data()
