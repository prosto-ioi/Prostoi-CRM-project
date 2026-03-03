from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType

from .models import Category, Tag, Client, Product, Deal, Task, Comment


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name_en', 'name_ru', 'name_kk', 'slug')
        read_only_fields = ('id', 'slug')


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')
        read_only_fields = ('id', 'slug')


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = (
            'id', 'first_name', 'last_name', 'email',
            'phone', 'address', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class ProductSerializer(serializers.ModelSerializer):
    category_detail = CategorySerializer(source='category', read_only=True)
    tags_detail = TagSerializer(source='tags', many=True, read_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=False,
    )

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'slug', 'category', 'category_detail',
            'tags', 'tags_detail', 'price', 'description',
            'in_stock', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'slug', 'created_at', 'updated_at')


class DealSerializer(serializers.ModelSerializer):
    client_detail = ClientSerializer(source='client', read_only=True)
    product_detail = ProductSerializer(source='product', read_only=True)

    class Meta:
        model = Deal
        fields = (
            'id', 'client', 'client_detail', 'product', 'product_detail',
            'title', 'amount', 'status', 'created_at', 'updated_at', 'closed_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = (
            'id', 'title', 'description', 'assigned_to',
            'client', 'deal', 'status', 'due_date',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.HiddenField(default=serializers.CurrentUserDefault())
    content_type = serializers.SlugRelatedField(
        queryset=ContentType.objects.filter(model__in=['task', 'deal']),
        slug_field='model',
    )

    class Meta:
        model = Comment
        fields = ('id', 'author', 'content_type', 'object_id', 'body', 'created_at')
        read_only_fields = ('id', 'created_at')