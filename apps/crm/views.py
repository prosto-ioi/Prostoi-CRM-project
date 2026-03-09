from rest_framework import viewsets
from django.contrib.contenttypes.models import ContentType

from .models import Category, Tag, Client, Product, Deal, Task, Comment
from .serializers import (
    CategorySerializer, TagSerializer, ClientSerializer,
    ProductSerializer, DealSerializer, TaskSerializer, CommentSerializer,
)
from .permission import isOwnerOrReadOnly, IsCommentAuthor, IsStaffOrReadOnly


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    permission_classes = [IsStaffOrReadOnly]


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    lookup_field = 'slug'
    permission_classes = [IsStaffOrReadOnly]


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [isOwnerOrReadOnly]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category').prefetch_related('tags').all()
    serializer_class = ProductSerializer
    lookup_field = 'slug'
    permission_classes = [isOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(created_by = self.request.user)


class DealViewSet(viewsets.ModelViewSet):
    queryset = Deal.objects.select_related('client', 'product').all()
    serializer_class = DealSerializer
    permission_classes = [isOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(created_by = self.request.user)


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.select_related('assigned_to', 'client', 'deal').all()
    serializer_class = TaskSerializer
    permission_classes = [isOwnerOrReadOnly]

# noinspection PyUnresolvedReferences
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
