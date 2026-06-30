# WardWatch - Civic Accountability Platform

> **Transforming individual complaints into collective civic action.**

[![Firebase](https://img.shields.io/badge/Firebase-Spark%20Plan-orange)](https://firebase.google.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688)](https://fastapi.tiangolo.com)
[![Flutter](https://img.shields.io/badge/Flutter-3.3.0-blue)](https://flutter.dev)
[![Security](https://img.shields.io/badge/Security-A--%20Grade-success)](https://github.com/mauryapranav/wardwatch)

---

## Live Demo

| Component | Link | Status |
|-----------|------|--------|
| **Official Portal** | [https://wardwatch-2c4fd.web.app](https://wardwatch-2c4fd.web.app) | ✅ Live |
| **API Health** | `http://localhost:8080/health` (local backend) | ⚠️ Local |
| **GitHub Repo** | [github.com/mauryapranav/wardwatch](https://github.com/mauryapranav/wardwatch) | ✅ Public |

**Portal Demo Login:** Use `official-ward12-l1` or any official ID

---

## What Is WardWatch?

WardWatch is a **civic accountability platform** that transforms how citizens report municipal issues and how officials manage them.

**The Problem:** Citizens report potholes, broken lights, water leaks — but complaints disappear into a black hole. No transparency, no accountability, no collective power.

**The Solution:**
- Citizens report issues → **Campaigns** are created
- Other citizens **join** nearby campaigns → Collective voice
- When 3+ people join → Campaign **auto-escalates** to officials
- Officials track progress with **SLA timers** → Accountability
- Citizens **vote** on fixes → Prevents false closures
- **Gamification** (reputation, leaderboard) → Sustained engagement

---

## Features

### For Citizens (Mobile App)
- 📷 **Report issues** with photo + GPS + description
- 🗺️ **Discovery map** — see nearby campaigns on Google Maps
- 👥 **Join campaigns** — add your voice to collective action
- ✅ **Verify fixes** — vote on whether resolved issues are actually fixed
- 🏆 **Earn reputation** — points for reporting, joining, verifying
- 🔔 **Push notifications** — updates on campaigns you joined

### For Officials (Web Portal)
- 📊 **Dashboard** — all campaigns with stats and filters
- 🔄 **Status updates** — Acknowledge → Start Work → Mark Resolved
- ⏰ **SLA tracking** — deadlines and escalation warnings
- 📋 **Timeline** — full history of every campaign
- 📈 **Leaderboard** — ward performance rankings

### System Intelligence (Automation)
- 🤖 **AI Classification** — Google Gemini categorizes photos automatically
- ⚡ **Auto-escalation** — triggers when citizen threshold is met
- 📧 **Email Drafting** — two-agent pattern (draft + send with validation)
- 🔒 **EXIF Stripping** — removes GPS metadata from photos for privacy
- 📊 **Mass Issue Detection** — flags campaigns with 15+ citizens
- 🔄 **SLA Breach Escalation** — auto-escalates to next level if deadline missed
- ⏳ **72-Hour Verification** — democratic closure via citizen voting

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Mobile** | Flutter + Dart | Cross-platform citizen app |
| **Backend** | FastAPI + Python 3.12 | High-performance REST API |
| **Database** | Firebase Firestore | Real-time NoSQL database |
| **Auth** | Firebase Auth + Phone OTP | Secure authentication |
| **Storage** | Firebase Cloud Storage | Photo uploads with security rules |
| **Hosting** | Firebase Hosting | Angular portal + CDN |
| **Functions** | Firebase Cloud Functions | Serverless automation |
| **Push** | Firebase Cloud Messaging | Cross-platform notifications |
| **AI** | Google Gemini API | Image classification |
| **Maps** | Google Maps API | Location services |
| **Security** | Firebase App Check | Request validation |
| **Secrets** | Google Cloud Secret Manager | API key management |
| **Deployment** | Cloud Run + Docker | Containerized backend |

---

## Architecture

```
Flutter Mobile  ←──→  FastAPI Backend  ←──→  Firebase Firestore
     │                      │                      │
     │              Firebase Auth                  │
     │              App Check                      │
     │                      │                      │
     │              Cloud Functions                │
     │         (Photo, Escalation, AI)             │
     │                      │                      │
     └────────────→  Angular Portal  ←─────────────┘
```

---

## Security

**Internal Audit Grade: A-**

- ✅ No hardcoded secrets (Secret Manager)
- ✅ Firebase App Check on every request
- ✅ Role-based access control (citizen / official / admin)
- ✅ Firestore rules — no `allow read, write: if true` anywhere
- ✅ Storage rules — auth + MIME type + size checks
- ✅ EXIF metadata stripping from photos
- ✅ Input sanitization (XSS prevention)
- ✅ Security headers (HSTS, CSP, X-Frame-Options)
- ✅ Rate limiting per user, per endpoint
- ✅ Two-agent email validation (draft + send separation)
- ✅ Phone verification (Firebase OTP)
- ✅ DPDP-compliant consent flows
- ✅ Comprehensive audit logging

---

## Project Structure

```
wardwatch/
├── api/                          # FastAPI Backend
│   ├── main.py                   # Entry point + security headers
│   ├── auth.py                   # Firebase Auth + App Check
│   ├── config.py                 # Configuration
│   ├── secrets.py                # Secret Manager integration
│   ├── rate_limit.py             # In-memory rate limiter
│   ├── routes/
│   │   ├── issues.py             # Campaign CRUD + nearby
│   │   ├── upload.py             # Photo upload (python-magic)
│   │   ├── ai.py                 # Gemini classification
│   │   ├── officials.py          # Official status updates
│   │   ├── leaderboard.py        # Leaderboard queries
│   │   └── geo.py                # Geo endpoints
│   ├── Dockerfile                # Production container
│   └── requirements.txt          # Python dependencies
│
├── mobile/                       # Flutter Mobile App
│   ├── lib/
│   │   ├── main.dart             # App entry + App Check init
│   │   ├── screens/              # All UI screens
│   │   │   ├── onboarding_screen.dart
│   │   │   ├── auth_screen.dart
│   │   │   ├── discovery_map_screen.dart
│   │   │   ├── create_campaign_screen.dart
│   │   │   ├── campaign_detail_screen.dart
│   │   │   ├── join_campaign_screen.dart
│   │   │   ├── leaderboard_screen.dart
│   │   │   ├── profile_screen.dart
│   │   │   ├── verification_screen.dart
│   │   │   └── camera_screen.dart
│   │   ├── services/
│   │   │   ├── api_service.dart  # HTTP client + App Check token
│   │   │   └── notification_service.dart
│   │   └── widgets/
│   │       ├── escalation_timeline.dart
│   │       └── sla_countdown.dart
│   └── pubspec.yaml              # Flutter dependencies
│
├── portal/                       # Angular Official Portal
│   ├── src/
│   │   ├── app/
│   │   │   ├── dashboard/
│   │   │   ├── issue-detail/
│   │   │   ├── login/
│   │   │   ├── services/
│   │   │   └── guards/
│   │   └── environments/
│   └── angular.json
│
├── firebase/                     # Firebase Configuration
│   ├── firebase.json             # Hosting + Functions config
│   ├── firestore.rules           # Security rules (RBAC)
│   ├── firestore.indexes.json    # Composite indexes
│   └── storage.rules             # Storage security rules
│
├── functions/                    # Cloud Functions (Node.js)
│   ├── index.js                  # Entry point
│   ├── photo_processor.js        # EXIF stripping + thumbnails
│   ├── auth_hooks.js             # Custom claims on signup
│   ├── verify_phone.js           # Phone verification
│   ├── verify_official.js        # Official verification
│   ├── thread_master_trigger.js  # Threshold escalation
│   ├── escalation.js             # Email drafting
│   ├── notification.js           # FCM notifications
│   ├── leaderboard_update.js     # Leaderboard calculations
│   └── cleanup.js                # Data retention
│
├── agents/                       # Python Agents
│   ├── routing_agent.py          # Drafts escalation emails
│   ├── send_agent.py             # Sends validated emails
│   └── verification_agent.py     # 72-hour verification logic
│
└── scripts/                      # Deployment & Data
    ├── deploy.sh                 # Full deployment script
    ├── seed_mock_data.py         # Demo data (10 campaigns, 8 citizens)
    ├── mock_data.py              # Simple mock data
    └── setup_service_account.sh  # IAM setup
```

---

## Quick Start

### Prerequisites
- Node.js + npm
- Python 3.12
- Flutter SDK
- Firebase CLI: `npm install -g firebase-tools`
- Google Cloud CLI: [cloud.google.com/sdk](https://cloud.google.com/sdk)

### 1. Clone the Repository
```bash
git clone https://github.com/mauryapranav/wardwatch.git
cd wardwatch
```

### 2. Deploy Firebase Components
```bash
cd firebase
firebase login
firebase deploy --only firestore:rules,hosting
```

### 3. Run Backend Locally
```bash
cd ../api
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
set PROJECT_ID=wardwatch-2c4fd
set CORS_ORIGINS=https://wardwatch-2c4fd.web.app,https://wardwatch-2c4fd.firebaseapp.com
set ENFORCE_APP_CHECK=false
python -m uvicorn main:app --host 0.0.0.0 --port 8080
```

### 4. Seed Demo Data
```bash
cd ../scripts
set PROJECT_ID=wardwatch-2c4fd
python seed_mock_data.py
```

### 5. Build Mobile App (Optional)
```bash
cd ../mobile
flutter build apk --dart-define=API_BASE_URL=https://your-api-url.com
```

---

## Demo Data

The `seed_mock_data.py` script creates:
- **3 Wards:** Andheri East, Bandra West, Juhu
- **6 Officials:** 2 per ward (Level 1 + Level 2)
- **8 Citizens:** With varying reputation scores (30 to 1050)
- **10 Campaigns:** Realistic Mumbai civic issues
  - Open, acknowledged, in_progress, verifying, closed, escalated, reopened
- **Leaderboard entries:** Ward performance rankings
- **Escalation drafts:** Ready-to-send email templates

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PROJECT_ID` | Yes | Firebase project ID |
| `CORS_ORIGINS` | Yes | Comma-separated allowed origins |
| `ENFORCE_APP_CHECK` | Yes | `true` for prod, `false` for dev |
| `GEMINI_API_KEY` | Optional | For AI image classification |
| `SENDGRID_API_KEY` | Optional | For email sending |
| `MAPS_API_KEY` | Optional | For geocoding |

---

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check |
| `/api/v1/upload` | POST | Yes + phone | Upload photo |
| `/api/v1/ai/classify` | POST | Yes | AI image classification |
| `/api/v1/issues` | POST | Yes + phone | Create campaign |
| `/api/v1/issues/nearby` | GET | Yes | Nearby campaigns |
| `/api/v1/issues/{id}` | GET | Yes | Campaign detail |
| `/api/v1/issues/{id}/join` | POST | Yes + phone | Join campaign |
| `/api/v1/officials/{id}/issues` | GET | Yes + official | Get assigned issues |
| `/api/v1/officials/{id}/status` | PUT | Yes + official | Update status |
| `/api/v1/leaderboard` | GET | Yes | Ward rankings |

---

## Screenshots

### Official Portal
- Login page with official ID
- Dashboard with stats (10 issues, 7 active, 1 resolved)
- Campaign cards with status filters
- Timeline and action buttons
- Ward leaderboard

### Mobile App (Flutter)
- Onboarding with DPDP consent
- Firebase Phone Auth
- Discovery map with Google Maps
- Campaign creation with camera + GPS
- Join campaign screen
- Leaderboard and profile

---

## License

MIT License — See [LICENSE](LICENSE) for details.

---

## Acknowledgments

- **Google** — Firebase, Cloud Run, Gemini, Flutter, Maps
- **Vibe2Ship Hackathon** — Coding Ninjas x Google for Developers
- **Mumbai** — The city that inspired this project

---

> *"WardWatch: Because civic issues deserve collective action, not lonely complaints."*

**Built with ❤️ by Pranav Maurya for Vibe2Ship 2026**
