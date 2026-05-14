from __future__ import annotations

import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

DEALS_LIST_TIMEOUT: int = 60 
DEALS_LIST_KEY: str = "crm:deals:list"


def get_deals_list_cahe():
    return cache.get(DEALS_LIST_KEY)
    
def set_deals_list_cahe(data: list):
    cache.set(DEALS_LIST_KEY, data, timeout= DEALS_LIST_TIMEOUT)
    logger.debug("Deals list cache SET (timeout=%ds)", DEALS_LIST_TIMEOUT)

def invalidate_deals_cache():
    """Delete the deals list cache entry."""
    cache.delete(DEALS_LIST_KEY)
    logger.debug("Deals list cache INVALIDATED")
