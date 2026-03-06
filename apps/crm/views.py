from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from django.contrib.contenttypes.models import ContentType

from .models import Category, Tag, Client, Product, Deal, Task, Comment
from .serializers import (
    CategorySerializer, TagSerializer, ClientSerializer,
    ProductSerializer, DealSerializer, TaskSerializer, CommentSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    lookup_field = 'slug'


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category').prefetch_related('tags').all()
    serializer_class = ProductSerializer
    lookup_field = 'slug'


class DealViewSet(viewsets.ModelViewSet):
    queryset = Deal.objects.select_related('client', 'product').all()
    serializer_class = DealSerializer


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.select_related('assigned_to', 'client', 'deal').all()
    serializer_class = TaskSerializer

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
            
                                            

# noinspection PyUnresolvedReferences
class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    http_method_names = ['get', 'post', 'delete']

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
