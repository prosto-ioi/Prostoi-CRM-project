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
from typing import ClassVar, cast, Any
from .pubsub import publish_deal_event
import httpx
from channels.db import database_sync_to_async
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType
from django.db.models import QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view, OpenApiResponse, OpenApiExample
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework import serializers
from .serializers import ProductReadSerializer, ProductWriteSerializer
from django.db import transaction
from .cache import (
    get_deals_list_cache,
    invalidate_deals_cache,
    set_deals_list_cache,
)
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .filters import DealFilter, ProductFilter, TaskFilter
from .models import Category, Client, Comment, Deal, Product, Tag, Task
from .permissions import IsAdminOrReadOnly, IsOwnerOrReadOnly
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


# Category 
@extend_schema_view(
    list=extend_schema(summary="List categories", tags=["Categories"]),
    retrieve=extend_schema(summary="Retrieve category", tags=["Categories"]),
    create=extend_schema(summary="Create category (staff only)", tags=["Categories"]),
    update=extend_schema(summary="Replace category (staff only)", tags=["Categories"]),
    partial_update=extend_schema(summary="Patch category (staff only)", tags=["Categories"]),
    destroy=extend_schema(summary="Delete category (staff only)", tags=["Categories"]),
)
class CategoryViewSet(ReadWriteSerializerMixin, viewsets.ModelViewSet):
    """Public to read; staff-only to write."""

    queryset = Category.objects.all()
    lookup_field = "slug"
    permission_classes = (IsAdminOrReadOnly,)
    read_serializer_class = CategoryReadSerializer
    write_serializer_class = CategoryWriteSerializer


# Tag 
@extend_schema_view(
    list=extend_schema(summary="List tags", tags=["Tags"]),
    retrieve=extend_schema(summary="Retrieve tag", tags=["Tags"]),
    create=extend_schema(summary="Create tag (staff only)", tags=["Tags"]),
    update=extend_schema(summary="Replace tag (staff only)", tags=["Tags"]),
    partial_update=extend_schema(summary="Patch tag (staff only)", tags=["Tags"]),
    destroy=extend_schema(summary="Delete tag (staff only)", tags=["Tags"]),
)
class TagViewSet(ReadWriteSerializerMixin, viewsets.ModelViewSet): 
    """Public to read; staff-only to write."""

    queryset = Tag.objects.all()
    lookup_field = "slug"
    permission_classes = (IsAdminOrReadOnly,)
    read_serializer_class = TagReadSerializer
    write_serializer_class = TagWriteSerializer


# Client 
@extend_schema_view(
    list=extend_schema(summary="List clients", tags=["Clients"]),
    retrieve=extend_schema(summary="Retrieve client", tags=["Clients"]),
    create=extend_schema(summary="Create client", tags=["Clients"]),
    update=extend_schema(summary="Replace client", tags=["Clients"]),
    partial_update=extend_schema(summary="Patch client", tags=["Clients"]),
    destroy=extend_schema(summary="Delete client", tags=["Clients"]),
)
class ClientViewSet(ReadWriteSerializerMixin, viewsets.ModelViewSet):
    """Any authenticated user can manage clients (no per-row ownership)."""

    queryset = Client.objects.all()
    permission_classes = (IsAuthenticated,)
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
            "Returns a list"
            "Requires IsAuthenticated"
        ),
        tags=["Products"],
        responses={
            200: ProductReadSerializer(many=True),
            401: OpenApiResponse(description="Unauthorized"),
        },
    ),
    retrieve=extend_schema(
        summary="Retrieve product",
        description=(
            "Returns one product by its lookup field"
            "Requires IsAuthenticated"
        ),
        tags=["Products"],
        responses={
            200: ProductReadSerializer,
            401: OpenApiResponse(description="Unauthorized"),
            404: OpenApiResponse(description="Not found"),
        },
    ),
    create=extend_schema(
        summary="Create product",
        description=(
            "Creates a new product"
            "Requires IsAuthenticated"
        ),
        tags=["Products"],
        request=ProductWriteSerializer,
        responses={
            201: ProductReadSerializer,
            400: OpenApiResponse(description="validation error"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="authenticated user doesn't have permission"),
        },
        examples=[
            OpenApiExample(
                "Create a product request",
                value={
                    "name": "coffee",
                    "category": 1,
                    "tags": [1,2],
                    "price": "4500.00",
                    "description": "Arabica coffee",
                    "in_stock": True,
                },
                response_only=True,
            ),
        ],
    ),
)
class ProductViewSet(ReadWriteSerializerMixin, viewsets.ModelViewSet):
    """Create is open to any authenticated user; per-row mutation is owner-only."""

    queryset = Product.objects.select_related("category", "created_by").prefetch_related("tags")
    lookup_field = "slug"
    filter_backends = (DjangoFilterBackend,)
    filterset_class = ProductFilter
    search_fields = ("name", "description")
    ordering_fields = ("price", "created_at")
    read_serializer_class = ProductReadSerializer
    write_serializer_class = ProductWriteSerializer

    def get_permissions(self) -> list[BasePermission]:
        """``update`` / ``destroy`` → owner-only; anything else → authenticated."""
        if _current_action(self) in _OBJECT_MUTATE_ACTIONS:
            return [IsOwnerOrReadOnly()]
        return [IsAuthenticated()]

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
            "Filters: `?status=new|in_progress|closed_won|closed_lost`, "
            "`?client=id`, `?min_amount=1000`, `?max_amount=50000`."
        ),
        tags=["Deals"],
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, description="Deal status"),
            OpenApiParameter("client", OpenApiTypes.INT, description="Client id"),
            OpenApiParameter("min_amount", OpenApiTypes.NUMBER, description="Min amount"),
            OpenApiParameter("max_amount", OpenApiTypes.NUMBER, description="Max amount"),
        ],
    ),
    retrieve=extend_schema(summary="Retrieve deal", tags=["Deals"]),
    create=extend_schema(summary="Create deal", tags=["Deals"]),
    update=extend_schema(summary="Replace deal (owner/staff)", tags=["Deals"]),
    partial_update=extend_schema(summary="Patch deal (owner/staff)", tags=["Deals"]),
    destroy=extend_schema(summary="Delete deal (owner/staff)", tags=["Deals"]),
)
class DealViewSet(ReadWriteSerializerMixin, viewsets.ModelViewSet):
    """Create is open to any authenticated user; per-row mutation is owner-only."""

    queryset = Deal.objects.select_related("client", "product", "created_by")
    filter_backends = (DjangoFilterBackend,)
    filterset_class = DealFilter
    search_fields = ("title",)
    ordering_fields = ("amount", "created_at")
    read_serializer_class = DealReadSerializer
    write_serializer_class = DealWriteSerializer

    def get_permissions(self) -> list[BasePermission]:
        if _current_action(self) in _OBJECT_MUTATE_ACTIONS:
            return [IsOwnerOrReadOnly()]
        return [IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        cached = get_deals_list_cache()
        if cached is not None:
            return Response(cached)
        
        response = super().list(request, *args, **kwargs)
        set_deals_list_cache(response.data)
        return response

    def perform_create(self, serializer):
        deal = serializer.save(created_by=self.request.user)
        invalidate_deals_cache()
        publish_deal_event("deal_created", deal.id)

    def perform_update(self, serializer):
        deal = serializer.save()
        invalidate_deals_cache()
        publish_deal_event("deal_updated", deal.id)

    def perform_destroy(self, instance):
        deal_id = instance.id
        instance.delete()
        invalidate_deals_cache()
        publish_deal_event("deal_deleted", deal_id)

# Task 
@extend_schema_view(
    list=extend_schema(
        summary="List tasks",
        description=(
            "Filters: `?status=pending|in_progress|completed`, "
            "`?assigned_to=id`, `?client=id`, `?deal=id`."
        ),
        tags=["Tasks"],
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, description="Task status"),
            OpenApiParameter("assigned_to", OpenApiTypes.INT, description="Assignee id"),
            OpenApiParameter("client", OpenApiTypes.INT, description="Client id"),
            OpenApiParameter("deal", OpenApiTypes.INT, description="Deal id"),
        ],
    ),
    retrieve=extend_schema(summary="Retrieve task", tags=["Tasks"]),
    create=extend_schema(summary="Create task", tags=["Tasks"]),
    update=extend_schema(summary="Replace task (assignee/staff)", tags=["Tasks"]),
    partial_update=extend_schema(summary="Patch task (assignee/staff)", tags=["Tasks"]),
    destroy=extend_schema(summary="Delete task (assignee/staff)", tags=["Tasks"]),
)
class TaskViewSet(ReadWriteSerializerMixin, viewsets.ModelViewSet):
    """Only the assignee (or staff) can mutate a task."""

    queryset = Task.objects.select_related("assigned_to", "client", "deal")
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TaskFilter
    search_fields = ("title", "description")
    ordering_fields = ("due_date", "created_at")
    read_serializer_class = TaskReadSerializer
    write_serializer_class = TaskWriteSerializer

    def get_permissions(self) -> list[BasePermission]:
        if _current_action(self) in _OBJECT_MUTATE_ACTIONS:
            return [IsOwnerOrReadOnly()]
        return [IsAuthenticated()]

    @extend_schema(
        summary="Task comments",
        description="GET — list this task's comments. POST — add a comment.",
        tags=["Tasks"],
        responses={
            status.HTTP_200_OK: CommentReadSerializer(many=True),
            status.HTTP_201_CREATED: CommentReadSerializer,
        },
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
        description="Filters: `?target=deal|task`, `?object_id=1`.",
        tags=["Comments"],
        parameters=[
            OpenApiParameter("target", OpenApiTypes.STR, description="Target model: deal | task"),
            OpenApiParameter("object_id", OpenApiTypes.INT, description="Target object id"),
        ],
    ),
    create=extend_schema(summary="Create comment", tags=["Comments"]),
    destroy=extend_schema(summary="Delete comment (author/staff)", tags=["Comments"]),
)
class CommentViewSet(ReadWriteSerializerMixin, viewsets.ModelViewSet):
    """Generic comments attached to a Task or Deal."""

    # No PATCH / PUT — comments are append-only by design.
    http_method_names = ("get", "post", "delete")  # type: ignore
    read_serializer_class = CommentReadSerializer
    write_serializer_class = CommentWriteSerializer

    def get_permissions(self) -> list[BasePermission]:
        # Only the author (or staff) can delete; anyone authenticated can list/create.
        if _current_action(self) == "destroy":
            return [IsOwnerOrReadOnly()]
        return [IsAuthenticated()]

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
            payload = await response.json()
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
        logger.warning("failed to fetch exchange rates", exc)
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
async def get_dashboard_stats(request):
    database_counts, exchange_rates, almaty_time = await asyncio.gather(
        _get_dashboard_database_counts(),
        _fetch_exchange_rates(),
        _fetch_almaty_time(),
    )
    return JsonResponse(
        {
            "database_counts": database_counts,
            "exchange_rates": exchange_rates,
            "almaty_time": almaty_time,
        }
    )