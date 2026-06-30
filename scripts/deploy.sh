#!/bin/bash
# WardWatch Deployment Script (Step 5.6)
# Deploys all Firebase components + Cloud Run API
# Run from workspace root: bash scripts/deploy.sh
#
# Prerequisites:
#   - gcloud CLI authenticated: gcloud auth login
#   - firebase CLI: npm install -g firebase-tools && firebase login
#   - PROJECT_ID environment variable set
#   - Docker installed (for Cloud Run)
#
# Usage:
#   export PROJECT_ID=wardwatch-2c4fd
#   bash scripts/deploy.sh [--skip-functions] [--skip-cloudrun] [--skip-hosting]

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-wardwatch-2c4fd}"
REGION="${REGION:-asia-south1}"
SERVICE_NAME="wardwatch-api"
CLOUD_RUN_SA="wardwatch-api-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# Parse flags
SKIP_FUNCTIONS=false
SKIP_CLOUDRUN=false
SKIP_HOSTING=false
for arg in "$@"; do
  case $arg in
    --skip-functions) SKIP_FUNCTIONS=true ;;
    --skip-cloudrun) SKIP_CLOUDRUN=true ;;
    --skip-hosting) SKIP_HOSTING=true ;;
  esac
done

echo "=================================================="
echo " WardWatch Deployment"
echo " Project: ${PROJECT_ID}"
echo " Region:  ${REGION}"
echo "=================================================="

# ─── Pre-flight checks ────────────────────────────────────────────────────────
info "Running pre-flight security checks..."

# No API keys in code (critical — fail if found)
if grep -r "AIza" . --exclude-dir=.git --exclude-dir=node_modules --include="*.dart" --include="*.py" --include="*.ts" --include="*.js" 2>/dev/null | grep -v ".env.example" | grep -q .; then
  error "SECURITY: Found 'AIza' pattern in source code. Remove API keys before deployment!"
fi

if grep -rE "(SENDGRID_API_KEY\s*=\s*['\"][^'\"]+['\"])" . --exclude-dir=.git --exclude-dir=node_modules 2>/dev/null | grep -q .; then
  error "SECURITY: Found hardcoded SendGrid API key. Use Secret Manager instead!"
fi

info "✅ Security checks passed."

# ─── Step 1: Deploy Firestore Rules ──────────────────────────────────────────
info "[1/6] Deploying Firestore security rules..."
cd firebase
firebase deploy --only firestore:rules --project "${PROJECT_ID}"
info "✅ Firestore rules deployed."

# ─── Step 2: Deploy Storage Rules ────────────────────────────────────────────
info "[2/6] Deploying Storage security rules..."
firebase deploy --only storage --project "${PROJECT_ID}"
info "✅ Storage rules deployed."
cd ..

# ─── Step 3: Deploy Cloud Functions ──────────────────────────────────────────
if [ "$SKIP_FUNCTIONS" = false ]; then
  info "[3/6] Installing and deploying Cloud Functions..."
  cd functions
  npm install --production
  firebase deploy --only functions --project "${PROJECT_ID}"
  cd ..
  info "✅ Cloud Functions deployed."
else
  warn "[3/6] Skipping Cloud Functions (--skip-functions)"
fi

# ─── Step 4: Deploy Cloud Run API ────────────────────────────────────────────
if [ "$SKIP_CLOUDRUN" = false ]; then
  info "[4/6] Building and deploying Cloud Run API..."
  cd api

  # Build Docker image
  IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:$(git rev-parse --short HEAD 2>/dev/null || echo latest)"
  docker build -t "${IMAGE}" .
  docker push "${IMAGE}"

  # Deploy to Cloud Run (non-root, uses service account)
  gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE}" \
    --region "${REGION}" \
    --platform managed \
    --service-account "${CLOUD_RUN_SA}" \
    --no-allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --set-env-vars "PROJECT_ID=${PROJECT_ID}" \
    --project "${PROJECT_ID}"

  cd ..
  info "✅ Cloud Run API deployed."
else
  warn "[4/6] Skipping Cloud Run (--skip-cloudrun)"
fi

# ─── Step 5: Deploy Firebase Hosting (Angular Portal) ────────────────────────
if [ "$SKIP_HOSTING" = false ]; then
  info "[5/6] Building and deploying Angular portal..."
  cd portal
  npm install
  npm run build -- --configuration=production
  cd ..
  cd firebase
  firebase deploy --only hosting --project "${PROJECT_ID}"
  cd ..
  info "✅ Firebase Hosting (portal) deployed."
else
  warn "[5/6] Skipping Firebase Hosting (--skip-hosting)"
fi

# ─── Step 6: Health verification ─────────────────────────────────────────────
info "[6/6] Verifying deployment health..."

if [ "$SKIP_CLOUDRUN" = false ]; then
  CLOUD_RUN_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --region "${REGION}" \
    --project "${PROJECT_ID}" \
    --format "value(status.url)" 2>/dev/null || echo "")

  if [ -n "${CLOUD_RUN_URL}" ]; then
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${CLOUD_RUN_URL}/health" \
      -H "Authorization: Bearer $(gcloud auth print-identity-token)" 2>/dev/null || echo "000")
    if [ "${HTTP_STATUS}" = "200" ]; then
      info "✅ Cloud Run health check: HTTP 200 ✓"
    else
      warn "⚠️  Cloud Run health check returned HTTP ${HTTP_STATUS}. Check logs."
    fi
  fi
fi

echo ""
echo "=================================================="
echo " Deployment Complete!"
echo " Project: ${PROJECT_ID}"
echo ""
echo " Portal: https://${PROJECT_ID}.web.app"
echo " API:    ${CLOUD_RUN_URL:-<check Cloud Run console>}"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  1. Verify all 22 items in DEPLOYMENT_CHECKLIST.md"
echo "  2. Run: python scripts/seed_mock_data.py"
echo "  3. Record demo following DEMO_SCRIPT.md"
echo ""
echo "Rollback (if needed):"
echo "  gcloud run services update-traffic ${SERVICE_NAME} --to-revisions=PREV=100"
