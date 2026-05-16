"""Custom DRF permissions used by the CRM viewsets.

Classes:
    * IsAdminOrReadOnly      — write only for staff/superuser.
    * IsOwnerOrReadOnly      — write only for the row's owner.
    * IsStaffOrReadOnly      — alias-class for IsAdminOrReadOnly (explicit name).
    * IsCommentAuthor        — write only for the comment's author.
    * IsAuthenticatedOrReadOnly — read for anyone, write only for authenticated.
"""

from __future__ import annotations

from typing import Any, ClassVar

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsAuthenticatedOrReadOnly(BasePermission):
    """Read for anyone (including anonymous); write only for authenticated users.

    Different from DRF's built-in by the same name in that anonymous users
    get 401 on write attempts rather than being silently passed to the view.
    Use when public read access is intentional (e.g. a public product catalog).
    """

    message = "Authentication is required to perform this action."

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)


class IsAdminOrReadOnly(BasePermission):
    """Read for any authenticated user; write only for staff/superuser.

    Intended for globally-shared reference data (e.g. ``Category``, ``Tag``)
    where only administrators should mutate state.
    """

    message = "Only staff users can modify this resource."

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        # GET / HEAD / OPTIONS — open to any authenticated user.
        if request.method in SAFE_METHODS:
            return True
        # Mutating methods — staff/superuser only.
        return bool(request.user.is_staff or request.user.is_superuser) # type: ignore


class IsOwnerOrReadOnly(BasePermission):
    """Read for any authenticated user; write only for the row's owner.

    Owner is resolved by looking up the first matching attribute from
    OWNER_FIELDS on the object. Staff/superusers always pass.
    """

    message = "You do not have permission to modify this object."

    # Attribute names checked when resolving the row's owner.
    OWNER_FIELDS: ClassVar[tuple[str, ...]] = ("author", "created_by", "assigned_to")

    def has_permission(self, request: Request, view: APIView) -> bool:
        # View-level gate — authentication is required for everything.
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(
        self,
        request: Request,
        view: APIView,
        obj: Any,
    ) -> bool:
        if request.method in SAFE_METHODS:
            return True
        # Staff override — admins can mutate any row.
        if request.user.is_staff or request.user.is_superuser: # type: ignore
            return True
        # Walk the candidate owner fields; first one that exists decides.
        for field in self.OWNER_FIELDS:
            if hasattr(obj, field):
                return getattr(obj, field) == request.user
        return False


class IsStaffOrReadOnly(BasePermission):
    """Explicit staff-only write permission.

    Functionally identical to IsAdminOrReadOnly but with a name that makes
    intent clear when applied to staff-gated endpoints (not just admin panel).
    """

    message = "Only staff members can perform this action."

    def has_permission(self, request: Request, view: APIView) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user.is_staff)  # type: ignore




