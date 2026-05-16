from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import (Category, Client, Deal, Product, Tag, Task)

pytestmark = pytest.mark.django_db

PASSWORD = "StrongPass123!"


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(django_user_model: Any) -> Any:
    return django_user_model.objects.create_user(
        email="rubric-user@example.com",
        first_name="Rubric",
        last_name="User",
        password=PASSWORD,
    )


@pytest.fixture
def staff(django_user_model: Any) -> Any:
    return django_user_model.objects.create_user(
        email="rubric-staff@example.com",
        first_name="Rubric",
        last_name="Staff",
        password=PASSWORD,
        is_staff=True,
    )


@pytest.fixture
def auth_client(api_client: APIClient, user: Any) -> APIClient:
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def staff_client(api_client: APIClient, staff: Any) -> APIClient:
    api_client.force_authenticate(user=staff)
    return api_client


@pytest.fixture
def crm_client() -> Client:
    return Client.objects.create(
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
    )


@pytest.fixture
def category() -> Category:
    return Category.objects.create(name_en="Software", slug="software")


@pytest.fixture
def tag() -> Tag:
    return Tag.objects.create(name="priority", slug="priority")


@pytest.fixture
def product(category: Category, tag: Tag, user: Any) -> Product:
    item = Product.objects.create(
        name="CRM License",
        slug="crm-license",
        category=category,
        price=Decimal("99.00"),
        created_by=user,
    )
    item.tags.add(tag)
    return item


@pytest.fixture
def deal(crm_client: Client, product: Product, user: Any) -> Deal:
    return Deal.objects.create(
        client=crm_client,
        product=product,
        title="Pilot sale",
        amount=Decimal("250.00"),
        status=Deal.Status.NEW,
        created_by=user,
    )


@pytest.fixture
def task(user: Any, crm_client: Client, deal: Deal) -> Task:
    return Task.objects.create(
        title="Follow up",
        assigned_to=user,
        client=crm_client,
        deal=deal,
    )


# Auth: 1 successful + 2 failing
def test_auth_success_registers_user(api_client: APIClient) -> None:
    response = api_client.post(
        reverse("register"),
        {
            "email": "new-rubric-user@example.com",
            "first_name": "New",
            "last_name": "User",
            "password": PASSWORD,
            "password2": PASSWORD,
            "language": "en",
            "timezone": "Asia/Almaty",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED


def test_auth_fails_missing_email(api_client: APIClient) -> None:
    response = api_client.post(
        reverse("register"),
        {
            "first_name": "No",
            "last_name": "Email",
            "password": PASSWORD,
            "password2": PASSWORD,
        },
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_auth_fails_wrong_password(api_client: APIClient, user: Any) -> None:
    response = api_client.post(
        reverse("token_obtain_pair"),
        {"email": user.email, "password": "WrongPass123!"},
        format="json",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# Categories: 1 successful + 2 failing
def test_categories_success_staff_creates(staff_client: APIClient) -> None:
    response = staff_client.post(
        reverse("category-list"),
        {"name_en": "Consulting", "name_ru": "Консалтинг", "name_kk": "Консалтинг"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED


def test_categories_fail_anonymous_list(api_client: APIClient) -> None:
    response = api_client.get(reverse("category-list"))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_categories_fail_regular_user_create(auth_client: APIClient) -> None:
    response = auth_client.post(reverse("category-list"), {"name_en": "Nope"}, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


# Tags: 1 successful + 2 failing
def test_tags_success_staff_creates(staff_client: APIClient) -> None:
    response = staff_client.post(reverse("tag-list"), {"name": "vip"}, format="json")
    assert response.status_code == status.HTTP_201_CREATED


def test_tags_fail_anonymous_list(api_client: APIClient) -> None:
    response = api_client.get(reverse("tag-list"))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_tags_fail_regular_user_create(auth_client: APIClient) -> None:
    response = auth_client.post(reverse("tag-list"), {"name": "blocked"}, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


# Clients: 1 successful + 2 failing
def test_clients_success_creates(auth_client: APIClient) -> None:
    response = auth_client.post(
        reverse("client-list"),
        {
            "first_name": "Grace",
            "last_name": "Hopper",
            "email": "grace@example.com",
            "phone": "+77001234567",
            "address": "Almaty",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED


def test_clients_fail_anonymous_list(api_client: APIClient) -> None:
    response = api_client.get(reverse("client-list"))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_clients_fail_invalid_email(auth_client: APIClient) -> None:
    response = auth_client.post(
        reverse("client-list"),
        {"first_name": "Bad", "last_name": "Email", "email": "not-an-email"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# Products: 1 successful + 2 failing
def test_products_success_creates(
    auth_client: APIClient,
    category: Category,
    tag: Tag,
) -> None:
    response = auth_client.post(
        reverse("product-list"),
        {
            "name": "Analytics Module",
            "category": category.pk,
            "tags": [tag.pk],
            "price": "120.50",
            "description": "Reporting add-on",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED


def test_products_fail_anonymous_list(api_client: APIClient) -> None:
    response = api_client.get(reverse("product-list"))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_products_fail_invalid_price(auth_client: APIClient, category: Category) -> None:
    response = auth_client.post(
        reverse("product-list"),
        {"name": "Broken", "category": category.pk, "price": "not-a-price"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# Deals: 1 successful + 2 failing
def test_deals_success_retrieves(auth_client: APIClient, deal: Deal) -> None:
    response = auth_client.get(reverse("deal-detail", kwargs={"pk": deal.pk}))
    assert response.status_code == status.HTTP_200_OK


def test_deals_fail_anonymous_list(api_client: APIClient) -> None:
    response = api_client.get(reverse("deal-list"))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_deals_fail_invalid_status(auth_client: APIClient, crm_client: Client) -> None:
    response = auth_client.post(
        reverse("deal-list"),
        {
            "client": crm_client.pk,
            "title": "Bad status",
            "amount": "10.00",
            "status": "invalid",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# Tasks: 1 successful + 2 failing
def test_tasks_success_creates(auth_client: APIClient, user: Any) -> None:
    response = auth_client.post(
        reverse("task-list"),
        {"title": "Call client", "assigned_to": user.pk, "status": Task.Status.PENDING},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED


def test_tasks_fail_anonymous_list(api_client: APIClient) -> None:
    response = api_client.get(reverse("task-list"))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_tasks_fail_invalid_status(auth_client: APIClient, user: Any) -> None:
    response = auth_client.post(
        reverse("task-list"),
        {"title": "Bad status", "assigned_to": user.pk, "status": "invalid"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# Comments: 1 successful + 2 failing
def test_comments_success_creates(auth_client: APIClient, deal: Deal) -> None:
    response = auth_client.post(
        reverse("comment-list"),
        {"content_type": "deal", "object_id": deal.pk, "body": "Looks promising"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED


def test_comments_fail_anonymous_list(api_client: APIClient) -> None:
    response = api_client.get(reverse("comment-list"))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_comments_fail_invalid_content_type(auth_client: APIClient) -> None:
    response = auth_client.post(
        reverse("comment-list"),
        {"content_type": "category", "object_id": 1, "body": "Nope"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# Stats: 1 successful + 2 failing
def test_stats_success_returns_dashboard_payload(
    api_client: APIClient,
    crm_client: Client,
    deal: Deal,
    task: Task,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_rates() -> dict[str, Any]:
        return {"base": "USD", "rates": {"KZT": 500, "RUB": 90, "EUR": 0.9}}

    async def fake_time() -> dict[str, Any]:
        return {"dateTime": "2026-05-16T12:00:00", "timeZone": "Asia/Almaty"}

    monkeypatch.setattr("crm.views._fetch_exchange_rates", fake_rates)
    monkeypatch.setattr("crm.views._fetch_almaty_time", fake_time)

    response = api_client.get(reverse("dashboard-stats"))
    assert response.status_code == status.HTTP_200_OK
    payload = json.loads(response.content)
    assert payload["database"]["clients_count"] == 1
    assert payload["database"]["deals_count"] == 1
    assert payload["database"]["tasks_count"] == 1


def test_stats_fail_post_not_allowed(api_client: APIClient) -> None:
    response = api_client.post(reverse("dashboard-stats"), {}, format="json")
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_stats_fail_put_not_allowed(api_client: APIClient) -> None:
    response = api_client.put(reverse("dashboard-stats"), {}, format="json")
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED