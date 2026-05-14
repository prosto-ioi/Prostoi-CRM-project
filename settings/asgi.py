"""ASGI entry point.

Mirrors :mod:`manage.py` and :mod:`settings.wsgi` — picks the settings module
based on ``CRM_ENV_ID``.
"""
from __future__ import annotations

import os

from django.core.asgi import get_asgi_application

_env_id = os.getenv("CRM_ENV_ID", "local")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"settings.env.{_env_id}")

application = get_asgi_application()
