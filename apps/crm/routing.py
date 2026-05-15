from __future__ import annotations

from django.urls import path

from .consumers import InventoryConsumer

websocket_urlpatterns = [
    path("ws/inventory/", InventoryConsumer.as_asgi()),
]