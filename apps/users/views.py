"""Authentication endpoints: registration, JWT obtain, JWT refresh."""

from __future__ import annotations

import logging
from typing import Any

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    CustomTokenObtainPairSerializer,
    UserReadSerializer,
    UserWriteSerializer,
)

logger = logging.getLogger(__name__)


class RegistrationView(APIView):
    """Register a new user and immediately issue a JWT token pair.

    Public endpoint — no authentication required.

    Responses:
        * ``201 Created`` — ``{access, refresh, user}`` for the new user.
        * ``400 Bad Request`` — validation error (duplicate email, weak
          password, mismatched confirmation, missing required field, ...).
    """

    permission_classes = (AllowAny,)
    # Class-level attr lets DRF Spectacular introspect the request shape.
    serializer_class = UserWriteSerializer

    @extend_schema(
        summary="Register a new user",
        description=(
            "Creates a new user and returns a JWT token pair plus the public "
            "user payload.\n\nNo authentication required.\n\n"
            "Fields: email, first_name, last_name, password, password2, "
            "language, timezone."
        ),
        tags=["Auth"],
        request=UserWriteSerializer,
        responses={
            status.HTTP_201_CREATED: UserReadSerializer,
            status.HTTP_400_BAD_REQUEST: None,
        },
        examples=[
            OpenApiExample(
                "Sample request",
                value={
                    "email": "user@example.com",
                    "first_name": "Alikhan",
                    "last_name": "Seitkali",
                    "password": "StrongPass123!",
                    "password2": "StrongPass123!",
                    "language": "en",
                    "timezone": "Asia/Almaty",
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        email: str = request.data.get("email", "")
        logger.info("Registration attempt: %s", email)

        # Validate + create explicitly — no reliance on generics magic.
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Issue tokens immediately so the client doesn't need a second hop.
        refresh = RefreshToken.for_user(user)
        logger.info("Registration successful: %s", email)

        payload: dict[str, Any] = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserReadSerializer(user, context={"request": request}).data,
        }
        return Response(payload, status=status.HTTP_201_CREATED)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Login — exchange (email, password) for a JWT token pair."""

    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Obtain JWT token pair (login)",
        description=(
            "Accepts email and password, returns access and refresh tokens. "
            "No authentication required."
        ),
        tags=["Auth"],
        responses={
            status.HTTP_200_OK: CustomTokenObtainPairSerializer,
            status.HTTP_400_BAD_REQUEST: None,
            status.HTTP_401_UNAUTHORIZED: None,
        },
        examples=[
            OpenApiExample(
                "Sample request",
                value={"email": "user@example.com", "password": "StrongPass123!"},
                request_only=True,
            ),
        ],
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        email: str = request.data.get("email", "")
        logger.info("Login attempt: %s", email)
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            logger.info("Login successful: %s", email)
        else:
            logger.warning(
                "Login failed: %s (status=%s)",
                email,
                response.status_code,
            )
        return response


class CustomTokenRefreshView(TokenRefreshView):
    """Exchange a valid refresh token for a fresh access token."""

    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Refresh access token",
        description="Accepts a refresh token, returns a new access token.",
        tags=["Auth"],
        responses={
            status.HTTP_200_OK: None,
            status.HTTP_400_BAD_REQUEST: None,
            status.HTTP_401_UNAUTHORIZED: None,
        },
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().post(request, *args, **kwargs)
