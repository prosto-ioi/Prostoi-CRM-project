"""Root URL configuration.

Pulls together three layers:

* Django admin at ``/admin/``.
* Per-app API mounts under ``/api/auth/`` and ``/api/crm/``.
* OpenAPI / Swagger / ReDoc views under ``/api/{schema,docs,redoc}/``.
"""

from __future__ import annotations

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Admin site.
    path("admin/", admin.site.urls),
    # Application APIs.
    path("api/auth/", include("users.urls")),
    path("api/crm/", include("crm.urls")),
    # Documentation (OpenAPI schema + interactive viewers).
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
