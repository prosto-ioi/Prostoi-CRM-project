from django.contrib import admin
from .models import Category, Tag, Client, Product, Deal, Task, Comment


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name_en', 'name_ru', 'name_kk', 'slug')
    prepopulated_fields = {'slug': ('name_en',)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone', 'created_at')
    search_fields = ('first_name', 'last_name', 'email')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'in_stock', 'created_at')
    list_filter = ('in_stock', 'category')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'amount', 'status', 'created_at', 'closed_at')
    list_filter = ('status',)
    search_fields = ('title', 'client__first_name', 'client__last_name')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'assigned_to', 'status', 'due_date', 'created_at')
    list_filter = ('status',)
    search_fields = ('title',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'content_type', 'object_id', 'created_at')
    list_filter = ('content_type',)
