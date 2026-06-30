"""
WardWatch API - Main Entry Point

Registers all API routers for all phases.
Production-ready: no debug endpoints, no hardcoded secrets.
"""
import logging
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from config import APP_NAME, APP_VERSION, API_V1_PREFIX

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

# ─── FastAPI Application ──────────────────────────────────────────────────────
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    docs_url=None,       # Disabled in production
    redoc_url=None,      # Disabled in production
    openapi_url=None,    # Disabled in production
)


# ─── H5: Security Headers Middleware ─────────────────────────────────────────
# Injects HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy,
# and Permissions-Policy headers on every response.
# Header values from Final Plan Part 6.
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://apis.google.com; "
            "img-src 'self' https://*.googleapis.com data:; "
            "connect-src 'self' https://*.googleapis.com https://*.firebaseio.com"
        )
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(self), camera=(self)"
        return response


app.add_middleware(SecurityHeadersMiddleware)


# ─── H1: CORS — Configurable origins, no localhost in production ──────────────
# CORS origins are read from the CORS_ORIGINS environment variable (comma-separated).
# If not set, defaults to the production Firebase Hosting domains only.
# localhost is NEVER included unless explicitly added via CORS_ORIGINS in dev.
_cors_env = os.environ.get("CORS_ORIGINS", "")
if _cors_env.strip():
    _cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]
else:
    # Production default: Firebase Hosting domains only. No localhost.
    _cors_origins = [
        "https://wardwatch-2c4fd.web.app",
        "https://wardwatch-2c4fd.firebaseapp.com",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Firebase-AppCheck"],
)


# ─── Health Endpoint ──────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run readiness/liveness probes."""
    return {"status": "healthy", "version": APP_VERSION}


# ─── API Routers (Phase 1-5) ─────────────────────────────────────────────────
# from routes.upload import router as upload_router
from routes.ai import router as ai_router
from routes.issues import router as issues_router
from routes.officials import router as officials_router
from routes.leaderboard import router as leaderboard_router
from routes.geo import router as geo_router

# app.include_router(upload_router, prefix=API_V1_PREFIX)
app.include_router(ai_router, prefix=API_V1_PREFIX)
app.include_router(issues_router, prefix=API_V1_PREFIX)
app.include_router(officials_router, prefix=API_V1_PREFIX)
app.include_router(leaderboard_router, prefix=API_V1_PREFIX)
app.include_router(geo_router, prefix=API_V1_PREFIX)

logger.info("WardWatch API started. Version: %s", APP_VERSION)
