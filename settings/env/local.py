"""Local development settings overlay.

Selected automatically when ``CRM_ENV_ID`` is unset or equal to ``"local"``.

Inherits everything from :mod:`settings.base`. Override only what differs
from the shared baseline — keep this file small.
"""
from __future__ import annotations

# Re-export everything from base. ``noqa: F401, F403`` silences the linter
# about the star import — this is the canonical Django pattern for env
# overlays and the star is intentional.
from settings.base import *  # noqa: F403

# ``DEBUG`` defaults to ``False`` in base; flip it on for local work.
DEBUG = True

# Django's ``runserver`` requires non-wildcard hosts when ``DEBUG`` is False;
# we're in DEBUG mode locally, so the base ``["*"]`` is fine. Listed here so
# the contract is explicit.
ALLOWED_HOSTS = ["*"]
