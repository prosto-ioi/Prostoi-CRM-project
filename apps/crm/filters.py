import django_filters
from .models import Product, Task, Deal

class ProductFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name='category__slug', lookup_expr='exact')
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    in_stock = django_filters.BooleanFilter(field_name='in_stock')
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Product
        fields = ['category', 'price', 'in_stock']

    def filter_search(self, queryset, name, value):
        return queryset.filter(name__icontains=value) | queryset.filter(description__icontains=value)


class TaskFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=Task.STATUS_CHOICES)
    assigned_to = django_filters.NumberFilter(field_name='assigned_to__id')
    client = django_filters.NumberFilter(field_name='client__id')
    deal = django_filters.NumberFilter(field_name='deal__id')
    due_date_from = django_filters.DateTimeFilter(field_name='due_date', lookup_expr='gte')
    due_date_to = django_filters.DateTimeFilter(field_name='due_date', lookup_expr='lte')

    class Meta:
        model = Task
        fields = ['status', 'assigned_to', 'client', 'deal']


class DealFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=Deal.STATUS_CHOICES)
    client = django_filters.NumberFilter(field_name='client__id')
    product = django_filters.NumberFilter(field_name='product__id')
    min_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    max_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Deal
        fields = ['status', 'client', 'product']