"""Cache helpers for the CRM app.

Implements Cache-Aside pattern from the lecture:
    Request → in Redis?
               HIT  → serve from Redis
               MISS → fetch from DB → store in Redis → serve

Invalidation is manual: called on every create / update / destroy.
"""

from __future__ import annotations

import logging
from typing import Any

from django.core.cache import cache

logger = logging.getLogger(__name__)

DEALS_LIST_KEY: str = "crm:deals:list"
DEALS_LIST_TIMEOUT: int = 60 

def get_deals_list_cache() -> list[dict[str, Any]] | None:
    """Return cached deals list or None on cache MISS."""
    data = cache.get(DEALS_LIST_KEY)
    if data is not None:
        logger.debug("Cache HIT: %s", DEALS_LIST_KEY)
    else:
        logger.debug("Cache MISS: %s", DEALS_LIST_KEY)
    return data


def set_deals_list_cache(data: list[dict[str, Any]]) -> None:
    """Store serialized deals list in Redis for DEALS_LIST_TIMEOUT seconds."""
    cache.set(DEALS_LIST_KEY, data, timeout=DEALS_LIST_TIMEOUT)
    logger.debug("Cache SET: %s (timeout=%ds)", DEALS_LIST_KEY, DEALS_LIST_TIMEOUT)


def invalidate_deals_cache() -> None:
    """Delete the deals list cache entry.

    Must be called on every create / update / destroy of a Deal
    so stale data is never served.
    """
    cache.delete(DEALS_LIST_KEY)
    logger.debug("Cache INVALIDATED: %s", DEALS_LIST_KEY)