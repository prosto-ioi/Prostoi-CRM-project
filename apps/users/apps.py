"""App configuration for the users app."""
from __future__ import annotations

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Configures the ``users`` app for Django's app registry."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "users"
    label = "users"
    verbose_name = "Users"
