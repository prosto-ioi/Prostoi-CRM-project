"""Serializers for the users app: registration, JWT, profile read."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import Token

from .models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT obtain-pair serializer that embeds profile fields in token + response."""

    @classmethod
    def get_token(cls, user: User) -> Token:
        """Add custom claims (email, names, language) to the access JWT."""
        token = super().get_token(user)
        token["email"] = user.email
        token["first_name"] = user.first_name
        token["last_name"] = user.last_name
        token["language"] = user.language
        return token

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Return ``{access, refresh, user}`` instead of just tokens.

        We annotate the local ``data`` as ``dict[str, Any]`` explicitly:
        the parent class is typed (via DRF-SimpleJWT stubs) as returning
        ``dict[str, str]``, but we widen it on purpose so we can embed a nested
        ``user`` payload.
        """
        # Widen the parent's return type — we add a nested dict under "user".
        data: dict[str, Any] = super().validate(attrs)
        data["user"] = {
            "id": self.user.id,
            "email": self.user.email,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "language": self.user.language,
            "timezone": self.user.timezone,
        }
        return data


class UserReadSerializer(serializers.ModelSerializer):
    """Read-only representation of a user — no password, no permissions, no PII leaks."""

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "language",
            "timezone",
            "date_joined",
            "avatar",
        )
        read_only_fields = fields


class UserWriteSerializer(serializers.ModelSerializer):
    """Registration serializer.

    Accepts a ``password`` + ``password2`` pair (confirmed in :meth:`validate`)
    and creates the user via :meth:`User.objects.create_user`, which hashes the
    password properly. Echoes the safe :class:`UserReadSerializer` shape on
    response so the password is never written back.
    """

    password = serializers.CharField(  # type: ignore
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    password2 = serializers.CharField(  # type: ignore
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "password",
            "password2",
            "language",
            "timezone",
        )
        extra_kwargs = {
            "email": {"required": True},
            "first_name": {"required": True},
            "last_name": {"required": True},
        }

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Confirm both password fields match.

        Returning a structured error keyed on ``password2`` so the client
        UI can highlight the right field.
        """
        if attrs.get("password") != attrs.get("password2"):
            raise serializers.ValidationError(  # type: ignore
                {"password2": "Passwords do not match."},
            )
        return attrs

    def create(self, validated_data: dict[str, Any]) -> User:
        """Create the user explicitly via the manager (proper password hashing)."""
        # Strip confirmation field — never persisted.
        validated_data.pop("password2", None)
        # Pop the raw password so we can pass it positionally to ``create_user``.
        password: str = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)

    def to_representation(self, instance: User) -> dict[str, Any]:
        """Always return the safe read shape on response."""
        return UserReadSerializer(instance, context=self.context).data
