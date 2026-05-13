"""Django-filter filter sets for the CRM list endpoints.

Each filter exposes a documented query-string contract used by the
corresponding viewset and surfaced in the OpenAPI schema.
"""
from __future__ import annotations

import django_filters
from django.db.models import Q, QuerySet

from .models import Deal, Product, Task


class ProductFilter(django_filters.FilterSet):
    """Filter products by category slug, price range, stock, and free-text search."""

    category = django_filters.CharFilter(field_name="category__slug", lookup_expr="exact")
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    in_stock = django_filters.BooleanFilter(field_name="in_stock")
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = Product
        fields = ("category", "price", "in_stock")

    def filter_search(
        self, queryset: QuerySet[Product], name: str, value: str,
    ) -> QuerySet[Product]:
        """Search both ``name`` and ``description`` case-insensitively."""
        # ``Q`` is preferred over chaining ``|`` of two filter() calls — it builds
        # a single SQL OR rather than a UNION-style query.
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))


class TaskFilter(django_filters.FilterSet):
    """Filter tasks by status, assignee, related client, related deal, and due-date range."""

    # ``.Status.choices`` replaces the old ``.STATUS_CHOICES`` constant, which
    # disappeared when we migrated the model to ``TextChoices``.
    status = django_filters.ChoiceFilter(choices=Task.Status.choices)
    assigned_to = django_filters.NumberFilter(field_name="assigned_to__id")
    client = django_filters.NumberFilter(field_name="client__id")
    deal = django_filters.NumberFilter(field_name="deal__id")
    due_date_from = django_filters.DateTimeFilter(field_name="due_date", lookup_expr="gte")
    due_date_to = django_filters.DateTimeFilter(field_name="due_date", lookup_expr="lte")

    class Meta:
        model = Task
        fields = ("status", "assigned_to", "client", "deal")


class DealFilter(django_filters.FilterSet):
    """Filter deals by status, client, product, amount range, and creation date range."""

    status = django_filters.ChoiceFilter(choices=Deal.Status.choices)
    client = django_filters.NumberFilter(field_name="client__id")
    product = django_filters.NumberFilter(field_name="product__id")
    min_amount = django_filters.NumberFilter(field_name="amount", lookup_expr="gte")
    max_amount = django_filters.NumberFilter(field_name="amount", lookup_expr="lte")
    created_after = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = Deal
        fields = ("status", "client", "product")