"""Django admin registrations for the CRM models."""
from __future__ import annotations

from django.contrib import admin

from .models import Category, Client, Comment, Deal, Product, Tag, Task


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin for ``Category`` — slug is auto-derived from ``name_en``."""

    list_display = ("name_en", "name_ru", "name_kk", "slug")
    prepopulated_fields: dict[str, tuple[str, ...]] = {"slug": ("name_en",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Admin for ``Tag``."""

    list_display = ("name", "slug")
    prepopulated_fields: dict[str, tuple[str, ...]] = {"slug": ("name",)}


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """Admin for ``Client`` with full-text-ish search across name and email."""

    list_display = ("first_name", "last_name", "email", "phone", "created_at")
    search_fields = ("first_name", "last_name", "email")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin for ``Product``; ``in_stock`` and ``category`` are filterable."""

    list_display = ("name", "category", "price", "in_stock", "created_at")
    list_filter = ("in_stock", "category")
    prepopulated_fields: dict[str, tuple[str, ...]] = {"slug": ("name",)}


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    """Admin for ``Deal``."""

    list_display = ("title", "client", "amount", "status", "created_at", "closed_at")
    list_filter = ("status",)
    search_fields = ("title", "client__first_name", "client__last_name")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Admin for ``Task`` with status filter and title search."""

    list_display = ("title", "assigned_to", "status", "due_date", "created_at")
    list_filter = ("status",)
    search_fields = ("title",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """Admin for generic ``Comment`` rows (attached to Task or Deal via GFK)."""

    list_display = ("author", "content_type", "object_id", "created_at")
    list_filter = ("content_type",)
