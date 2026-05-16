"""ASGI entry point.

Mirrors :mod:`manage.py` and :mod:`settings.wsgi` — picks the settings module
based on ``CRM_ENV_ID``.
"""
from __future__ import annotations

import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"settings.env.{os.getenv('CRM_ENV_ID', 'local')}")
django_asgi_app = get_asgi_application()

from crm.routing import websocket_urlpatterns
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns),),
})
