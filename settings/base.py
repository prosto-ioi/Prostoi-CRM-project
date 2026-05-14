"""Django settings for the Prostoi CRM project (base layer).

Environment-specific overlays (``settings/env/local.py``, ``settings/env/prod.py``)
import from this file. Anything truly shared lives here.
"""

from __future__ import annotations

import os
import sys
from datetime import timedelta
from pathlib import Path

# ─── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
# Allow ``from users.models import User`` instead of ``apps.users.models`` —
# the apps directory is added to ``sys.path`` here so import paths in code,
# migrations and management commands stay short.
sys.path.insert(0, str(BASE_DIR / "apps"))


# ─── Core ───────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("CRM_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("CRM_SECRET_KEY is not set in .env")

DEBUG = os.getenv("CRM_DEBUG", "False") == "True"

ALLOWED_HOSTS = ["*"]

AUTH_USER_MODEL = "users.User"


# ─── Apps ───────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "django_filters",
    "users",
    "crm",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # ``UserPreferencesMiddleware`` reads ``request.user`` to pick a language
    # + timezone, so it MUST follow ``AuthenticationMiddleware``. It also
    # replaces Django's stock ``LocaleMiddleware`` — we don't include that
    # one because our middleware already handles ``Accept-Language`` for
    # anonymous requests via ``get_language_from_request``.
    "users.middleware.UserPreferencesMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "settings.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "settings.wsgi.application"


# ─── Database ───────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
}


# ─── Auth & passwords ───────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ─── i18n / TZ ──────────────────────────────────────────────────────────────
# Default language used when neither ``user.language`` nor the request's
# ``Accept-Language`` header points at a supported locale.
LANGUAGE_CODE = "en"

# Explicit allowlist of locales the project ships translations for. Anything
# outside this set is silently ignored by ``UserPreferencesMiddleware``.
# Wrap the human-readable name in ``gettext_lazy`` so the label itself shows
# up in the language menu translated.
from django.utils.translation import gettext_lazy as _  # noqa: E402

LANGUAGES = [
    ("en", _("English")),
    ("ru", _("Russian")),
    ("kk", _("Kazakh")),
]

# Where ``makemessages`` writes ``.po`` files and ``compilemessages`` reads
# them. Project-level dir so translations are shared across apps rather than
# scattered per-app.
LOCALE_PATHS = [BASE_DIR / "locale"]

TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# ─── Static / media ─────────────────────────────────────────────────────────
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ─── DRF ────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}


# ─── SimpleJWT ──────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "JWK_URL": None,
    "LEEWAY": 0,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": (
        "rest_framework_simplejwt.authentication.default_user_authentication_rule"
    ),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
    "JTI_CLAIM": "jti",
}


# ─── CORS ───────────────────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:8000",
]


# ─── OpenAPI / Swagger ──────────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE": "Prostoi CRM API",
    "DESCRIPTION": "CRM system for managing clients, deals, and tasks.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}


# ─── Logging ────────────────────────────────────────────────────────────────
# Single config that covers both local dev and prod. ``CRM_LOG_LEVEL`` may be
# set in ``.env`` to bump verbosity (``DEBUG`` for noisy local work,
# ``WARNING`` for prod).
LOG_LEVEL = os.getenv("CRM_LOG_LEVEL", "INFO" if not DEBUG else "DEBUG")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            # ``asctime`` first so log scrapers can sort lexicographically.
            "format": "{asctime} [{levelname}] {name}: {message}",
            "style": "{",
        },
        "simple": {
            "format": "[{levelname}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        # Our own app loggers — keep them named by app for filtering.
        "users": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "crm": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}
