"""Cache helpers for the CRM app.

Implements Cache-Aside pattern from the lecture:
    Request → in Redis?
               HIT  → serve from Redis
               MISS → fetch from DB → store in Redis → serve

Invalidation is manual: called on every create / update / destroy.
"""

from __future__ import annotations

from hashlib import sha256
import logging
from typing import Any

from django.core.cache import cache

logger = logging.getLogger(__name__)

DEALS_LIST_KEY: str = "crm:deals:list"
DEALS_LIST_TIMEOUT: int = 60 


def make_deals_list_cache_key(full_path: str) -> str:
    """Return a stable Redis key for a specific deals list URL."""
    digest = sha256(full_path.encode("utf-8")).hexdigest()
    return f"{DEALS_LIST_KEY}:{digest}"


def get_deals_list_cache(key: str) -> list[dict[str, Any]] | None:
    """Return cached deals list or None on cache MISS."""
    data = cache.get(key)
    if data is not None:
        logger.debug("Cache HIT: %s", key)
    else:
        logger.debug("Cache MISS: %s", key)
    return data


def set_deals_list_cache(key: str, data: list[dict[str, Any]]) -> None:
    """Store serialized deals list in Redis for DEALS_LIST_TIMEOUT seconds."""
    cache.set(key, data, timeout=DEALS_LIST_TIMEOUT)
    logger.debug("Cache SET: %s (timeout=%ds)", key, DEALS_LIST_TIMEOUT)


def invalidate_deals_cache() -> None:
    """Delete the deals list cache entry.

    Must be called on every create / update / destroy of a Deal
    so stale data is never served.
    """
    cache.delete_pattern(f"{DEALS_LIST_KEY}:*")
    logger.debug("Cache INVALIDATED: %s:*", DEALS_LIST_KEY)
