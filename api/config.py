"""
WardWatch API Configuration
Reads PROJECT_ID from environment variable.
All secrets are fetched from Google Cloud Secret Manager.
"""
import os
import logging

logger = logging.getLogger(__name__)

# ─── Non-secret configuration from environment ────────────────────────────────
PROJECT_ID: str = os.environ.get("PROJECT_ID", "")

if not PROJECT_ID:
    logger.warning(
        "PROJECT_ID environment variable not set. "
        "This is required for Cloud Run deployment."
    )

# API version prefix
API_V1_PREFIX = "/api/v1"

# App version
APP_VERSION = "2.0.0"
APP_NAME = "WardWatch API"
