"""Rate limiting middleware for the CRM API.

Implements the Fixed Window Counter algorithm from the lecture:
    Window: 60 seconds
    Authenticated users: 100 req/min
    Anonymous (by IP):    20 req/min

Uses Redis INCR + EXPIRE via pipeline (one round-trip instead of two).
"""

from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django_redis import get_redis_connection


class RateLimitMiddleware:
    """Fixed-window rate limiter backed by Redis.

    Must be placed early in MIDDLEWARE so it runs before heavyweight
    middleware (auth, sessions, etc.).
    """

    AUTHENTICATED_LIMIT: int = 100
    ANONYMOUS_LIMIT: int = 20
    WINDOW: int = 60  # seconds

    def __init__(self, get_response):
        self.get_response = get_response
        self.redis = get_redis_connection("default")

    def __call__(self, request: HttpRequest):
        if hasattr(request, "user") and request.user.is_authenticated:
            client_id = f"user:{request.user.pk}"
            limit = self.AUTHENTICATED_LIMIT
        else:
            ip = request.META.get("REMOTE_ADDR", "unknown")
            client_id = f"ip:{ip}"
            limit = self.ANONYMOUS_LIMIT

        key = f"rl:{client_id}"

        current = self.redis.get(key)
        if current is not None and int(current) >= limit:
            ttl = self.redis.ttl(key)
            return JsonResponse(
                {"error": "Too many requests", "retry_after": ttl},
                status=429,
            )

        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, self.WINDOW)
        pipe.execute()

        return self.get_response(request)