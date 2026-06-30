"""
WardWatch API - Firebase Auth Middleware
Verifies Firebase Auth JWT tokens and provides role-based dependency functions.

H4 Fix: Also verifies the X-Firebase-AppCheck token after Firebase Auth verification.
- App Check verification uses firebase_admin.app_check.verify_token()
- Controlled by the ENFORCE_APP_CHECK environment variable:
    * "true"  → reject requests without a valid App Check token (production)
    * "false" → skip App Check verification (local dev / emulator)
- Generic error messages only — no Firebase internals exposed to client.
"""
import logging
import os
from typing import Optional
from functools import wraps

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK (idempotent)
if not firebase_admin._apps:
    # In Cloud Run, Application Default Credentials are used automatically.
    # For local development, set GOOGLE_APPLICATION_CREDENTIALS env var.
    firebase_admin.initialize_app()

# HTTP Bearer token scheme
_bearer_scheme = HTTPBearer(auto_error=False)

# H4: App Check enforcement flag.
# Set ENFORCE_APP_CHECK=true in production Cloud Run env vars.
# Set ENFORCE_APP_CHECK=false for local development and emulator testing.
_ENFORCE_APP_CHECK = os.environ.get("ENFORCE_APP_CHECK", "false").lower() == "true"


class FirebaseUser:
    """Decoded Firebase Auth token with extracted custom claims."""
    def __init__(self, decoded_token: dict):
        self.uid: str = decoded_token.get("uid", "")
        self.role: Optional[str] = decoded_token.get("role")
        self.phone_verified: bool = decoded_token.get("phone_verified", False)
        self.admin: bool = decoded_token.get("admin", False)
        self.ward_id: Optional[str] = decoded_token.get("ward_id")
        self.system_agent: bool = decoded_token.get("system_agent", False)
        self._raw_token: dict = decoded_token

    def __repr__(self):
        return f"<FirebaseUser uid={self.uid} role={self.role}>"


async def _verify_app_check_token(request: Request) -> None:
    """
    H4: Verify the X-Firebase-AppCheck token from the request header.
    Uses firebase_admin.app_check.verify_token() — the Python SDK equivalent
    of the admin.appCheck().verifyToken() call in verify_app_check.js.

    Only enforced when ENFORCE_APP_CHECK=true (production).
    In development (ENFORCE_APP_CHECK=false), this is a no-op.
    Raises 401 if the token is missing or invalid in enforcement mode.
    """
    if not _ENFORCE_APP_CHECK:
        return  # Skip in development / emulator mode

    app_check_token = request.headers.get("X-Firebase-AppCheck")
    if not app_check_token:
        logger.warning("SECURITY App Check token missing from request path=%s", request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        from firebase_admin import app_check
        app_check.verify_token(app_check_token)
    except Exception:
        # Intentionally generic: do not expose App Check error details
        logger.warning("SECURITY App Check token invalid path=%s", request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def verify_firebase_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> "FirebaseUser":
    """
    FastAPI dependency: Verifies the Bearer token in the Authorization header.
    Also verifies the X-Firebase-AppCheck token (H4 fix) when ENFORCE_APP_CHECK=true.
    Returns a FirebaseUser if valid. Raises 401 if missing or invalid.
    Generic error messages only — no Firebase internals exposed to client.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # H4: Verify App Check token BEFORE processing the Firebase Auth token
    await _verify_app_check_token(request)

    token = credentials.credentials
    try:
        decoded = firebase_auth.verify_id_token(token, check_revoked=True)
        return FirebaseUser(decoded)
    except firebase_auth.RevokedIdTokenError:
        logger.warning("Revoked token presented.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except firebase_auth.UserDisabledError:
        logger.warning("Disabled user attempted access.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        # Intentionally generic: do not expose Firebase error details
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(role: str):
    """
    FastAPI dependency factory: Requires the user to have a specific role.
    Raises 403 if the role does not match.
    """
    async def _require_role(
        user: FirebaseUser = Depends(verify_firebase_token),
    ) -> FirebaseUser:
        if user.role != role and not user.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )
        return user
    return _require_role


async def require_official(
    user: FirebaseUser = Depends(verify_firebase_token),
) -> "FirebaseUser":
    """
    FastAPI dependency: Requires the user to have role 'official' or be admin.
    Raises 403 if not.
    """
    if user.role != "official" and not user.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions.",
        )
    return user


async def require_admin(
    user: FirebaseUser = Depends(verify_firebase_token),
) -> "FirebaseUser":
    """
    FastAPI dependency: Requires admin privileges.
    Raises 403 if not admin.
    """
    if not user.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions.",
        )
    return user


async def require_phone_verified(
    user: FirebaseUser = Depends(verify_firebase_token),
) -> "FirebaseUser":
    """
    FastAPI dependency: Requires the user's phone number to be verified.
    Raises 403 if not phone-verified.
    """
    if not user.phone_verified and not user.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phone verification required.",
        )
    return user


def get_current_user(
    user: FirebaseUser = Depends(verify_firebase_token),
) -> "FirebaseUser":
    """
    FastAPI dependency: Returns the current authenticated user.
    Alias for verify_firebase_token for semantic clarity.
    """
    return user
