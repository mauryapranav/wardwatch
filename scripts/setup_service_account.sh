#!/bin/bash
# WardWatch Service Account Setup Script
# Creates the wardwatch-api-sa service account with least-privilege roles.
# This script is idempotent - safe to run multiple times.
#
# Usage: ./setup_service_account.sh <PROJECT_ID>
# Example: ./setup_service_account.sh wardwatch-2c4fd

set -euo pipefail

PROJECT_ID="${1:-wardwatch-2c4fd}"
SA_NAME="wardwatch-api-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=== WardWatch Service Account Setup ==="
echo "Project ID: ${PROJECT_ID}"
echo "Service Account: ${SA_EMAIL}"
echo ""

# Create service account (idempotent: ignore error if already exists)
echo "[1/3] Creating service account..."
gcloud iam service-accounts create "${SA_NAME}" \
  --project="${PROJECT_ID}" \
  --display-name="WardWatch API Service Account" \
  --description="Least-privilege service account for WardWatch Cloud Run API" \
  2>/dev/null || echo "Service account already exists, skipping creation."

# Grant ONLY the 4 required roles (no roles/editor, no roles/owner)
echo "[2/3] Granting least-privilege roles..."
ROLES=(
  "roles/datastore.user"
  "roles/storage.objectAdmin"
  "roles/secretmanager.secretAccessor"
  "roles/logging.logWriter"
)

for ROLE in "${ROLES[@]}"; do
  echo "  Granting: ${ROLE}"
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${ROLE}" \
    --condition=None \
    --quiet
done

echo "[3/3] Verifying roles (should show only 4 roles)..."
gcloud projects get-iam-policy "${PROJECT_ID}" \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:${SA_EMAIL}"

echo ""
echo "=== Setup Complete ==="
echo "Service account: ${SA_EMAIL}"
echo "Roles granted: ${#ROLES[@]} (datastore.user, storage.objectAdmin, secretmanager.secretAccessor, logging.logWriter)"
echo ""
echo "IMPORTANT: Do NOT grant roles/editor or roles/owner to this service account."
echo "IMPORTANT: Use this service account for Cloud Run deployment:"
echo "  --service-account=${SA_EMAIL}"
