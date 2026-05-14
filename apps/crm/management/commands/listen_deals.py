"""Management command that subscribes to the CRM deals Pub/Sub channel.

Usage::

    python manage.py listen_deals

Run in a separate terminal / process. Prints every event to stdout.
Extend ``_handle_event`` to send emails, push notifications, etc.
"""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand
from django_redis import get_redis_connection

from crm.pubsub import DEALS_CHANNEL


class Command(BaseCommand):
    help = "Listens for deal events on the Redis Pub/Sub channel."

    def handle(self, *args: Any, **options: Any) -> None:
        redis_client = get_redis_connection("default")
        pubsub = redis_client.pubsub()
        pubsub.subscribe(DEALS_CHANNEL)

        self.stdout.write(f"Listening on channel '{DEALS_CHANNEL}'...")

        for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data: dict[str, Any] = json.loads(message["data"])
            self._handle_event(data)

    def _handle_event(self, data: dict[str, Any]) -> None:
        """Process a single deal event.

        Override or extend this method to send emails, trigger
        notifications, update analytics, etc.
        """
        self.stdout.write(
            f"Event: {data['event']}, deal #{data['deal_id']}"
        )