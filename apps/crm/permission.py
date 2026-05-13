"""Deprecated module — kept for backward compatibility.

Use :mod:`crm.permissions` (plural) instead. All public names from the old
``permission.py`` are re-exported below.

Will be removed in a future release.
"""

from __future__ import annotations

import warnings

from .permissions import IsAdminOrReadOnly, IsOwnerOrReadOnly

warnings.warn(
    "crm.permission is deprecated; import from crm.permissions instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Legacy aliases for any code path that still imports the old class names.
IsStaffOrReadOnly = IsAdminOrReadOnly
IsCommentAuthor = IsOwnerOrReadOnly
IsAthenticatedOrReadOnly = IsOwnerOrReadOnly  # (also fixes the typo in old name)

__all__ = (
    "IsAdminOrReadOnly",
    "IsAthenticatedOrReadOnly",
    "IsCommentAuthor",
    "IsOwnerOrReadOnly",
    "IsStaffOrReadOnly",
)
