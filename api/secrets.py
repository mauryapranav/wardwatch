"""
WardWatch API - Secret Manager Integration
Fetches secrets from Google Cloud Secret Manager.
Falls back to .env.example placeholder detection in development.

CRITICAL SECURITY RULES:
- Never log or print secret values
- Never store secrets in environment variables
- Never commit secrets to git
"""
import os
import logging
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)


def _get_secret_manager_client():
    """Create and return a Secret Manager client."""
    from google.cloud import secretmanager
    return secretmanager.SecretManagerServiceClient()


def get_secret(secret_id: str, project_id: Optional[str] = None) -> str:
    """
    Fetch the latest version of a secret from Google Cloud Secret Manager.

    Args:
        secret_id: The secret's resource name (e.g., 'gemini-api-key')
        project_id: GCP project ID. Defaults to PROJECT_ID env var.

    Returns:
        The secret value as a string.

    Raises:
        RuntimeError: If the secret cannot be fetched.

    IMPORTANT: Never log the returned value.
    """
    if project_id is None:
        project_id = os.environ.get("PROJECT_ID", "")

    if not project_id:
        raise RuntimeError(
            f"Cannot fetch secret '{secret_id}': PROJECT_ID not set. "
            "Set the PROJECT_ID environment variable."
        )

    try:
        client = _get_secret_manager_client()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        value = response.payload.data.decode("utf-8").strip()
        logger.info(f"Successfully fetched secret: {secret_id}")
        # NEVER log the value itself
        return value
    except Exception as e:
        # Generic error — do not expose secret details in the error message
        logger.error(f"Failed to fetch secret '{secret_id}': {type(e).__name__}")
        raise RuntimeError(
            f"Failed to load required secret: {secret_id}. "
            "Ensure the secret exists in Secret Manager and the service account "
            "has roles/secretmanager.secretAccessor."
        ) from None


class _Secrets:
    """
    Lazy-loaded secrets container.
    Secrets are fetched on first access, not at import time.
    This allows the module to be imported without network access during testing.
    """
    _cache: dict = {}
    _loaded: bool = False

    REQUIRED_SECRETS = [
        "gemini-api-key",
        "sendgrid-api-key",
        "maps-api-key",
    ]

    def _load_all(self):
        """Load all required secrets from Secret Manager."""
        if self._loaded:
            return
        missing = []
        for secret_name in self.REQUIRED_SECRETS:
            try:
                self._cache[secret_name] = get_secret(secret_name)
            except RuntimeError:
                missing.append(secret_name)
        if missing:
            raise RuntimeError(
                f"Required secrets missing from Secret Manager: {missing}. "
                "Please create these secrets before starting the API."
            )
        self._loaded = True
        logger.info("All required secrets loaded successfully.")

    @property
    def GEMINI_API_KEY(self) -> str:
        self._load_all()
        return self._cache["gemini-api-key"]

    @property
    def SENDGRID_API_KEY(self) -> str:
        self._load_all()
        return self._cache["sendgrid-api-key"]

    @property
    def MAPS_API_KEY(self) -> str:
        self._load_all()
        return self._cache["maps-api-key"]


# Module-level singleton
secrets = _Secrets()
