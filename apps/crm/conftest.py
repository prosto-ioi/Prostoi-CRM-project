"""Shared test infrastructure for the CRM app.

Keeps the per-class test files lean by centralising:

* Common constants (URL names, default passwords, default factory payloads).
* Helpers that compose them — ``reverse_list`` / ``reverse_detail`` /
  ``authenticate``.
* A typed :class:`TestAPIClient` protocol that fixes a long-standing gap in
  ``djangorestframework-stubs`` (the inherited ``Client.post/get/...`` typing
  bleeds through and Pylance sees the return type as ``WSGIRequest`` instead
  of ``rest_framework.response.Response``).

Nothing in this module depends on a specific test class; the goal is that
test files only describe *behaviour*, not boilerplate.
"""
from __future__ import annotations

from typing import Any, Final, Protocol

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.response import Response
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


# ─── Typed DRF client protocol ─────────────────────────────────────────────
class TestAPIClient(Protocol):
    """Structural type for DRF's :class:`APIClient` used in tests.

    Why this exists
        At runtime ``APIClient.post(...)`` returns a DRF
        :class:`rest_framework.response.Response`, but the static stubs for
        ``djangorestframework-stubs`` inherit the type from Django's
        :class:`django.test.Client`, which is typed as returning a
        ``_MonkeyPatchedWSGIResponse``. Pylance then resolves that to
        ``WSGIRequest | Unknown`` and complains everywhere a test reads
        ``response.data``.

    The fix
        We declare a small :class:`Protocol` listing only the methods we
        actually call in tests, each returning ``Response`` explicitly, and
        :func:`make_api_client` returns one of these. Tests then read
        ``response.data`` without any type errors and never need ``cast``
        sprinkled around. Runtime behaviour is unchanged — ``Protocol`` is
        purely a type-checker construct.
    """

    def get(self, path: str, data: Any = ..., **kwargs: Any) -> Response: ...

    def post(
        self, path: str, data: Any = ..., format: str = ..., **kwargs: Any,
    ) -> Response: ...

    def put(
        self, path: str, data: Any = ..., format: str = ..., **kwargs: Any,
    ) -> Response: ...

    def patch(
        self, path: str, data: Any = ..., format: str = ..., **kwargs: Any,
    ) -> Response: ...

    def delete(self, path: str, **kwargs: Any) -> Response: ...

    def force_authenticate(self, user: Any | None = ..., token: Any = ...) -> None: ...

    def credentials(self, **kwargs: Any) -> None: ...


def make_api_client() -> TestAPIClient:
    """Return a DRF ``APIClient`` typed as :class:`TestAPIClient`.

    At runtime this is exactly :class:`rest_framework.test.APIClient`; the
    return-type annotation gives Pylance the correct ``Response`` shape for
    every HTTP method.
    """
    # ``APIClient`` structurally satisfies ``TestAPIClient`` — the protocol
    # methods are all real methods on the class. Pyright accepts the
    # assignment without an explicit cast.
    return APIClient()  # type: ignore[return-value]


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


def authenticate(client: TestAPIClient, user: Any) -> None:
    """Force-authenticate ``client`` as ``user`` (bypasses JWT for speed)."""
    client.force_authenticate(user=user)
