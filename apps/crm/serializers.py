"""DRF serializers for the CRM app.

Every model has two serializers:

    * ``XxxReadSerializer``  — used for ``list`` / ``retrieve`` and as the
      response shape for ``create`` / ``update``. Exposes nested detail blocks.
    * ``XxxWriteSerializer`` — accepts a minimal write payload and delegates
      its ``to_representation`` to the Read serializer so the wire shape stays
      consistent for the client.
"""
from __future__ import annotations

# ``PrimaryKeyRelatedField`` / ``SlugRelatedField`` are imported from their
# canonical module ``rest_framework.relations`` rather than via the
# ``rest_framework.serializers`` re-export: the latter goes through a
# ``from .relations import *`` which DRF's type stubs don't model, so
# Pylance otherwise flags them as ``reportAttributeAccessIssue``.
from typing import Any

from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from rest_framework.relations import PrimaryKeyRelatedField, SlugRelatedField

from .models import Category, Client, Comment, Deal, Product, Tag, Task


# ─────────────────────────────── Category ────────────────────────────────
class CategoryReadSerializer(serializers.ModelSerializer):
    """Full category representation (incl. auto-generated ``slug``)."""

    class Meta:
        model = Category
        fields = ("id", "name_en", "name_ru", "name_kk", "slug")
        read_only_fields = fields


class CategoryWriteSerializer(serializers.ModelSerializer):
    """Category create/update. ``slug`` is derived on save and not user-settable."""

    class Meta:
        model = Category
        fields = ("name_en", "name_ru", "name_kk")

    def to_representation(self, instance: Category) -> dict[str, Any]:
        return CategoryReadSerializer(instance, context=self.context).data


# ─────────────────────────────── Tag ────────────────────────────────
class TagReadSerializer(serializers.ModelSerializer):
    """Tag read serializer."""

    class Meta:
        model = Tag
        fields = ("id", "name", "slug")
        read_only_fields = fields


class TagWriteSerializer(serializers.ModelSerializer):
    """Tag write serializer. ``slug`` is derived on save."""

    class Meta:
        model = Tag
        fields = ("name",)

    def to_representation(self, instance: Tag) -> dict[str, Any]:
        return TagReadSerializer(instance, context=self.context).data


# ─────────────────────────────── Client ────────────────────────────────
class ClientReadSerializer(serializers.ModelSerializer):
    """Full client representation."""

    class Meta:
        model = Client
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "address",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ClientWriteSerializer(serializers.ModelSerializer):
    """Client write serializer (email uniqueness enforced by the model)."""

    class Meta:
        model = Client
        fields = ("first_name", "last_name", "email", "phone", "address")

    def to_representation(self, instance: Client) -> dict[str, Any]:
        return ClientReadSerializer(instance, context=self.context).data


# ─────────────────────────────── Product ────────────────────────────────
class ProductReadSerializer(serializers.ModelSerializer):
    """Product with nested ``category`` and ``tags`` detail blocks for the UI."""

    category_detail = CategoryReadSerializer(source="category", read_only=True)
    tags_detail = TagReadSerializer(source="tags", many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "category",
            "category_detail",
            "tags",
            "tags_detail",
            "price",
            "description",
            "in_stock",
            "created_at",
            "updated_at",
            "created_by",
        )
        read_only_fields = fields


class ProductWriteSerializer(serializers.ModelSerializer):
    """Product write serializer. ``slug`` and ``created_by`` are set server-side."""

    tags = PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=False,
    )

    class Meta:
        model = Product
        fields = ("name", "category", "tags", "price", "description", "in_stock")

    def to_representation(self, instance: Product) -> dict[str, Any]:
        return ProductReadSerializer(instance, context=self.context).data


# ─────────────────────────────── Deal ────────────────────────────────
class DealReadSerializer(serializers.ModelSerializer):
    """Deal with nested ``client`` and ``product`` detail blocks for the UI."""

    client_detail = ClientReadSerializer(source="client", read_only=True)
    product_detail = ProductReadSerializer(source="product", read_only=True)

    class Meta:
        model = Deal
        fields = (
            "id",
            "client",
            "client_detail",
            "product",
            "product_detail",
            "title",
            "amount",
            "status",
            "created_at",
            "updated_at",
            "closed_at",
            "created_by",
        )
        read_only_fields = fields


class DealWriteSerializer(serializers.ModelSerializer):
    """Deal write serializer. ``created_by`` is set in the view."""

    class Meta:
        model = Deal
        fields = ("client", "product", "title", "amount", "status", "closed_at")

    def to_representation(self, instance: Deal) -> dict[str, Any]:
        return DealReadSerializer(instance, context=self.context).data


# ─────────────────────────────── Task ────────────────────────────────
class TaskReadSerializer(serializers.ModelSerializer):
    """Task read serializer."""

    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "description",
            "assigned_to",
            "client",
            "deal",
            "status",
            "due_date",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class TaskWriteSerializer(serializers.ModelSerializer):
    """Task write serializer."""

    class Meta:
        model = Task
        fields = (
            "title",
            "description",
            "assigned_to",
            "client",
            "deal",
            "status",
            "due_date",
        )

    def to_representation(self, instance: Task) -> dict[str, Any]:
        return TaskReadSerializer(instance, context=self.context).data


# ─────────────────────────────── Comment ────────────────────────────────
class CommentReadSerializer(serializers.ModelSerializer):
    """Comment read serializer.

    ``content_type`` is rendered as a plain model name string (``"task"`` /
    ``"deal"``) instead of a numeric FK id — friendlier for the API client.
    """

    content_type = SlugRelatedField(read_only=True, slug_field="model")

    class Meta:
        model = Comment
        fields = ("id", "author", "content_type", "object_id", "body", "created_at")
        read_only_fields = fields


class CommentWriteSerializer(serializers.ModelSerializer):
    """Comment write serializer.

    ``author`` is set server-side from ``request.user`` — never trust client
    input for authorship. The ``content_type`` queryset is restricted to the
    two models that legitimately accept comments.
    """

    content_type = SlugRelatedField(
        queryset=ContentType.objects.filter(model__in=["task", "deal"]),
        slug_field="model",
    )

    class Meta:
        model = Comment
        fields = ("content_type", "object_id", "body")

    def to_representation(self, instance: Comment) -> dict[str, Any]:
        return CommentReadSerializer(instance, context=self.context).data