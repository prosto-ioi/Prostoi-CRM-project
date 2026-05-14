"""Production settings overlay.

Selected when ``CRM_ENV_ID=prod`` is set in ``.env``.

Switches the database to PostgreSQL via env vars, hardens host/CORS lists,
and turns ``DEBUG`` off explicitly so an accidental ``CRM_DEBUG=True`` in
the environment does not cascade into production.
"""
from __future__ import annotations

import os

from settings.base import *  # noqa: F403

# Hard off in prod, regardless of ``CRM_DEBUG`` in env.
DEBUG = False

# Restrict to the hostnames we actually serve. Comma-separated env var.
ALLOWED_HOSTS = [h.strip() for h in os.getenv("CRM_ALLOWED_HOSTS", "").split(",") if h.strip()]

# Database — PostgreSQL via standard env vars.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["CRM_DB_NAME"],
        "USER": os.environ["CRM_DB_USER"],
        "PASSWORD": os.environ["CRM_DB_PASSWORD"],
        "HOST": os.getenv("CRM_DB_HOST", "localhost"),
        "PORT": os.getenv("CRM_DB_PORT", "5432"),
    },
}

# CORS — explicit allowlist only.
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("CRM_CORS_ORIGINS", "").split(",") if o.strip()
]

# Standard prod security headers.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True