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
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    """Product category with multilingual names (EN/RU/KK)."""

    name_en = models.CharField(_("name (EN)"), max_length=100)
    name_ru = models.CharField(_("name (RU)"), max_length=100, blank=True, default="")
    name_kk = models.CharField(_("name (KK)"), max_length=100, blank=True, default="")
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = _("category")
        verbose_name_plural = _("categories")
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

    name = models.CharField(_("name"), max_length=50, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = _("tag")
        verbose_name_plural = _("tags")
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

    first_name = models.CharField(_("first name"), max_length=50)
    last_name = models.CharField(_("last name"), max_length=50)
    email = models.EmailField(_("email"), unique=True)
    phone = models.CharField(_("phone"), max_length=20, blank=True, default="")
    address = models.CharField(_("address"), max_length=100, blank=True, default="")
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("client")
        verbose_name_plural = _("clients")
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.email})"


class Product(models.Model):
    """A sellable product or service."""

    name = models.CharField(_("name"), max_length=200)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="products",
        verbose_name=_("category"),
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name="products",
        verbose_name=_("tags"),
    )
    price = models.DecimalField(
        _("price"),
        max_digits=10,
        decimal_places=2,
        db_index=True,
    )
    description = models.TextField(_("description"), blank=True, default="")
    in_stock = models.BooleanField(_("in stock"), default=True, db_index=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_products",
        verbose_name=_("created by"),
    )

    class Meta:
        verbose_name = _("product")
        verbose_name_plural = _("products")
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

        NEW = "new", _("New")
        IN_PROGRESS = "in_progress", _("In progress")
        CLOSED_WON = "closed_won", _("Closed (won)")
        CLOSED_LOST = "closed_lost", _("Closed (lost)")

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="deals",
        verbose_name=_("client"),
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deals",
        verbose_name=_("product"),
    )
    title = models.CharField(_("title"), max_length=200)
    amount = models.DecimalField(
        _("amount"),
        max_digits=10,
        decimal_places=2,
        db_index=True,
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)
    closed_at = models.DateTimeField(_("closed at"), blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_deals",
        verbose_name=_("created by"),
    )

    class Meta:
        verbose_name = _("deal")
        verbose_name_plural = _("deals")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} — {self.client}"


class Task(models.Model):
    """Actionable task, optionally linked to a ``Client`` and/or ``Deal``."""

    class Status(models.TextChoices):
        """Lifecycle status of a task."""

        PENDING = "pending", _("Pending")
        IN_PROGRESS = "in_progress", _("In progress")
        COMPLETED = "completed", _("Completed")

    title = models.CharField(_("title"), max_length=200)
    description = models.TextField(_("description"), blank=True, default="")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name=_("assigned to"),
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="tasks",
        verbose_name=_("client"),
    )
    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="tasks",
        verbose_name=_("deal"),
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    due_date = models.DateTimeField(_("due date"), blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    # Reverse generic accessor: ``task.comments.all()``.
    comments = GenericRelation("Comment", related_query_name="task")

    class Meta:
        verbose_name = _("task")
        verbose_name_plural = _("tasks")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class Comment(models.Model):
    """Generic comment — attachable to a ``Deal`` or ``Task`` via GFK."""

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name=_("author"),
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("content type"),
    )
    object_id = models.PositiveIntegerField(_("object id"))
    content_object = GenericForeignKey("content_type", "object_id")
    body = models.TextField(_("body"))
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("comment")
        verbose_name_plural = _("comments")
        ordering = ["-created_at"]
        # Composite index — every list query filters on these two columns.
        indexes = [models.Index(fields=["content_type", "object_id"])]

    def __str__(self) -> str:
        # Use ``object_id`` directly; ``content_object`` may be ``None`` if the
        # target row was deleted, and dereferencing ``.id`` would crash.
        return f"comment by {self.author} on {self.content_type.model}#{self.object_id}"
