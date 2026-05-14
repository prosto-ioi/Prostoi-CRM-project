"""Redis Pub/Sub helpers for the CRM app.

Publisher:  called from DealViewSet on create/update/destroy.
Subscriber: run as a management command — python manage.py listen_deals.

Channel: "crm:deals"

Limitations (from the lecture):
    - Offline subscribers MISS messages — Redis does not store them.
    - No delivery acknowledgment — use Celery for critical tasks.
    - Use Pub/Sub for: notifications, cache invalidation across servers,
      real-time dashboard updates.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from django_redis import get_redis_connection

logger = logging.getLogger(__name__)

DEALS_CHANNEL: str = "crm:deals"


def publish_deal_event(event: str, deal_id: int, extra: dict[str, Any] | None = None) -> None:
    """Publish a deal lifecycle event to the Redis channel.

    Args:
        event:   Event name, e.g. ``"deal_created"``, ``"deal_updated"``,
                 ``"deal_deleted"``.
        deal_id: PK of the affected ``Deal`` row.
        extra:   Optional extra fields merged into the payload.
    """
    redis_client = get_redis_connection("default")
    payload: dict[str, Any] = {"event": event, "deal_id": deal_id}
    if extra:
        payload.update(extra)
    redis_client.publish(DEALS_CHANNEL, json.dumps(payload))
    logger.debug("Published %s for deal #%d", event, deal_id)