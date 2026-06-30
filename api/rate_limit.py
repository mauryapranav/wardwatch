"""
WardWatch API - In-Memory Rate Limiter
Simple sliding window rate limiter using in-memory counters.

# H2: WARNING: This in-memory rate limiter is PER-INSTANCE.
# With multiple Cloud Run instances, rate limits are easily bypassed because state is not shared.
# For production, replace this with Redis / Cloud Memorystore.
"""
import time
import logging
from collections import defaultdict, deque
from threading import Lock
from typing import Tuple

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Thread-safe storage: {(user_id, endpoint): deque of timestamps}
_request_log: dict = defaultdict(deque)
_lock = Lock()


def check_rate_limit(
    user_id: str,
    endpoint: str,
    max_requests: int,
    window_seconds: int = 60,
) -> None:
    """
    Check if the user has exceeded the rate limit for an endpoint.
    Raises HTTP 429 if the limit is exceeded.

    Args:
        user_id: Firebase UID of the user
        endpoint: Endpoint identifier (e.g., 'upload', 'ai_classify')
        max_requests: Maximum number of requests in the window
        window_seconds: Time window in seconds (default: 60)

    NOTE: For production, use Redis instead of this in-memory implementation.
    """
    key = (user_id, endpoint)
    now = time.monotonic()
    cutoff = now - window_seconds

    with _lock:
        q = _request_log[key]
        # Remove timestamps outside the window
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(window_seconds)},
            )
        q.append(now)
