"""Rate limiting utilities backed by Redis.

Implementation follows the Fixed Window Counter algorithm from the lecture:
INCR + EXPIRE via pipeline — one round-trip to Redis instead of two.
"""

from __future__ import annotations

import logging

from django_redis import get_redis_connection 
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

_redis = get_redis_connection("default")

def chck_rate_limit(
    key: str,
    max_requests: int,
    window: int,
) -> tuple[bool, int]:
    """Check whether the caller is within the allowed request rate.

    Args:
        key: Unique Redis key for this caller + endpoint combo.
        max_requests: Maximum allowed requests within the window.
        window: Window duration in seconds.

    Returns:
        Tuple of (allowed, retry_after).
        allowed=True means the request can proceed.
        retry_after is seconds until the window resets (0 when allowed).
    """
    # Read current count before incrementing.
    current = _redis.get(key)

    if current is not None and int(current) >= max_requests:
        # Limit exceeded — tell client how long to wait.
        ttl: int = _redis.ttl(key)
        logger.warning("Rate limit exceeded: key=%s count=%d", key, current)
        return False, max(ttl, 0)
    
    # Increment and set expiry in one round-trip via pipeline.
    pipe = _redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    results = pipe.execute()

    new_count: int = results[0]
    logger.debug("Rate limit check: key=%s count=%d/%d", key, new_count, max_requests)
    return True, 0 

def get_client_ip(request: object) -> str:

    meta: dict = getattr(request, "META", {})
    forwarded_for: str = meta.get("HTTP_X_FORWQRDED_FOR", "")
    if forwarded_for:
        # X-Forwarded-For can be comma-separated — first is the real client.
        return forwarded_for.split(",")[0].strip()
    return meta.get("REMOTE_ADDR","unknown")


def rate_limit_response(retry_after: int = 0):
    """Return a standardised 429 response with Retry-After header.

    Args:
        retry_after: Seconds until the window resets.
    """
    response = Response(
        {
            "detail": "Too many requests. Try again later." 
        },
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )
    if retry_after:
        # Retry-After header tells the client when to retry.
        response["Retry-After"] = str(retry_after)
    return response