"""Django admin registration for the custom ``User`` model."""
from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin for the custom email-based ``User`` model.

    Overrides ``fieldsets`` and ``add_fieldsets`` because the default admin
    assumes a ``username`` field, which we don't have.
    """

    # Columns shown on the user list page.
    list_display = ("email", "first_name", "last_name", "is_staff", "is_active")
    list_filter = ("is_active", "is_staff", "date_joined")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)

    # Edit-existing-user form layout.
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "avatar")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_staff",
                    "is_active",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    # Create-new-user form layout — the default uses ``username`` here.
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    # ``date_joined`` is ``auto_now_add=True`` — display only, never editable.
    readonly_fields = ("date_joined", "last_login")
