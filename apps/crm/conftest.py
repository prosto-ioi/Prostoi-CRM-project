"""Shared test infrastructure for the CRM app.

Keeps the per-class test files lean by centralising:

* Common constants (URL names, default passwords, default factory payloads).
* Helpers that compose them — ``reverse_list`` / ``reverse_detail`` /
  ``authenticate``.

Nothing in this module depends on a specific test class; the goal is that
test files only describe *behaviour*, not boilerplate.
"""
from __future__ import annotations

from typing import Any, Final

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()

# ─── Test fixtures: constants ──────────────────────────────────────────────
#
# Keep all magic strings here so a typo in one test does not require chasing
# it through the whole test module.

# Default password used by every factory below. Strong enough to pass Django's
# ``CommonPasswordValidator`` / ``NumericPasswordValidator``.
DEFAULT_PASSWORD: Final[str] = "TestPass123!"

# Router basenames as registered in ``apps/crm/urls.py``. Concatenated with
# ``-list`` / ``-detail`` to get the actual URL name.
BASENAME_CATEGORY: Final[str] = "category"
BASENAME_TAG: Final[str] = "tag"
BASENAME_CLIENT: Final[str] = "client"
BASENAME_PRODUCT: Final[str] = "product"
BASENAME_DEAL: Final[str] = "deal"
BASENAME_TASK: Final[str] = "task"
BASENAME_COMMENT: Final[str] = "comment"


# ─── Test fixtures: URL helpers ────────────────────────────────────────────
def reverse_list(basename: str) -> str:
    """Return the list-route URL for a viewset basename.

    Example:
        >>> reverse_list("category")
        '/api/crm/categories/'
    """
    return reverse(f"{basename}-list")


def reverse_detail(basename: str, lookup: int | str) -> str:
    """Return the detail-route URL for a viewset basename + lookup value.

    ``lookup`` is either a PK (``int``) or a slug (``str``) depending on the
    viewset's ``lookup_field``.
    """
    return reverse(f"{basename}-detail", kwargs={"pk": lookup}) \
        if isinstance(lookup, int) \
        else reverse(f"{basename}-detail", kwargs={"slug": lookup})


# ─── Test fixtures: user factories ─────────────────────────────────────────
def make_user(
    email: str = "owner@example.com",
    *,
    is_staff: bool = False,
    password: str = DEFAULT_PASSWORD,
    **extra: Any,
) -> Any:
    """Create a saved user with the project's custom manager.

    Args:
        email: Unique email; required because it is the ``USERNAME_FIELD``.
        is_staff: Whether the user should be staff/admin.
        password: Raw password — hashed by ``create_user``.
        **extra: Additional ``User`` fields (``first_name`` defaulted etc.).

    Returns:
        The persisted ``User`` instance.
    """
    extra.setdefault("first_name", "Test")
    extra.setdefault("last_name", "User")
    user = User.objects.create_user(  # type: ignore[attr-defined]
        email=email,
        password=password,
        **extra,
    )
    if is_staff:
        user.is_staff = True
        user.save(update_fields=["is_staff"])
    return user


def authenticate(client: APIClient, user: Any) -> None:
    """Force-authenticate ``client`` as ``user`` (bypasses JWT for speed)."""
    client.force_authenticate(user=user)