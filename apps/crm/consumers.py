from __future__ import annotations

import json
from typing import Any

from channels.generic.websocket import AsyncWebsocketConsumer


class InventoryConsumer(AsyncWebsocketConsumer):
    group_name = "inventory_updates"

    async def connect(self) -> None:
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name,
        )

    async def inventory_update(self, event: dict[str, Any]) -> None:
        await self.send(
            text_data=json.dumps(
                {
                    "type": "inventory_update",
                    "product_id": event["product_id"],
                    "stock_count": event.get("stock_count"),
                    "in_stock": event.get("in_stock"),
                }
            )
        )
