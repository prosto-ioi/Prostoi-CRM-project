"""User model and manager for the CRM system.

Custom user that uses ``email`` as the unique identifier (no usernames),
plus per-user UI preferences (``language``, ``timezone``).
"""
from __future__ import annotations

from typing import Any

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models


class UserManager(BaseUserManager["User"]):
    """Custom manager: creates users by email instead of username.

    Parameterised with ``[User]`` so static analysers know that ``self.model``
    is ``type[User]`` and queryset results are ``User`` instances.
    """

    def create_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        """Create and persist a regular user.

        Args:
            email: Unique email address. Required.
            first_name: First name. Required.
            last_name: Last name. Required.
            password: Raw password. If ``None``, the user is unusable until reset.
            **extra_fields: Extra ``User`` fields (``is_staff``, ``language``, etc.).

        Returns:
            The newly created and persisted ``User``.

        Raises:
            ValueError: When any required field is empty.
        """
        if not email:
            raise ValueError("Email is required.")
        if not first_name:
            raise ValueError("First name is required.")
        if not last_name:
            raise ValueError("Last name is required.")

        email = self.normalize_email(email)
        user: User = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        first_name: str,
        last_name: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> User:
        """Create and persist a superuser (always ``is_staff`` and ``is_superuser``)."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, first_name, last_name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user keyed by ``email``.

    Notes:
        - The redundant ``EmailValidator`` was removed: ``EmailField`` already
          validates the address format on its own.
        - ``date_joined`` uses ``auto_now_add=True`` — the timestamp is set once
          at row creation and can never be silently overwritten thereafter.
    """

    class Language(models.TextChoices):
        """Supported interface languages."""

        EN = "en", "English"
        RU = "ru", "Russian"
        KK = "kk", "Kazakh"

    email = models.EmailField("email address", unique=True)
    first_name = models.CharField("first name", max_length=50)
    last_name = models.CharField("last name", max_length=50)

    is_active = models.BooleanField("active", default=True)
    is_staff = models.BooleanField("staff status", default=False)
    # auto_now_add — set at INSERT, then immutable. Replaces the mutable default.
    date_joined = models.DateTimeField("date joined", auto_now_add=True)

    avatar = models.ImageField("avatar", upload_to="avatars/", null=True, blank=True)

    language = models.CharField(
        "language",
        max_length=2,
        choices=Language.choices,
        default=Language.EN,
    )
    timezone = models.CharField("timezone", max_length=50, default="UTC")

    # Explicit annotation lets Pylance type ``User.objects`` as ``UserManager``
    # rather than the default unbound manager.
    objects: UserManager = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        app_label = "users"
        verbose_name = "user"
        verbose_name_plural = "users"
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return f"{self.get_full_name()} ({self.email})"

    def get_full_name(self) -> str:
        """Return ``"first last"`` (stripped)."""
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self) -> str:
        """Return the user's first name."""
        return self.first_name