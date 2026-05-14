"""URL configuration for the users app.

All routes are mounted under ``/api/auth/`` by the root URLconf.

URL name reference (for ``reverse(...)``):

* ``register``           — POST, create a new account.
* ``token_obtain_pair``  — POST, exchange credentials for a JWT pair.
* ``token_refresh``      — POST, exchange a refresh token for a new access.
* ``token_verify``       — POST, check that a token is still valid.
"""
from __future__ import annotations

from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView

from . import views

urlpatterns = [
    path('register/', views.RegistrationView.as_view(), name='register'),

    path('token/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', views.CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
