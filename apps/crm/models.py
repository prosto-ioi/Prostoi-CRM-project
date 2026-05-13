"""CRM domain models: ``Category``, ``Tag``, ``Client``, ``Product``,
``Deal``, ``Task``, and the generic ``Comment``.

Design choices:
    - Statuses are declared as ``TextChoices`` (no string literal hard-coding
      anywhere — ``Deal.Status.NEW``, ``Task.Status.PENDING`` etc).
    - Frequently filtered/ordered columns have ``db_index=True``.
"""
from __future__ import annotations

from typing import Any

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    """Product category with multilingual names (EN/RU/KK)."""

    name_en = models.CharField("name (EN)", max_length=100)
    name_ru = models.CharField("name (RU)", max_length=100, blank=True, default="")
    name_kk = models.CharField("name (KK)", max_length=100, blank=True, default="")
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = "category"
        verbose_name_plural = "categories"
        ordering = ["name_en"]

    def __str__(self) -> str:
        return self.name_en

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Auto-derive ``slug`` from ``name_en`` when one is not supplied."""
        if not self.slug:
            self.slug = slugify(self.name_en)
        super().save(*args, **kwargs)

    def get_name(self, lang: str = "en") -> str:
        """Return the localised name, falling back to ``name_en``.

        Bug fix: previously called ``getattr(self.name_en, ...)`` — i.e. it ran
        ``getattr`` on a *string*, which would either crash or always fall
        through. We now look up the attribute on ``self``.
        """
        return getattr(self, f"name_{lang}", "") or self.name_en


class Tag(models.Model):
    """Simple keyword tag, attachable to products."""

    name = models.CharField("name", max_length=50, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = "tag"
        verbose_name_plural = "tags"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Auto-derive ``slug`` from ``name`` when one is not supplied."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Client(models.Model):
    """External CRM client — the people we sell to."""

    first_name = models.CharField("first name", max_length=50)
    last_name = models.CharField("last name", max_length=50)
    email = models.EmailField("email", unique=True)
    phone = models.CharField("phone", max_length=20, blank=True, default="")
    address = models.CharField("address", max_length=100, blank=True, default="")
    created_at = models.DateTimeField("created at", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("updated at", auto_now=True)

    class Meta:
        verbose_name = "client"
        verbose_name_plural = "clients"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.email})"


class Product(models.Model):
    """A sellable product or service."""

    name = models.CharField("name", max_length=200)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="products",
        verbose_name="category",
    )
    tags = models.ManyToManyField(
        Tag, blank=True, related_name="products", verbose_name="tags",
    )
    price = models.DecimalField(
        "price", max_digits=10, decimal_places=2, db_index=True,
    )
    description = models.TextField("description", blank=True, default="")
    in_stock = models.BooleanField("in stock", default=True, db_index=True)
    created_at = models.DateTimeField("created at", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("updated at", auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_products",
        verbose_name="created by",
    )

    class Meta:
        verbose_name = "product"
        verbose_name_plural = "products"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Auto-derive ``slug`` from ``name`` when one is not supplied."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Deal(models.Model):
    """A sales opportunity tied to a ``Client`` (and optionally a ``Product``)."""

    class Status(models.TextChoices):
        """Lifecycle status of a deal."""

        NEW = "new", "New"
        IN_PROGRESS = "in_progress", "In progress"
        CLOSED_WON = "closed_won", "Closed (won)"
        CLOSED_LOST = "closed_lost", "Closed (lost)"

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="deals",
        verbose_name="client",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deals",
        verbose_name="product",
    )
    title = models.CharField("title", max_length=200)
    amount = models.DecimalField(
        "amount", max_digits=10, decimal_places=2, db_index=True,
    )
    status = models.CharField(
        "status",
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    created_at = models.DateTimeField("created at", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("updated at", auto_now=True)
    closed_at = models.DateTimeField("closed at", blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_deals",
        verbose_name="created by",
    )

    class Meta:
        verbose_name = "deal"
        verbose_name_plural = "deals"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} — {self.client}"


class Task(models.Model):
    """Actionable task, optionally linked to a ``Client`` and/or ``Deal``."""

    class Status(models.TextChoices):
        """Lifecycle status of a task."""

        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"

    title = models.CharField("title", max_length=200)
    description = models.TextField("description", blank=True, default="")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="assigned to",
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="tasks",
        verbose_name="client",
    )
    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="tasks",
        verbose_name="deal",
    )
    status = models.CharField(
        "status",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    due_date = models.DateTimeField("due date", blank=True, null=True, db_index=True)
    created_at = models.DateTimeField("created at", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("updated at", auto_now=True)

    # Reverse generic accessor: ``task.comments.all()``.
    comments = GenericRelation("Comment", related_query_name="task")

    class Meta:
        verbose_name = "task"
        verbose_name_plural = "tasks"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class Comment(models.Model):
    """Generic comment — attachable to a ``Deal`` or ``Task`` via GFK."""

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="author",
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name="content type",
    )
    object_id = models.PositiveIntegerField("object id")
    content_object = GenericForeignKey("content_type", "object_id")
    body = models.TextField("body")
    created_at = models.DateTimeField("created at", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "comment"
        verbose_name_plural = "comments"
        ordering = ["-created_at"]
        # Composite index — every list query filters on these two columns.
        indexes = [models.Index(fields=["content_type", "object_id"])]

    def __str__(self) -> str:
        # Use ``object_id`` directly; ``content_object`` may be ``None`` if the
        # target row was deleted, and dereferencing ``.id`` would crash.
        return f"comment by {self.author} on {self.content_type.model}#{self.object_id}"