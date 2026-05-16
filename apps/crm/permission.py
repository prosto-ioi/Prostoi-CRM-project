"""Deprecated module — kept for backward compatibility.

Use :mod:`crm.permissions` instead. Will be removed in a future release.
"""

from __future__ import annotations

import warnings

from .permissions import (
    IsAdminOrReadOnly,
    IsAthenticatedOrReadOnly,
    IsCommentAuthor,
    IsOwnerOrReadOnly,
    IsStaffOrReadOnly,
)
warnings.warn(
    "crm.permission is deprecated; import from crm.permissions instead.",
    DeprecationWarning,
    stacklevel=2,
)


__all__ = (
    "IsAdminOrReadOnly",
    "IsAthenticatedOrReadOnly",
    "IsCommentAuthor",
    "IsOwnerOrReadOnly",
    "IsStaffOrReadOnly",
)
