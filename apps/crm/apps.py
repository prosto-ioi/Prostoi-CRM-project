"""App configuration for the CRM app."""
from __future__ import annotations

from django.apps import AppConfig


class CrmConfig(AppConfig):
    """Configures the ``crm`` app for Django's app registry."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "crm"
    label = "crm"
    verbose_name = "CRM"
