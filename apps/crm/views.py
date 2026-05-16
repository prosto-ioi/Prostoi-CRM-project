"""CRM viewsets — clients, categories, tags, products, deals, tasks, comments.

Every viewset selects between a Read and a Write serializer via
:meth:`get_serializer_class`. Object-level permissions are split per action
through :meth:`get_permissions` — ``create`` is generally open to any
authenticated user, while ``update`` / ``partial_update`` / ``destroy`` are
restricted to the row's owner (or staff).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar, cast

import httpx
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Count, Prefetch, QuerySet
from django.http import HttpRequest, JsonResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from .cache import (
    get_deals_list_cache,
    invalidate_deals_cache,
    make_deals_list_cache_key,
    set_deals_list_cache,
)
from .filters import DealFilter, ProductFilter, TaskFilter
from .models import Category, Client, Comment, Deal, Product, Tag, Task
from .permissions import IsAdminOrReadOnly, IsOwnerOrReadOnly
from .pubsub import publish_deal_event
from .serializers import (
    CategoryReadSerializer,
    CategoryWriteSerializer,
    ClientReadSerializer,
    ClientWriteSerializer,
    CommentReadSerializer,
    CommentWriteSerializer,
    DealReadSerializer,
    DealWriteSerializer,
    ProductReadSerializer,
    ProductWriteSerializer,
    TagReadSerializer,
    TagWriteSerializer,
    TaskReadSerializer,
    TaskWriteSerializer,
)
from .tasks import send_welcome_email

logger = logging.getLogger(__name__)
# Actions that mutate state — used by the Read/Write serializer switcher.
_WRITE_ACTIONS: frozenset[str] = frozenset({"create", "update", "partial_update"})

# Actions that touch a single existing row — used to pick object-level perms.
_OBJECT_MUTATE_ACTIONS: frozenset[str] = frozenset({"update", "partial_update", "destroy"})


def _current_action(viewset: viewsets.GenericViewSet) -> str | None:
    """Return ``viewset.action`` safely.

    ``action`` is set on the instance by DRF's ``ViewSetMixin.initialize_request``
    at runtime; Pyright cannot see it via static analysis, so we read it with
    ``getattr`` and a fallback. This avoids ``reportAttributeAccessIssue`` while
    keeping behaviour identical.
    """
    return getattr(viewset, "action", None)


class ReadWriteSerializerMixin:
    """Mixin: pick the write serializer for mutating actions, otherwise read."""

    read_serializer_class: ClassVar[type[BaseSerializer]]
    write_serializer_class: ClassVar[type[BaseSerializer]]

    def get_serializer_class(self) -> type[BaseSerializer]:
        # ``self`` is a viewset at runtime — the cast keeps type checkers happy
        # about the ``action`` lookup.
        action_name = _current_action(cast(viewsets.GenericViewSet, self))
        if action_name in _WRITE_ACTIONS:
            return self.write_serializer_class
        return self.read_serializer_class


class OwnerMutationPermissionMixin:
    """Mixin: authenticated reads/creates, owner-or-staff object mutations."""

    owner_mutation_actions: ClassVar[frozenset[str]] = _OBJECT_MUTATE_ACTIONS

    def get_permissions(self) -> list[BasePermission]:
        if _current_action(cast(viewsets.GenericViewSet, self)) in self.owner_mutation_actions:
            return [IsOwnerOrReadOnly()]
        return [IsAuthenticated()]


class DealCacheInvalidationMixin:
    """Mixin: cache and publish deal lifecycle events in one place."""

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        cache_key = make_deals_list_cache_key(request.get_full_path())
        cached = get_deals_list_cache(cache_key)
        if cached is not None:
            return Response(cached)

        response = super().list(request, *args, **kwargs)
        set_deals_list_cache(cache_key, response.data)
        return response

    def perform_create(self, serializer: BaseSerializer) -> None:
        deal = serializer.save(created_by=self.request.user)
        invalidate_deals_cache()
        publish_deal_event("deal_created", deal.id)

    def perform_update(self, serializer: BaseSerializer) -> None:
        deal = serializer.save()
        invalidate_deals_cache()
        publish_deal_event("deal_updated", deal.id)

    def perform_destroy(self, instance: Deal) -> None:
        deal_id = instance.id
        instance.delete()
        invalidate_deals_cache()
        publish_deal_event("deal_deleted", deal_id)


# Category
@extend_schema_view(
    list=extend_schema(
        summary="List categories",
        description=(
            "Requires JWT authentication. Supports filtering by slug, text search across "
            "localized names, and ordering by English name. Any authenticated user may read."
        ),
        tags=["Categories"],
        request=None,
        responses={
            status.HTTP_200_OK: CategoryReadSerializer(many=True),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
        },
        examples=[
            OpenApiExample(
                "Category list response",
                value=[
                    {
                        "id": 1,
                        "name": "Software",
                        "name_en": "Software",
                        "name_ru": "ПО",
                        "name_kk": "Бағдарлама",
                        "slug": "software",
                    }
                ],
                response_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve category",
        description="Requires JWT authentication. Any authenticated user may read a category.",
        tags=["Categories"],
        request=None,
        responses={
            status.HTTP_200_OK: CategoryReadSerializer,
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Category not found"),
        },
        examples=[
            OpenApiExample(
                "Category detail response",
                value={
                    "id": 1,
                    "name": "Software",
                    "name_en": "Software",
                    "name_ru": "ПО",
                    "name_kk": "Бағдарлама",
                    "slug": "software",
                },
                response_only=True,
            ),
        ],
    ),
    create=extend_schema(
        summary="Create category",
        description="Requires JWT authentication and staff/superuser permission.",
        tags=["Categories"],
        request=CategoryWriteSerializer,
        responses={
            status.HTTP_201_CREATED: CategoryReadSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(description="Staff permission required"),
        },
        examples=[
            OpenApiExample(
                "Create category request",
                value={"name_en": "Software", "name_ru": "ПО", "name_kk": "Бағдарлама"},
                request_only=True,
            ),
        ],
    ),
    update=extend_schema(
        summary="Replace category",
        description="Requires JWT authentication and staff/superuser permission.",
        tags=["Categories"],
        request=CategoryWriteSerializer,
        responses={
            status.HTTP_200_OK: CategoryReadSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(description="Staff permission required"),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Category not found"),
        },
        examples=[
            OpenApiExample(
                "Replace category request",
                value={
                    "name_en": "Services",
                    "name_ru": "Услуги",
                    "name_kk": "Қызметтер",
                },
                request_only=True,
            ),
        ],
    ),
    partial_update=extend_schema(
        summary="Patch category",
        description="Requires JWT authentication and staff/superuser permission.",
        tags=["Categories"],
        request=CategoryWriteSerializer,
        responses={
            status.HTTP_200_OK: CategoryReadSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(description="Staff permission required"),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Category not found"),
        },
        examples=[
            OpenApiExample(
                "Patch category request",
                value={"name_ru": "Сервисы"},
                request_only=True,
            ),
        ],
    ),
    destroy=extend_schema(
        summary="Delete category",
        description="Requires JWT authentication and staff/superuser permission.",
        tags=["Categories"],
        request=None,
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description="Category deleted"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(description="Staff permission required"),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Category not found"),
        },
        examples=[
            OpenApiExample("Delete category response", value=None, response_only=True),
        ],
    ),
)
class CategoryViewSet(ReadWriteSerializerMixin, viewsets.ModelViewSet):
    """Public to read; staff-only to write."""

    queryset = Category.objects.all()
    lookup_field = "slug"
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ("slug",)
    search_fields = ("name_en", "name_ru", "name_kk")
    ordering_fields = ("name_en",)
    read_serializer_class = CategoryReadSerializer
    write_serializer_class = CategoryWriteSerializer


# Tag
@extend_schema_view(
    list=extend_schema(
        summary="List tags",
        description=(
            "Requires JWT authentication. Supports filtering by name or slug, search by "
            "name, and ordering by name. Any authenticated user may read."
        ),
        tags=["Tags"],
        request=None,
        responses={
            status.HTTP_200_OK: TagReadSerializer(many=True),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
        },
        examples=[
            OpenApiExample(
                "Tag list response",
                value=[{"id": 1, "name": "priority", "slug": "priority"}],
                response_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve tag",
        description="Requires JWT authentication. Any authenticated user may read a tag.",
        tags=["Tags"],
        request=None,
        responses={
            status.HTTP_200_OK: TagReadSerializer,
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Tag not found"),
        },
        examples=[
            OpenApiExample(
                "Tag detail response",
                value={"id": 1, "name": "priority", "slug": "priority"},
                response_only=True,
            ),
        ],
    ),
    create=extend_schema(
        summary="Create tag",
        description="Requires JWT authentication and staff/superuser permission.",
        tags=["Tags"],
        request=TagWriteSerializer,
        responses={
            status.HTTP_201_CREATED: TagReadSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(description="Staff permission required"),
        },
        examples=[
            OpenApiExample(
                "Create tag request",
                value={"name": "priority"},
                request_only=True,
            ),
        ],
    ),
    update=extend_schema(
        summary="Replace tag",
        description="Requires JWT authentication and staff/superuser permission.",
        tags=["Tags"],
        request=TagWriteSerializer,
        responses={
            status.HTTP_200_OK: TagReadSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(description="Staff permission required"),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Tag not found"),
        },
        examples=[
            OpenApiExample("Replace tag request", value={"name": "vip"}, request_only=True),
        ],
    ),
    partial_update=extend_schema(
        summary="Patch tag",
        description="Requires JWT authentication and staff/superuser permission.",
        tags=["Tags"],
        request=TagWriteSerializer,
        responses={
            status.HTTP_200_OK: TagReadSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(description="Staff permission required"),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Tag not found"),
        },
        examples=[
            OpenApiExample("Patch tag request", value={"name": "hot"}, request_only=True),
        ],
    ),
    destroy=extend_schema(
        summary="Delete tag",
        description="Requires JWT authentication and staff/superuser permission.",
        tags=["Tags"],
        request=None,
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description="Tag deleted"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(description="Staff permission required"),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Tag not found"),
        },
        examples=[
            OpenApiExample("Delete tag response", value=None, response_only=True),
        ],
    ),
)
class TagViewSet(ReadWriteSerializerMixin, viewsets.ModelViewSet):
    """Public to read; staff-only to write."""

    queryset = Tag.objects.all()
    lookup_field = "slug"
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ("slug", "name")
    search_fields = ("name",)
    ordering_fields = ("name",)
    read_serializer_class = TagReadSerializer
    write_serializer_class = TagWriteSerializer


# Client
@extend_schema_view(
    list=extend_schema(
        summary="List clients",
        description=(
            "Requires JWT authentication. Supports filtering by email, search by "
            "name/email/phone, and ordering by creation, update, or last name."
        ),
        tags=["Clients"],
        request=None,
        responses={
            status.HTTP_200_OK: ClientReadSerializer(many=True),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
        },
        examples=[
            OpenApiExample(
                "Client list response",
                value=[
                    {
                        "id": 1,
                        "first_name": "Aruzhan",
                        "last_name": "Kim",
                        "email": "aruzhan@example.com",
                        "phone": "+77001112233",
                        "address": "Almaty",
                    }
                ],
                response_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve client",
        description="Requires JWT authentication. Any authenticated user may read a client.",
        tags=["Clients"],
        request=None,
        responses={
            status.HTTP_200_OK: ClientReadSerializer,
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Client not found"),
        },
        examples=[
            OpenApiExample(
                "Client detail response",
                value={
                    "id": 1,
                    "first_name": "Aruzhan",
                    "last_name": "Kim",
                    "email": "aruzhan@example.com",
                    "phone": "+77001112233",
                    "address": "Almaty",
                },
                response_only=True,
            ),
        ],
    ),
    create=extend_schema(
        summary="Create client",
        description=(
            "Requires JWT authentication. Any authenticated user may create a client; "
            "a welcome email task is queued after commit."
        ),
        tags=["Clients"],
        request=ClientWriteSerializer,
        responses={
            status.HTTP_201_CREATED: ClientReadSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
        },
        examples=[
            OpenApiExample(
                "Create client request",
                value={
                    "first_name": "Aruzhan",
                    "last_name": "Kim",
                    "email": "aruzhan@example.com",
                    "phone": "+77001112233",
                    "address": "Almaty",
                },
                request_only=True,
            ),
        ],
    ),
    update=extend_schema(
        summary="Replace client",
        description="Requires JWT authentication. Any authenticated user may update clients.",
        tags=["Clients"],
        request=ClientWriteSerializer,
        responses={
            status.HTTP_200_OK: ClientReadSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Client not found"),
        },
        examples=[
            OpenApiExample(
                "Replace client request",
                value={
                    "first_name": "Aruzhan",
                    "last_name": "Kim",
                    "email": "aruzhan@example.com",
                    "phone": "+77001112233",
                    "address": "Astana",
                },
                request_only=True,
            ),
        ],
    ),
    partial_update=extend_schema(
        summary="Patch client",
        description="Requires JWT authentication. Any authenticated user may patch clients.",
        tags=["Clients"],
        request=ClientWriteSerializer,
        responses={
            status.HTTP_200_OK: ClientReadSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Client not found"),
        },
        examples=[
            OpenApiExample(
                "Patch client request",
                value={"phone": "+77009998877"},
                request_only=True,
            ),
        ],
    ),
    destroy=extend_schema(
        summary="Delete client",
        description="Requires JWT authentication. Any authenticated user may delete clients.",
        tags=["Clients"],
        request=None,
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description="Client deleted"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Client not found"),
        },
        examples=[
            OpenApiExample("Delete client response", value=None, response_only=True),
        ],
    ),
)
class ClientViewSet(ReadWriteSerializerMixin, viewsets.ModelViewSet):
    """Any authenticated user can manage clients (no per-row ownership)."""

    queryset = Client.objects.all()
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ("email",)
    search_fields = ("first_name", "last_name", "email", "phone")
    ordering_fields = ("created_at", "updated_at", "last_name")
    read_serializer_class = ClientReadSerializer
    write_serializer_class = ClientWriteSerializer

    def perform_create(self, serializer: BaseSerializer) -> None:
        client = serializer.save()
        transaction.on_commit(lambda: send_welcome_email.delay(client.id))


# Product
@extend_schema_view(
    list=extend_schema(
        summary="List products",
        description=(
            "Requires JWT authentication. Supports category, price range, stock, "
            "search, and ordering filters. Returns nested category/tag data plus "
            "the annotated deals_count field."
        ),
        tags=["Products"],
        request=None,
        parameters=[
            OpenApiParameter("category", OpenApiTypes.STR, description="Category slug"),
            OpenApiParameter("min_price", OpenApiTypes.NUMBER, description="Minimum price"),
            OpenApiParameter("max_price", OpenApiTypes.NUMBER, description="Maximum price"),
            OpenApiParameter("in_stock", OpenApiTypes.BOOL, description="Filter by stock flag"),
            OpenApiParameter("search", OpenApiTypes.STR, description="Search name or description"),
            OpenApiParameter("ordering", OpenApiTypes.STR, description="price or created_at"),
        ],
        responses={
            status.HTTP_200_OK: ProductReadSerializer(many=True),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
        },
        examples=[
            OpenApiExample(
                "Product list response",
                value=[
                    {
                        "id": 1,
                        "name": "CRM setup",
                        "slug": "crm-setup",
                        "category": 1,
                        "tags": [1, 2],
                        "price": "4500.00",
                        "description": "Implementation package",
                        "in_stock": True,
                        "created_by": 1,
                        "deals_count": 3,
                    }
                ],
                response_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve product",
        description=(
            "Requires JWT authentication. Returns one product by slug with nested "
            "category/tag data and deals_count."
        ),
        tags=["Products"],
        request=None,
        responses={
            status.HTTP_200_OK: ProductReadSerializer,
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Product not found"),
        },
        examples=[
            OpenApiExample(
                "Product detail response",
                value={
                    "id": 1,
                    "name": "CRM setup",
                    "slug": "crm-setup",
                    "category": 1,
                    "tags": [1, 2],
                    "price": "4500.00",
                    "description": "Implementation package",
                    "in_stock": True,
                    "created_by": 1,
                    "deals_count": 3,
                },
                response_only=True,
            ),
        ],
    ),
    create=extend_schema(
        summary="Create product",
        description=(
            "Requires JWT authentication. Any authenticated user may create a product; "
            "created_by is set from request.user."
        ),
        tags=["Products"],
        request=ProductWriteSerializer,
        responses={
            status.HTTP_201_CREATED: ProductReadSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
        },
        examples=[
            OpenApiExample(
                "Create a product request",
                value={
                    "name": "coffee",
                    "category": 1,
                    "tags": [1, 2],
                    "price": "4500.00",
                    "description": "Arabica coffee",
                    "in_stock": True,
                },
                request_only=True,
            ),
        ],
    ),
    update=extend_schema(
        summary="Replace product",
        description="Requires JWT authentication and product owner or staff permission.",
        tags=["Products"],
        request=ProductWriteSerializer,
        responses={
            status.HTTP_200_OK: ProductReadSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(
                description="Owner or staff permission required"
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Product not found"),
        },
        examples=[
            OpenApiExample(
                "Replace product request",
                value={
                    "name": "CRM setup",
                    "category": 1,
                    "tags": [1, 2],
                    "price": "5000.00",
                    "description": "Updated package",
                    "in_stock": True,
                },
                request_only=True,
            ),
        ],
    ),
    partial_update=extend_schema(
        summary="Patch product",
        description="Requires JWT authentication and product owner or staff permission.",
        tags=["Products"],
        request=ProductWriteSerializer,
        responses={
            status.HTTP_200_OK: ProductReadSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(
                description="Owner or staff permission required"
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Product not found"),
        },
        examples=[
            OpenApiExample("Patch product request", value={"in_stock": False}, request_only=True),
        ],
    ),
    destroy=extend_schema(
        summary="Delete product",
        description="Requires JWT authentication and product owner or staff permission.",
        tags=["Products"],
        request=None,
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description="Product deleted"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(
                description="Owner or staff permission required"
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Product not found"),
        },
        examples=[
            OpenApiExample("Delete product response", value=None, response_only=True),
        ],
    ),
)
class ProductViewSet(
    OwnerMutationPermissionMixin,
    ReadWriteSerializerMixin,
    viewsets.ModelViewSet,
):
    """Create is open to any authenticated user; per-row mutation is owner-only."""

    queryset = (
        Product.objects.select_related("category", "created_by")
        .prefetch_related("tags")
        .annotate(deals_count=Count("deals", distinct=True))
    )
    lookup_field = "slug"
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = ProductFilter
    search_fields = ("name", "description")
    ordering_fields = ("price", "created_at")
    read_serializer_class = ProductReadSerializer
    write_serializer_class = ProductWriteSerializer

    def perform_create(self, serializer: BaseSerializer) -> None:
        # Stamp ``created_by`` from the request — never trust client input.
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer: BaseSerializer) -> None:
        product = serializer.save()
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        async_to_sync(channel_layer.group_send)(
            "inventory_updates",
            {
                "type": "inventory_update",
                "product_id": product.id,
                "stock_count": getattr(product, "stock_count", None),
                "in_stock": product.in_stock,
            },
        )


# Deal
@extend_schema_view(
    list=extend_schema(
        summary="List deals",
        description=(
            "Requires JWT authentication. Supports status, client, product, amount range, "
            "creation date range, search, and ordering filters. Returns nested client and "
            "optimized nested product details."
        ),
        tags=["Deals"],
        request=None,
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, description="Deal status"),
            OpenApiParameter("client", OpenApiTypes.INT, description="Client id"),
            OpenApiParameter("product", OpenApiTypes.INT, description="Product id"),
            OpenApiParameter("min_amount", OpenApiTypes.NUMBER, description="Min amount"),
            OpenApiParameter("max_amount", OpenApiTypes.NUMBER, description="Max amount"),
            OpenApiParameter("created_after", OpenApiTypes.DATETIME, description="Created after"),
            OpenApiParameter("created_before", OpenApiTypes.DATETIME, description="Created before"),
            OpenApiParameter("search", OpenApiTypes.STR, description="Search by title"),
            OpenApiParameter("ordering", OpenApiTypes.STR, description="amount or created_at"),
        ],
        responses={
            status.HTTP_200_OK: DealReadSerializer(many=True),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
        },
        examples=[
            OpenApiExample(
                "Deal list response",
                value=[
                    {
                        "id": 1,
                        "client": 1,
                        "product": 1,
                        "title": "Enterprise rollout",
                        "amount": "12000.00",
                        "status": "new",
                        "closed_at": None,
                        "created_by": 1,
                    }
                ],
                response_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve deal",
        description=(
            "Requires JWT authentication. Returns one deal with nested "
            "client/product details."
        ),
        tags=["Deals"],
        request=None,
        responses={
            status.HTTP_200_OK: DealReadSerializer,
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Deal not found"),
        },
        examples=[
            OpenApiExample(
                "Deal detail response",
                value={
                    "id": 1,
                    "client": 1,
                    "product": 1,
                    "title": "Enterprise rollout",
                    "amount": "12000.00",
                    "status": "new",
                    "closed_at": None,
                    "created_by": 1,
                },
                response_only=True,
            ),
        ],
    ),
    create=extend_schema(
        summary="Create deal",
        description=(
            "Requires JWT authentication. Any authenticated user may create a deal; "
            "created_by is set from request.user."
        ),
        tags=["Deals"],
        request=DealWriteSerializer,
        responses={
            status.HTTP_201_CREATED: DealReadSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
        },
        examples=[
            OpenApiExample(
                "Create deal request",
                value={
                    "client": 1,
                    "product": 1,
                    "title": "Enterprise rollout",
                    "amount": "12000.00",
                    "status": "new",
                    "closed_at": None,
                },
                request_only=True,
            ),
        ],
    ),
    update=extend_schema(
        summary="Replace deal",
        description="Requires JWT authentication and deal owner or staff permission.",
        tags=["Deals"],
        request=DealWriteSerializer,
        responses={
            status.HTTP_200_OK: DealReadSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(
                description="Owner or staff permission required"
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Deal not found"),
        },
        examples=[
            OpenApiExample(
                "Replace deal request",
                value={
                    "client": 1,
                    "product": 1,
                    "title": "Enterprise rollout",
                    "amount": "15000.00",
                    "status": "in_progress",
                    "closed_at": None,
                },
                request_only=True,
            ),
        ],
    ),
    partial_update=extend_schema(
        summary="Patch deal",
        description="Requires JWT authentication and deal owner or staff permission.",
        tags=["Deals"],
        request=DealWriteSerializer,
        responses={
            status.HTTP_200_OK: DealReadSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(
                description="Owner or staff permission required"
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Deal not found"),
        },
        examples=[
            OpenApiExample("Patch deal request", value={"status": "closed_won"}, request_only=True),
        ],
    ),
    destroy=extend_schema(
        summary="Delete deal",
        description="Requires JWT authentication and deal owner or staff permission.",
        tags=["Deals"],
        request=None,
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description="Deal deleted"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(
                description="Owner or staff permission required"
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Deal not found"),
        },
        examples=[
            OpenApiExample("Delete deal response", value=None, response_only=True),
        ],
    ),
)
class DealViewSet(
    DealCacheInvalidationMixin,
    OwnerMutationPermissionMixin,
    ReadWriteSerializerMixin,
    viewsets.ModelViewSet,
):
    """Create is open to any authenticated user; per-row mutation is owner-only."""

    queryset = Deal.objects.select_related("client", "created_by").prefetch_related(
        Prefetch(
            "product",
            queryset=Product.objects.select_related("category", "created_by")
            .prefetch_related("tags")
            .annotate(deals_count=Count("deals", distinct=True)),
        )
    )
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = DealFilter
    search_fields = ("title",)
    ordering_fields = ("amount", "created_at")
    read_serializer_class = DealReadSerializer
    write_serializer_class = DealWriteSerializer

# Task
@extend_schema_view(
    list=extend_schema(
        summary="List tasks",
        description=(
            "Requires JWT authentication. Supports status, assignee, client, deal, due-date, "
            "search, and ordering filters. Returns task records with optimized FK loading."
        ),
        tags=["Tasks"],
        request=None,
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, description="Task status"),
            OpenApiParameter("assigned_to", OpenApiTypes.INT, description="Assignee id"),
            OpenApiParameter("client", OpenApiTypes.INT, description="Client id"),
            OpenApiParameter("deal", OpenApiTypes.INT, description="Deal id"),
            OpenApiParameter("due_date_from", OpenApiTypes.DATETIME, description="Due date from"),
            OpenApiParameter("due_date_to", OpenApiTypes.DATETIME, description="Due date to"),
            OpenApiParameter("search", OpenApiTypes.STR, description="Search title or description"),
            OpenApiParameter("ordering", OpenApiTypes.STR, description="due_date or created_at"),
        ],
        responses={
            status.HTTP_200_OK: TaskReadSerializer(many=True),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
        },
        examples=[
            OpenApiExample(
                "Task list response",
                value=[
                    {
                        "id": 1,
                        "title": "Call client",
                        "description": "Confirm next steps",
                        "assigned_to": 1,
                        "client": 1,
                        "deal": 1,
                        "status": "pending",
                        "due_date": "2026-05-20T09:00:00Z",
                    }
                ],
                response_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve task",
        description="Requires JWT authentication. Any authenticated user may read a task.",
        tags=["Tasks"],
        request=None,
        responses={
            status.HTTP_200_OK: TaskReadSerializer,
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Task not found"),
        },
        examples=[
            OpenApiExample(
                "Task detail response",
                value={
                    "id": 1,
                    "title": "Call client",
                    "description": "Confirm next steps",
                    "assigned_to": 1,
                    "client": 1,
                    "deal": 1,
                    "status": "pending",
                    "due_date": "2026-05-20T09:00:00Z",
                },
                response_only=True,
            ),
        ],
    ),
    create=extend_schema(
        summary="Create task",
        description="Requires JWT authentication. Any authenticated user may create a task.",
        tags=["Tasks"],
        request=TaskWriteSerializer,
        responses={
            status.HTTP_201_CREATED: TaskReadSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
        },
        examples=[
            OpenApiExample(
                "Create task request",
                value={
                    "title": "Call client",
                    "description": "Confirm next steps",
                    "assigned_to": 1,
                    "client": 1,
                    "deal": 1,
                    "status": "pending",
                    "due_date": "2026-05-20T09:00:00Z",
                },
                request_only=True,
            ),
        ],
    ),
    update=extend_schema(
        summary="Replace task",
        description="Requires JWT authentication and assignee or staff permission.",
        tags=["Tasks"],
        request=TaskWriteSerializer,
        responses={
            status.HTTP_200_OK: TaskReadSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(
                description="Assignee or staff permission required"
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Task not found"),
        },
        examples=[
            OpenApiExample(
                "Replace task request",
                value={
                    "title": "Call client",
                    "description": "Confirmed next steps",
                    "assigned_to": 1,
                    "client": 1,
                    "deal": 1,
                    "status": "in_progress",
                    "due_date": "2026-05-20T09:00:00Z",
                },
                request_only=True,
            ),
        ],
    ),
    partial_update=extend_schema(
        summary="Patch task",
        description="Requires JWT authentication and assignee or staff permission.",
        tags=["Tasks"],
        request=TaskWriteSerializer,
        responses={
            status.HTTP_200_OK: TaskReadSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(
                description="Assignee or staff permission required"
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Task not found"),
        },
        examples=[
            OpenApiExample("Patch task request", value={"status": "completed"}, request_only=True),
        ],
    ),
    destroy=extend_schema(
        summary="Delete task",
        description="Requires JWT authentication and assignee or staff permission.",
        tags=["Tasks"],
        request=None,
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description="Task deleted"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(
                description="Assignee or staff permission required"
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Task not found"),
        },
        examples=[
            OpenApiExample("Delete task response", value=None, response_only=True),
        ],
    ),
)
class TaskViewSet(
    OwnerMutationPermissionMixin,
    ReadWriteSerializerMixin,
    viewsets.ModelViewSet,
):
    """Only the assignee (or staff) can mutate a task."""

    queryset = Task.objects.select_related("assigned_to", "client", "deal")
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = TaskFilter
    search_fields = ("title", "description")
    ordering_fields = ("due_date", "created_at")
    read_serializer_class = TaskReadSerializer
    write_serializer_class = TaskWriteSerializer

    @extend_schema(
        summary="Task comments",
        description=(
            "Requires JWT authentication. GET lists comments for this task; POST creates "
            "a task comment with author set from request.user."
        ),
        tags=["Tasks"],
        request=CommentWriteSerializer,
        responses={
            status.HTTP_200_OK: CommentReadSerializer(many=True),
            status.HTTP_201_CREATED: CommentReadSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Task not found"),
        },
        examples=[
            OpenApiExample(
                "Create task comment request",
                value={"body": "Called successfully."},
                request_only=True,
            ),
            OpenApiExample(
                "Task comments response",
                value=[
                    {
                        "id": 1,
                        "author": 1,
                        "content_type": "task",
                        "object_id": 1,
                        "body": "Called successfully.",
                    }
                ],
                response_only=True,
            ),
        ],
    )
    @action(detail=True, methods=["get", "post"], url_path="comments")
    def comments(self, request: Request, pk: int | None = None) -> Response:
        """Nested convenience endpoint for a single task's comments."""
        task = self.get_object()
        task_ct = ContentType.objects.get_for_model(Task)

        if request.method == "GET":
            qs = Comment.objects.filter(content_type=task_ct, object_id=task.id).select_related(
                "author"
            )
            data = CommentReadSerializer(qs, many=True, context={"request": request}).data
            return Response(data, status=status.HTTP_200_OK)

        """POST — server fills in content_type/object_id from URL context, so
        the client only needs to send ``body``. We inject them BEFORE
        validation rather than passing them via save() — otherwise the
        serializer's "this field is required" check fires first.
        ``request.data`` is either a plain ``dict`` (JSON body) or a Django
        ``QueryDict`` (form-data). Both expose ``.copy()`` and accept
        subscript assignment, so this works uniformly — using ``{**...}``
        instead would unpack QueryDict values as one-element lists.'"""

        payload = request.data.copy()
        payload["content_type"] = "task"
        payload["object_id"] = task.id
        writer = CommentWriteSerializer(data=payload, context={"request": request})
        writer.is_valid(raise_exception=True)
        # ``author`` is the only field the user is never allowed to set.
        writer.save(author=request.user)
        return Response(writer.data, status=status.HTTP_201_CREATED)


# Comment
@extend_schema_view(
    list=extend_schema(
        summary="List comments",
        description=(
            "Requires JWT authentication. Supports filtering by target model and object id. "
            "Returns comments with author/content-type data selected efficiently."
        ),
        tags=["Comments"],
        request=None,
        parameters=[
            OpenApiParameter("target", OpenApiTypes.STR, description="Target model: deal | task"),
            OpenApiParameter("object_id", OpenApiTypes.INT, description="Target object id"),
        ],
        responses={
            status.HTTP_200_OK: CommentReadSerializer(many=True),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
        },
        examples=[
            OpenApiExample(
                "Comment list response",
                value=[
                    {
                        "id": 1,
                        "author": 1,
                        "content_type": "deal",
                        "object_id": 1,
                        "body": "Decision maker asked for a proposal.",
                    }
                ],
                response_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve comment",
        description="Requires JWT authentication. Any authenticated user may read a comment.",
        tags=["Comments"],
        request=None,
        responses={
            status.HTTP_200_OK: CommentReadSerializer,
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Comment not found"),
        },
        examples=[
            OpenApiExample(
                "Comment detail response",
                value={
                    "id": 1,
                    "author": 1,
                    "content_type": "deal",
                    "object_id": 1,
                    "body": "Decision maker asked for a proposal.",
                },
                response_only=True,
            ),
        ],
    ),
    create=extend_schema(
        summary="Create comment",
        description=(
            "Requires JWT authentication. Any authenticated user may create a comment; "
            "author is set from request.user."
        ),
        tags=["Comments"],
        request=CommentWriteSerializer,
        responses={
            status.HTTP_201_CREATED: CommentReadSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Validation error"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
        },
        examples=[
            OpenApiExample(
                "Create comment request",
                value={"content_type": "deal", "object_id": 1, "body": "Send proposal tomorrow."},
                request_only=True,
            ),
        ],
    ),
    update=extend_schema(
        summary="Replace comment",
        description="Not exposed by this API. Comments are append-only; use delete and recreate.",
        tags=["Comments"],
        request=CommentWriteSerializer,
        responses={
            status.HTTP_405_METHOD_NOT_ALLOWED: OpenApiResponse(description="Method not allowed"),
        },
        examples=[
            OpenApiExample(
                "Replace comment request",
                value={"content_type": "deal", "object_id": 1, "body": "Updated body."},
                request_only=True,
            ),
        ],
    ),
    partial_update=extend_schema(
        summary="Patch comment",
        description="Not exposed by this API. Comments are append-only; use delete and recreate.",
        tags=["Comments"],
        request=CommentWriteSerializer,
        responses={
            status.HTTP_405_METHOD_NOT_ALLOWED: OpenApiResponse(description="Method not allowed"),
        },
        examples=[
            OpenApiExample(
                "Patch comment request",
                value={"body": "Updated body."},
                request_only=True,
            ),
        ],
    ),
    destroy=extend_schema(
        summary="Delete comment",
        description="Requires JWT authentication and comment author or staff permission.",
        tags=["Comments"],
        request=None,
        responses={
            status.HTTP_204_NO_CONTENT: OpenApiResponse(description="Comment deleted"),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(description="Unauthorized"),
            status.HTTP_403_FORBIDDEN: OpenApiResponse(
                description="Author or staff permission required"
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="Comment not found"),
        },
        examples=[
            OpenApiExample("Delete comment response", value=None, response_only=True),
        ],
    ),
)
class CommentViewSet(
    OwnerMutationPermissionMixin,
    ReadWriteSerializerMixin,
    viewsets.ModelViewSet,
):
    """Generic comments attached to a Task or Deal."""

    # No PATCH / PUT — comments are append-only by design.
    http_method_names = ("get", "post", "delete")  # type: ignore
    owner_mutation_actions = frozenset({"destroy"})
    read_serializer_class = CommentReadSerializer
    write_serializer_class = CommentWriteSerializer

    def get_queryset(self) -> QuerySet[Comment]:
        # ``self.request`` is a DRF ``Request`` at runtime, but DRF generics
        # type it as Django's ``HttpRequest`` — re-bind it locally so Pylance
        # sees the right surface (``query_params``, ``data``, ``user`` …).
        request: Request = self.request  # type: ignore[assignment]
        qs: QuerySet[Comment] = Comment.objects.select_related("author", "content_type")
        target: str | None = request.query_params.get("target")
        object_id: str | None = request.query_params.get("object_id")

        if target:
            # ``model__iexact`` keeps the lookup case-insensitive and safe.
            ct = ContentType.objects.filter(model__iexact=target).first()
            if ct is None:
                # Unknown target → empty result set, not a server error.
                return qs.none()
            qs = qs.filter(content_type=ct)

        if object_id:
            qs = qs.filter(object_id=object_id)
        return qs

    def perform_create(self, serializer: BaseSerializer) -> None:
        # Author is injected from the request — never trusted from input.
        serializer.save(author=self.request.user)

@database_sync_to_async
def _get_dashboard_database_counts() -> dict[str, int]:
    return {
        "clients_count": Client.objects.count(),
        "deals_count": Deal.objects.count(),
        "tasks_count": Task.objects.count(),
    }

async def _fetch_exchange_rates() -> dict[str, Any]:
    url = "https://open.er-api.com/v6/latest/USD"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
        rates = payload.get("rates", {})
        return {
            "base": payload.get("base_code", "USD"),
            "rates":{
                "KZT": rates.get("KZT"),
                "RUB": rates.get("RUB"),
                "EUR": rates.get("EUR"),
            },
        }
    except Exception as exc:
        logger.warning("failed to fetch exchange rates: %s", exc)
        return {
            "base": "USD",
            "rates": {
                "KZT": None,
                "RUB": None,
                "EUR": None,
            },
            "error": "exchange_rates_unavailable",
        }

async def _fetch_almaty_time() -> dict[str, Any]:
    url = "https://timeapi.io/api/time/current/zone?timeZone=Asia/Almaty"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
            return {
                "dateTime": payload.get("datetime"),
                "date": payload.get("date"),
                "time": payload.get("time"),
                "timeZone": payload.get("timeZone", "Asia/Almaty"),
            }
    except Exception as exc:
        logger.warning("failed to fetch almaty time: %s", exc)
        return {
            "dateTime": None,
            "date": None,
            "time": None,
            "timeZone": "Asia/Almaty",
            "error": "almaty_time_unavailable",
        }

class DashboardStatsResponceSerializer(serializers.Serializer):
    database = serializers.DictField(
        child=serializers.IntegerField(),
        help_text="Database entity counts",
    )
    exchange_rates = serializers.DictField(
        help_text="Exchange rate payload",
    )
    almaty_time = serializers.DictField(
        help_text="Current Almaty time payload",
    )

@extend_schema(
    summary="get Dashboard stats",
    description="Get Dashboard stats",
    tags=["Dashboard"],
    parameters=[],
    auth=[],
    responses={
        200: DashboardStatsResponceSerializer,
    },
    examples=[
        OpenApiExample(
            "dashboard stats response",
            value={
                "database": {
                    "clients_count": 12,
                    "deals_count": 8,
                    "tasks_count": 21,
                },
                "exchange_rates": {
                    "base": "USD",
                    "rates": {
                        "KZT": 500,
                        "RUB": 100,
                        "EUR": 0.90,
                    },
                },
                "almaty_time": {
                    "dateTime": "2026-05-16T14:30:00",
                    "date": "2026-05-16",
                    "time": "14:30",
                    "timeZone": "Asia/Almaty",
                },
            },
            response_only=True,
        ),
    ],
)
async def get_dashboard_stats(request: HttpRequest) -> JsonResponse:
    database_counts, exchange_rates, almaty_time = await asyncio.gather(
        _get_dashboard_database_counts(),
        _fetch_exchange_rates(),
        _fetch_almaty_time(),
    )
    return JsonResponse(
        {
            "database": database_counts,
            "exchange_rates": exchange_rates,
            "almaty_time": almaty_time,
        }
    )
