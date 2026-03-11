from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.contenttypes.models import ContentType
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes


from .models import Category, Tag, Client, Product, Deal, Task, Comment
from .serializers import (
    CategorySerializer, TagSerializer, ClientSerializer,
    ProductSerializer, DealSerializer, TaskSerializer, CommentSerializer,
)
from .permission import IsOwnerOrReadOnly, IsStaffOrReadOnly, IsCommentAuthor
from .filters import ProductFilter, DealFilter, TaskFilter


@extend_schema_view(
    list=extend_schema(summary='Список категорий', tags=['Categories']),
    retrieve=extend_schema(summary='Детали категории', tags=['Categories']),
    create=extend_schema(summary='Создать категорию', description='Только staff/admin', tags=['Categories'], responses={201: CategorySerializer, 400: None, 403: None}),
    update=extend_schema(summary='Обновить категорию (PUT)', tags=['Categories']),
    partial_update=extend_schema(summary='Обновить категорию (PATCH)', tags=['Categories']),
    destroy=extend_schema(summary='Удалить категорию', tags=['Categories']),
)
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    permission_classes = [IsStaffOrReadOnly]


@extend_schema_view(
    list=extend_schema(summary='Список тегов', tags=['Tags']),
    retrieve=extend_schema(summary='Детали тега', tags=['Tags']),
    create=extend_schema(summary='Создать тег', description='Только staff/admin', tags=['Tags']),
    update=extend_schema(summary='Обновить тег (PUT)', tags=['Tags']),
    partial_update=extend_schema(summary='Обновить тег (PATCH)', tags=['Tags']),
    destroy=extend_schema(summary='Удалить тег', tags=['Tags']),
)
class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    lookup_field = 'slug'
    permission_classes = [IsStaffOrReadOnly]


@extend_schema_view(
    list=extend_schema(summary='Список клиентов',description='Поддерживает пагинацию' , tags=['Clients']),
    retrieve=extend_schema(summary='Детали клиента', tags=['Clients']),
    create=extend_schema(summary='Создать клиента', description='Email должен быть уникальным.', tags=['Clients'], responses={201: CategorySerializer, 400: None, 401: None}),
    update=extend_schema(summary='Обновить клиента (PUT)', tags=['Clients']),
    partial_update=extend_schema(summary='Обновить клиента (PATCH)', tags=['Clients']),
    destroy=extend_schema(summary='Удалить клиента', tags=['Clients']),
)
class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsOwnerOrReadOnly]

@extend_schema_view(
    list=extend_schema(
        summary='Список продуктов',
        description='Фильтры: `?category=slug`, `?min_price=100`, `?max_price=500`, `?in_stock=true`, `?search=...`, `?ordering=price`',
        tags=['Products'],
        parameters=[
            OpenApiParameter('category', OpenApiTypes.STR, description='Slug категории'),
            OpenApiParameter('min_price', OpenApiTypes.NUMBER, description='Минимальная цена'),
            OpenApiParameter('max_price', OpenApiTypes.NUMBER, description='Максимальная цена'),
            OpenApiParameter('in_stock', OpenApiTypes.BOOL, description='Только в наличии'),
            OpenApiParameter('search', OpenApiTypes.STR, description='Поиск по названию и описанию'),
            OpenApiParameter('ordering', OpenApiTypes.STR, description='Сортировка: price, -price, created_at'),
        ],
    ),
    retrieve=extend_schema(summary='Детали продукта (по slug)', tags=['Products']),
    create=extend_schema(summary='Создать продукт', description='`created_by` устанавливается автоматически.', tags=['Products'], responses={201: ProductSerializer, 400: None, 401: None}),
    update=extend_schema(summary='Обновить продукт (PUT)', tags=['Products']),
    partial_update=extend_schema(summary='Обновить продукт (PATCH)', tags=['Products']),
    destroy=extend_schema(summary='Удалить продукт', description='Только создатель или staff.', tags=['Products'], responses={204: None, 403: None, 404: None}),
)
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category').prefetch_related('tags').all()
    serializer_class = ProductSerializer
    lookup_field = 'slug'
    permission_classes = [IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

@extend_schema_view(
    list=extend_schema(
        summary='Список сделок',
        description='Фильтры: `?status=new|in_progress|closed_won|closed_lost`, `?client=id`, `?min_amount=1000`, `?max_amount=50000`',
        tags=['Deals'],
        parameters=[
            OpenApiParameter('status', OpenApiTypes.STR, description='Статус сделки'),
            OpenApiParameter('client', OpenApiTypes.INT, description='ID клиента'),
            OpenApiParameter('min_amount', OpenApiTypes.NUMBER, description='Минимальная сумма'),
            OpenApiParameter('max_amount', OpenApiTypes.NUMBER, description='Максимальная сумма'),
        ],
    ),
    retrieve=extend_schema(summary='Детали сделки', tags=['Deals']),
    create=extend_schema(summary='Создать сделку', description='`created_by` устанавливается автоматически.', tags=['Deals'], responses={201: DealSerializer, 400: None, 401: None}),
    update=extend_schema(summary='Обновить сделку (PUT)', tags=['Deals']),
    partial_update=extend_schema(summary='Обновить сделку (PATCH)', tags=['Deals']),
    destroy=extend_schema(summary='Удалить сделку', description='Только создатель или staff.', tags=['Deals'], responses={204: None, 403: None, 404: None}),
)
class DealViewSet(viewsets.ModelViewSet):
    queryset = Deal.objects.select_related('client', 'product').all()
    serializer_class = DealSerializer
    permission_classes = [IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = DealFilter
    search_fields = ['title']
    ordering_fields = ['amount', 'created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

@extend_schema_view(
    list=extend_schema(
        summary='Список задач',
        description='Фильтры: `?status=pending|in_progress|completed`, `?assigned_to=id`, `?client=id`, `?deal=id`',
        tags=['Tasks'],
        parameters=[
            OpenApiParameter('status', OpenApiTypes.STR, description='Статус задачи'),
            OpenApiParameter('assigned_to', OpenApiTypes.INT, description='ID исполнителя'),
            OpenApiParameter('client', OpenApiTypes.INT, description='ID клиента'),
            OpenApiParameter('deal', OpenApiTypes.INT, description='ID сделки'),
        ],
    ),
    retrieve=extend_schema(summary='Детали задачи', tags=['Tasks']),
    create=extend_schema(summary='Создать задачу', tags=['Tasks']),
    update=extend_schema(summary='Обновить задачу (PUT)', tags=['Tasks']),
    partial_update=extend_schema(summary='Обновить задачу (PATCH)', tags=['Tasks']),
    destroy=extend_schema(summary='Удалить задачу', tags=['Tasks']),
)
class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.select_related('assigned_to', 'client', 'deal').all()
    serializer_class = TaskSerializer
    permission_classes = [IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = TaskFilter
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'created_at']

    @extend_schema(
        summary='Комментарии к задаче',
        description='GET — список комментариев задачи. POST — добавить комментарий.',
        tags=['Tasks'],
        responses={200: CommentSerializer(many=True), 201: CommentSerializer},
    )
    @action(detail=True, methods=['get', 'post'], url_path='comments')
    def comments(self, request, pk=None):
        task = self.get_object()
        if request.method == 'GET':
            comments = Comment.objects.filter(
                content_type=ContentType.objects.get_for_model(Task),
                object_id=task.id
            ).select_related('author')
            serializer = CommentSerializer(comments, many=True, context={'request': request})
            return Response(serializer.data)
        elif request.method == 'POST':
            serializer = CommentSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save(
                    author=request.user,
                    content_type=ContentType.objects.get_for_model(Task),
                    object_id=task.id
                )
                return Response(serializer.data, status=201)
            return Response(serializer.errors, status=400)

@extend_schema_view(
    list=extend_schema(
        summary='Список комментариев',
        description='Фильтрация: `?target=deal|task`, `?object_id=1`',
        tags=['Comments'],
        parameters=[
            OpenApiParameter('target', OpenApiTypes.STR, description='Тип объекта: deal или task'),
            OpenApiParameter('object_id', OpenApiTypes.INT, description='ID объекта'),
        ],
    ),
    create=extend_schema(summary='Создать комментарий', description='`author` устанавливается автоматически.', tags=['Comments']),
    destroy=extend_schema(summary='Удалить комментарий', description='Только автор или staff.', tags=['Comments'], responses={204: None, 403: None, 404: None}),
)
class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    http_method_names = ['get', 'post', 'delete']
    permission_classes = [IsCommentAuthor]

    def get_queryset(self):
        qs = Comment.objects.select_related('author', 'content_type').all()
        target = self.request.query_params.get('target')
        object_id = self.request.query_params.get('object_id')
        if target:
            ct = ContentType.objects.filter(model=target).first()
            if ct:
                qs = qs.filter(content_type=ct)
        if object_id:
            qs = qs.filter(object_id=object_id)
        return qs