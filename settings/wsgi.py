"""WSGI entry point.

Mirrors :mod:`manage.py` — picks the settings module based on ``CRM_ENV_ID``
so the same code runs locally (``local``) and in production (``prod``).
"""
from __future__ import annotations

import os

from django.core.wsgi import get_wsgi_application

# ``setdefault`` lets process supervisors (gunicorn, uwsgi) override this via
# a real environment variable when needed.
_env_id = os.getenv("CRM_ENV_ID", "local")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"settings.env.{_env_id}")

application = get_wsgi_application()
