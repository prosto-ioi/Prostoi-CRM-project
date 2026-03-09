from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db.models import ForeignKey
from django.utils.text import slugify

class Category(models.Model):
    name_en = models.CharField('Name (EN)', max_length=100)
    name_ru = models.CharField('Название (RU)', max_length=100, blank=True, default='')
    name_kk = models.CharField('Атауы(KK)', max_length=100, blank=True, default='')
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name_en']


    def __str__(self):
        return self.name_en

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name_en)
        super().save(*args, **kwargs)

    def get_name(self, lang='en'):
        return getattr(self.name_en, f'name_{lang}') or self.name_en

class Tag(models.Model):
    name = models.CharField('Название', max_length=50, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = 'tag'
        verbose_name_plural = 'tags'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Client(models.Model):
    first_name = models.CharField('Имя', max_length=50)
    last_name = models.CharField('Фамилия', max_length=50)
    email = models.EmailField('Email', unique=True)
    phone = models.CharField('Телефон', max_length=20, blank=True, default='')
    address = models.CharField('Адрес', max_length=100, blank=True, default='')
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Оьнавлен', auto_now=True)

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

class Product(models.Model):
    name = models.CharField('Название', max_length = 200)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='products',
        verbose_name='Категория',
    )

    tags = models.ManyToManyField(Tag, blank=True, related_name='products', verbose_name='Теги')
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    description = models.TextField('Описание', blank=True, default='')
    in_stock = models.BooleanField('В наличии', default=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL, null=True, blank=True, related_name='created_product', verbose_name='Создал')

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Deal(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новая'), ('in_progress', 'В работе'), ('closed_won', 'Закрыта (успех)'), ('closed_lost', 'Закрыта (провал'),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='deals',
        verbose_name='Клиент',
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deals',
        verbose_name='Продукт',
    )

    title = models.CharField('Название', max_length=200)
    amount = models.DecimalField('Сумма', max_digits=10, decimal_places=2)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    closed_at = models.DateTimeField('Закрыта', blank=True, null=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL, null=True, blank=True, related_name='created_deal', verbose_name='Создал')


    class Meta:
        verbose_name = 'Сделка'
        verbose_name_plural = 'Сделки'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.client}"

class Task (models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает'), ('in_progress', 'В работе'), ('completed','Завершена'),
    ]

    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True, default='')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name='Исполнитель',
    )
    client = ForeignKey(
        Client,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tasks',
        verbose_name='Клиент',
    )
    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tasks',
        verbose_name='Сделка',
    )
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='pending')
    due_date = models.DateTimeField('Срок', blank=True, null=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)

    comments = GenericRelation('Comment', related_query_name='task')

    class Meta:
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class Comment(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Автор',
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name='Тип объекта',
    )
    object_id = models.PositiveIntegerField('ID объекта')
    content_object = GenericForeignKey('content_type', 'object_id')
    body = models.TextField('Текст')
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Коментарий'
        verbose_name_plural = 'Кщментарии'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"comment by {self.author} on {self.content_type.model}#{self.content_object.id}"