"""Custom DRF permissions used by the CRM viewsets.

Two classes:
    * :class:`IsAdminOrReadOnly` — read-only for everyone authenticated,
      write only for staff/superuser. Use for reference data (categories, tags).
    * :class:`IsOwnerOrReadOnly` — read for any authenticated user, write only
      for the row's "owner" (``author`` / ``created_by`` / ``assigned_to``).
"""
from __future__ import annotations

from typing import Any, ClassVar

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsAdminOrReadOnly(BasePermission):
    """Read for any authenticated user; write only for staff/superuser.

    Intended for globally-shared reference data (e.g. ``Category``, ``Tag``)
    where only administrators should mutate state.
    """

    message = "Only staff users can modify this resource."

    def has_permission(self, request: Request, view: APIView) -> bool:
        # Anonymous users are rejected outright — DRF turns this into 401
        # when no authentication class has populated the user.
        if not request.user or not request.user.is_authenticated:
            return False
        # GET / HEAD / OPTIONS — open to any authenticated user.
        if request.method in SAFE_METHODS:
            return True
        # Mutating methods — staff/superuser only.
        return bool(request.user.is_staff or request.user.is_superuser)


class IsOwnerOrReadOnly(BasePermission):
    """Read for any authenticated user; write only for the row's owner.

    "Owner" is resolved at the object level by looking up — in order — the
    first attribute on the instance from :attr:`OWNER_FIELDS`. Staff and
    superusers always pass the object check (admin override).
    """

    message = "You do not have permission to modify this object."

    #: Attribute names checked when resolving the row's owner.
    OWNER_FIELDS: ClassVar[tuple[str, ...]] = ("author", "created_by", "assigned_to")

    def has_permission(self, request: Request, view: APIView) -> bool:
        # View-level gate — authentication is required for everything.
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(
        self, request: Request, view: APIView, obj: Any,
    ) -> bool:
        # Anyone authenticated can read.
        if request.method in SAFE_METHODS:
            return True
        # Staff override — admins can mutate any row.
        if request.user.is_staff or request.user.is_superuser:
            return True
        # Walk the candidate owner fields; first one that exists decides.
        for field in self.OWNER_FIELDS:
            if hasattr(obj, field):
                return getattr(obj, field) == request.user
        # No owner field on the model — fail closed.
        return False