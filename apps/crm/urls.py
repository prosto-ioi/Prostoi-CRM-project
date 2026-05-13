"""URL configuration for the CRM app.

Uses a DRF :class:`~rest_framework.routers.DefaultRouter` to wire up the
seven CRUD viewsets. The router automatically generates list/detail/action
routes named ``<basename>-list``, ``<basename>-detail`` and
``<basename>-<action_name>`` (e.g. ``task-comments``).
"""
from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"categories", views.CategoryViewSet, basename="category")
router.register(r"tags", views.TagViewSet, basename="tag")
router.register(r"clients", views.ClientViewSet, basename="client")
router.register(r"products", views.ProductViewSet, basename="product")
router.register(r"deals", views.DealViewSet, basename="deal")
router.register(r"tasks", views.TaskViewSet, basename="task")
router.register(r"comments", views.CommentViewSet, basename="comment")

urlpatterns = [
    path("", include(router.urls)),
]
