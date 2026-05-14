"""Integration tests for the CRM REST API.

Covers all seven viewsets (Category, Tag, Client, Product, Deal, Task, Comment)
under three lenses:

* **Happy path** — basic CRUD returns the right status code and shape.
* **Auth** — anonymous requests are rejected with ``401``.
* **Permissions / business rules** — non-owners get ``403``, staff-only endpoints
  reject non-staff with ``403``, validation errors return ``400``, etc.

Implementation choices worth flagging:

* ``setUpTestData`` (class-level) is used for read-mostly fixtures (users,
  reference rows). It runs once per class inside a transaction — orders of
  magnitude faster than ``setUp`` and still safely rolled back between tests.
* All URLs go through :func:`reverse_list` / :func:`reverse_detail` — no
  hard-coded paths.
* All status codes go through :class:`rest_framework.status` — no magic numbers.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, ClassVar

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rest_framework import status
from rest_framework.response import Response

from crm.models import Category, Client, Comment, Deal, Product, Tag, Task

from .conftest import (
    BASENAME_CATEGORY,
    BASENAME_CLIENT,
    BASENAME_COMMENT,
    BASENAME_DEAL,
    BASENAME_PRODUCT,
    BASENAME_TAG,
    BASENAME_TASK,
    TestAPIClient,
    authenticate,
    make_api_client,
    make_user,
    reverse_detail,
    reverse_list,
)

User = get_user_model()

# Reusable test payloads — kept module-level so they stay together and are
# easy to find. Each test that mutates one should ``.copy()`` first.
_CATEGORY_PAYLOAD: dict[str, str] = {
    "name_en": "Software",
    "name_ru": "Программы",
    "name_kk": "Бағдарламалар",
}
_TAG_PAYLOAD: dict[str, str] = {"name": "urgent"}
_CLIENT_PAYLOAD: dict[str, str] = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone": "+77001234567",
    "address": "Almaty, KZ",
}


# ════════════════════════════════════════════════════════════════════════════
#  Base test case
# ════════════════════════════════════════════════════════════════════════════
class _CrmAPITestCase(TestCase):
    """Base for all CRM viewset tests.

    Provides a pre-authenticated ``self.client`` (as a regular user) and a
    pre-built ``self.user`` / ``self.staff`` / ``self.other_user`` trio so
    subclasses do not have to repeat the auth boilerplate.
    """

    # ``setUpTestData`` runs once per class — much cheaper than ``setUp``.
    user: ClassVar[Any]
    other_user: ClassVar[Any]
    staff: ClassVar[Any]

    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = make_user(email="owner@example.com")
        cls.other_user = make_user(email="intruder@example.com")
        cls.staff = make_user(email="staff@example.com", is_staff=True)

    def setUp(self) -> None:
        # Per-test client — force_authenticate state must not leak across tests.
        self.api: TestAPIClient = make_api_client()
        authenticate(self.api, self.user)

    # ─── tiny helpers used across the suite ────────────────────────────────
    def as_user(self, user: Any) -> TestAPIClient:
        """Return a fresh client authenticated as ``user``."""
        client = make_api_client()
        authenticate(client, user)
        return client

    def as_anonymous(self) -> TestAPIClient:
        """Return a fresh client with no credentials."""
        return make_api_client()

    @staticmethod
    def assert_status(response: Response, expected: int) -> None:
        """Assert response status with a useful message including the body."""
        assert response.status_code == expected, (
            f"Expected {expected}, got {response.status_code}. "
            f"Body: {response.data!r}"
        )

    @staticmethod
    def extract_results(response: Response) -> list[dict[str, Any]]:
        """Return the list of rows from a list-route response.

        Works for both paginated (``{"results": [...]}``) and unpaginated
        responses so individual tests do not have to care which mode the
        viewset is configured in.
        """
        # Paginated responses always carry a ``results`` key; plain list
        # responses are already a list of dicts.
        if isinstance(response.data, dict) and "results" in response.data:
            return response.data["results"]
        return response.data  # type: ignore[return-value]


# ════════════════════════════════════════════════════════════════════════════
#  Category
# ════════════════════════════════════════════════════════════════════════════
class CategoryAPITests(_CrmAPITestCase):
    """Categories are public-read, staff-write."""

    LIST_URL: ClassVar[str]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.LIST_URL = reverse_list(BASENAME_CATEGORY)

    # ── auth ──────────────────────────────────────────────────────────────
    def test_list_requires_authentication(self) -> None:
        response = self.as_anonymous().get(self.LIST_URL)
        self.assert_status(response, status.HTTP_401_UNAUTHORIZED)

    # ── permissions ───────────────────────────────────────────────────────
    def test_non_staff_cannot_create(self) -> None:
        """Regular users can read categories but not write them."""
        response = self.api.post(self.LIST_URL, _CATEGORY_PAYLOAD)
        self.assert_status(response, status.HTTP_403_FORBIDDEN)

    def test_staff_can_create(self) -> None:
        response = self.as_user(self.staff).post(self.LIST_URL, _CATEGORY_PAYLOAD)
        self.assert_status(response, status.HTTP_201_CREATED)
        # Slug is auto-derived from name_en; not user-controllable.
        self.assertEqual(response.data["slug"], "software")
        self.assertEqual(response.data["name_en"], "Software")

    # ── CRUD by staff ─────────────────────────────────────────────────────
    def test_staff_full_crud(self) -> None:
        client = self.as_user(self.staff)

        # CREATE
        created = client.post(self.LIST_URL, _CATEGORY_PAYLOAD)
        self.assert_status(created, status.HTTP_201_CREATED)
        slug = created.data["slug"]
        detail_url = reverse_detail(BASENAME_CATEGORY, slug)

        # READ (retrieve)
        retrieved = client.get(detail_url)
        self.assert_status(retrieved, status.HTTP_200_OK)

        # UPDATE (PUT)
        replaced = client.put(detail_url, {**_CATEGORY_PAYLOAD, "name_en": "Apps"})
        self.assert_status(replaced, status.HTTP_200_OK)
        self.assertEqual(replaced.data["name_en"], "Apps")

        # PATCH
        patched = client.patch(detail_url, {"name_ru": "ПО"})
        self.assert_status(patched, status.HTTP_200_OK)
        self.assertEqual(patched.data["name_ru"], "ПО")

        # DESTROY
        destroyed = client.delete(detail_url)
        self.assert_status(destroyed, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(slug=slug).exists())


# ════════════════════════════════════════════════════════════════════════════
#  Tag
# ════════════════════════════════════════════════════════════════════════════
class TagAPITests(_CrmAPITestCase):
    """Tags are public-read, staff-write — same contract as categories."""

    LIST_URL: ClassVar[str]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.LIST_URL = reverse_list(BASENAME_TAG)

    def test_list_requires_authentication(self) -> None:
        response = self.as_anonymous().get(self.LIST_URL)
        self.assert_status(response, status.HTTP_401_UNAUTHORIZED)

    def test_non_staff_cannot_create(self) -> None:
        response = self.api.post(self.LIST_URL, _TAG_PAYLOAD)
        self.assert_status(response, status.HTTP_403_FORBIDDEN)

    def test_staff_can_create(self) -> None:
        response = self.as_user(self.staff).post(self.LIST_URL, _TAG_PAYLOAD)
        self.assert_status(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["slug"], "urgent")

    def test_duplicate_name_rejected(self) -> None:
        staff = self.as_user(self.staff)
        staff.post(self.LIST_URL, _TAG_PAYLOAD)
        duplicate = staff.post(self.LIST_URL, _TAG_PAYLOAD)
        self.assert_status(duplicate, status.HTTP_400_BAD_REQUEST)


# ════════════════════════════════════════════════════════════════════════════
#  Client
# ════════════════════════════════════════════════════════════════════════════
class ClientAPITests(_CrmAPITestCase):
    """Clients can be managed by any authenticated user (no per-row ownership)."""

    LIST_URL: ClassVar[str]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.LIST_URL = reverse_list(BASENAME_CLIENT)

    def test_list_requires_authentication(self) -> None:
        response = self.as_anonymous().get(self.LIST_URL)
        self.assert_status(response, status.HTTP_401_UNAUTHORIZED)

    def test_create_then_retrieve(self) -> None:
        created = self.api.post(self.LIST_URL, _CLIENT_PAYLOAD)
        self.assert_status(created, status.HTTP_201_CREATED)
        self.assertEqual(created.data["email"], _CLIENT_PAYLOAD["email"])

        detail = self.api.get(reverse_detail(BASENAME_CLIENT, created.data["id"]))
        self.assert_status(detail, status.HTTP_200_OK)

    def test_duplicate_email_rejected(self) -> None:
        self.api.post(self.LIST_URL, _CLIENT_PAYLOAD)
        duplicate = self.api.post(self.LIST_URL, _CLIENT_PAYLOAD)
        self.assert_status(duplicate, status.HTTP_400_BAD_REQUEST)

    def test_any_authenticated_user_can_delete(self) -> None:
        """No per-row ownership on Client — other authenticated users may delete."""
        created = self.api.post(self.LIST_URL, _CLIENT_PAYLOAD)
        deleted = self.as_user(self.other_user).delete(
            reverse_detail(BASENAME_CLIENT, created.data["id"]),
        )
        self.assert_status(deleted, status.HTTP_204_NO_CONTENT)


# ════════════════════════════════════════════════════════════════════════════
#  Product
# ════════════════════════════════════════════════════════════════════════════
class ProductAPITests(_CrmAPITestCase):
    """Products: anyone authenticated creates; only owner (or staff) edits/deletes."""

    LIST_URL: ClassVar[str]
    category: ClassVar[Category]
    tag: ClassVar[Tag]

    # Shared price kept out of every test body.
    DEFAULT_PRICE: ClassVar[Decimal] = Decimal("99.99")

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.LIST_URL = reverse_list(BASENAME_PRODUCT)
        cls.category = Category.objects.create(name_en="Software", slug="software")
        cls.tag = Tag.objects.create(name="urgent", slug="urgent")

    def _build_payload(self, **overrides: Any) -> dict[str, Any]:
        """Return a fresh product payload with sensible defaults."""
        payload: dict[str, Any] = {
            "name": "CRM License",
            "category": self.category.id,
            "tags": [self.tag.id],
            "price": str(self.DEFAULT_PRICE),
            "description": "Annual CRM Pro license",
        }
        payload.update(overrides)
        return payload

    # ── auth ──────────────────────────────────────────────────────────────
    def test_list_requires_authentication(self) -> None:
        response = self.as_anonymous().get(self.LIST_URL)
        self.assert_status(response, status.HTTP_401_UNAUTHORIZED)

    # ── happy path ────────────────────────────────────────────────────────
    def test_create_sets_created_by_to_request_user(self) -> None:
        """``perform_create`` must stamp ``created_by`` from request — not body."""
        # Deliberately try to spoof created_by in the body — should be ignored.
        payload = self._build_payload(created_by=self.other_user.id)
        response = self.api.post(self.LIST_URL, payload, format="json")
        self.assert_status(response, status.HTTP_201_CREATED)
        product = Product.objects.get(slug=response.data["slug"])
        self.assertEqual(product.created_by, self.user)

    def test_create_includes_nested_category_and_tags(self) -> None:
        response = self.api.post(self.LIST_URL, self._build_payload(), format="json")
        self.assert_status(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["category_detail"]["name_en"], "Software")
        self.assertEqual(len(response.data["tags_detail"]), 1)
        self.assertEqual(response.data["tags_detail"][0]["name"], "urgent")

    # ── permissions ───────────────────────────────────────────────────────
    def test_non_owner_cannot_update(self) -> None:
        owner_response = self.api.post(self.LIST_URL, self._build_payload(), format="json")
        slug = owner_response.data["slug"]

        intruder = self.as_user(self.other_user)
        response = intruder.patch(reverse_detail(BASENAME_PRODUCT, slug), {"in_stock": False})
        self.assert_status(response, status.HTTP_403_FORBIDDEN)

    def test_owner_can_update(self) -> None:
        owner_response = self.api.post(self.LIST_URL, self._build_payload(), format="json")
        slug = owner_response.data["slug"]

        response = self.api.patch(reverse_detail(BASENAME_PRODUCT, slug), {"in_stock": False})
        self.assert_status(response, status.HTTP_200_OK)
        self.assertFalse(response.data["in_stock"])

    def test_staff_can_update_any(self) -> None:
        """Staff override applies — they can edit rows they do not own."""
        owner_response = self.api.post(self.LIST_URL, self._build_payload(), format="json")
        slug = owner_response.data["slug"]

        response = self.as_user(self.staff).patch(
            reverse_detail(BASENAME_PRODUCT, slug), {"in_stock": False},
        )
        self.assert_status(response, status.HTTP_200_OK)

    # ── filters ───────────────────────────────────────────────────────────
    def test_filter_by_category_slug(self) -> None:
        other_category = Category.objects.create(name_en="Hardware", slug="hardware")
        Product.objects.create(name="A", slug="a", category=self.category, price=self.DEFAULT_PRICE)
        Product.objects.create(name="B", slug="b", category=other_category, price=self.DEFAULT_PRICE)

        response = self.api.get(self.LIST_URL, {"category": self.category.slug})
        self.assert_status(response, status.HTTP_200_OK)
        results = self.extract_results(response)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["slug"], "a")

    def test_filter_by_price_range(self) -> None:
        Product.objects.create(name="Cheap", slug="cheap", price=Decimal("10.00"))
        Product.objects.create(name="Mid", slug="mid", price=Decimal("100.00"))
        Product.objects.create(name="Pricy", slug="pricy", price=Decimal("1000.00"))

        response = self.api.get(self.LIST_URL, {"min_price": "50", "max_price": "500"})
        self.assert_status(response, status.HTTP_200_OK)
        results = self.extract_results(response)
        slugs = {row["slug"] for row in results}
        self.assertEqual(slugs, {"mid"})


# ════════════════════════════════════════════════════════════════════════════
#  Deal
# ════════════════════════════════════════════════════════════════════════════
class DealAPITests(_CrmAPITestCase):
    """Deal create is open; per-row mutations are owner-only."""

    LIST_URL: ClassVar[str]
    crm_client: ClassVar[Client]
    DEFAULT_AMOUNT: ClassVar[Decimal] = Decimal("250.00")

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.LIST_URL = reverse_list(BASENAME_DEAL)
        cls.crm_client = Client.objects.create(
            first_name="Jane",
            last_name="Roe",
            email="jane.roe@example.com",
        )

    def _build_payload(self, **overrides: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "client": self.crm_client.id,
            "title": "Initial sale",
            "amount": str(self.DEFAULT_AMOUNT),
            "status": Deal.Status.NEW,
        }
        payload.update(overrides)
        return payload

    # ── auth ──────────────────────────────────────────────────────────────
    def test_list_requires_authentication(self) -> None:
        response = self.as_anonymous().get(self.LIST_URL)
        self.assert_status(response, status.HTTP_401_UNAUTHORIZED)

    # ── happy path ────────────────────────────────────────────────────────
    def test_create_uses_textchoices(self) -> None:
        """Status must be one of ``Deal.Status`` values — anything else → 400."""
        response = self.api.post(self.LIST_URL, self._build_payload(), format="json")
        self.assert_status(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Deal.Status.NEW)

    def test_invalid_status_rejected(self) -> None:
        response = self.api.post(
            self.LIST_URL,
            self._build_payload(status="not_a_real_status"),
            format="json",
        )
        self.assert_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)

    def test_create_stamps_created_by(self) -> None:
        # Try to spoof created_by — must be overwritten with request.user.
        payload = self._build_payload(created_by=self.other_user.id)
        response = self.api.post(self.LIST_URL, payload, format="json")
        self.assert_status(response, status.HTTP_201_CREATED)
        deal = Deal.objects.get(pk=response.data["id"])
        self.assertEqual(deal.created_by, self.user)

    # ── permissions ───────────────────────────────────────────────────────
    def test_non_owner_cannot_update(self) -> None:
        owner_response = self.api.post(self.LIST_URL, self._build_payload(), format="json")
        deal_id = owner_response.data["id"]

        response = self.as_user(self.other_user).patch(
            reverse_detail(BASENAME_DEAL, deal_id),
            {"status": Deal.Status.CLOSED_WON},
        )
        self.assert_status(response, status.HTTP_403_FORBIDDEN)

    def test_owner_can_close_deal(self) -> None:
        owner_response = self.api.post(self.LIST_URL, self._build_payload(), format="json")
        deal_id = owner_response.data["id"]

        response = self.api.patch(
            reverse_detail(BASENAME_DEAL, deal_id),
            {"status": Deal.Status.CLOSED_WON},
        )
        self.assert_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Deal.Status.CLOSED_WON)

    # ── filters ───────────────────────────────────────────────────────────
    def test_filter_by_status(self) -> None:
        Deal.objects.create(client=self.crm_client, title="A",
                            amount=Decimal("10.00"), status=Deal.Status.NEW)
        Deal.objects.create(client=self.crm_client, title="B",
                            amount=Decimal("20.00"), status=Deal.Status.CLOSED_WON)

        response = self.api.get(self.LIST_URL, {"status": Deal.Status.CLOSED_WON})
        self.assert_status(response, status.HTTP_200_OK)
        results = self.extract_results(response)
        titles = {row["title"] for row in results}
        self.assertEqual(titles, {"B"})


# ════════════════════════════════════════════════════════════════════════════
#  Task
# ════════════════════════════════════════════════════════════════════════════
class TaskAPITests(_CrmAPITestCase):
    """Tasks — only the assignee (or staff) can mutate."""

    LIST_URL: ClassVar[str]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.LIST_URL = reverse_list(BASENAME_TASK)

    def _build_payload(self, **overrides: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "title": "Follow up with client",
            "description": "Schedule the demo call",
            "assigned_to": self.user.id,
            "status": Task.Status.PENDING,
        }
        payload.update(overrides)
        return payload

    # ── auth ──────────────────────────────────────────────────────────────
    def test_list_requires_authentication(self) -> None:
        response = self.as_anonymous().get(self.LIST_URL)
        self.assert_status(response, status.HTTP_401_UNAUTHORIZED)

    # ── happy path ────────────────────────────────────────────────────────
    def test_create_with_textchoice_status(self) -> None:
        response = self.api.post(self.LIST_URL, self._build_payload(), format="json")
        self.assert_status(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Task.Status.PENDING)

    def test_invalid_status_rejected(self) -> None:
        response = self.api.post(
            self.LIST_URL,
            self._build_payload(status="not_real"),
            format="json",
        )
        self.assert_status(response, status.HTTP_400_BAD_REQUEST)

    # ── permissions ───────────────────────────────────────────────────────
    def test_assignee_can_complete_task(self) -> None:
        task = Task.objects.create(title="T", assigned_to=self.user)
        response = self.api.patch(
            reverse_detail(BASENAME_TASK, task.id),
            {"status": Task.Status.COMPLETED},
        )
        self.assert_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Task.Status.COMPLETED)

    def test_non_assignee_cannot_update(self) -> None:
        task = Task.objects.create(title="T", assigned_to=self.user)
        response = self.as_user(self.other_user).patch(
            reverse_detail(BASENAME_TASK, task.id),
            {"status": Task.Status.COMPLETED},
        )
        self.assert_status(response, status.HTTP_403_FORBIDDEN)

    # ── filters ───────────────────────────────────────────────────────────
    def test_filter_by_assigned_to(self) -> None:
        Task.objects.create(title="Mine", assigned_to=self.user)
        Task.objects.create(title="Theirs", assigned_to=self.other_user)

        response = self.api.get(self.LIST_URL, {"assigned_to": self.user.id})
        self.assert_status(response, status.HTTP_200_OK)
        results = self.extract_results(response)
        titles = {row["title"] for row in results}
        self.assertEqual(titles, {"Mine"})


# ════════════════════════════════════════════════════════════════════════════
#  Comment (GenericForeignKey)
# ════════════════════════════════════════════════════════════════════════════
class CommentAPITests(_CrmAPITestCase):
    """Comments attach to Task or Deal via GFK; only the author can delete."""

    LIST_URL: ClassVar[str]
    crm_client: ClassVar[Client]
    deal: ClassVar[Deal]
    task: ClassVar[Task]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.LIST_URL = reverse_list(BASENAME_COMMENT)
        cls.crm_client = Client.objects.create(
            first_name="Anna", last_name="Smith", email="anna@example.com",
        )
        cls.deal = Deal.objects.create(
            client=cls.crm_client, title="Demo", amount=Decimal("50.00"),
        )
        cls.task = Task.objects.create(title="Demo task", assigned_to=cls.user)

    # ── auth ──────────────────────────────────────────────────────────────
    def test_list_requires_authentication(self) -> None:
        response = self.as_anonymous().get(self.LIST_URL)
        self.assert_status(response, status.HTTP_401_UNAUTHORIZED)

    # ── happy path ────────────────────────────────────────────────────────
    def test_create_comment_on_deal(self) -> None:
        response = self.api.post(self.LIST_URL, {
            "content_type": "deal",
            "object_id": self.deal.id,
            "body": "Sent the proposal",
        })
        self.assert_status(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["body"], "Sent the proposal")
        # Author must be stamped server-side, never from request body.
        comment = Comment.objects.get(pk=response.data["id"])
        self.assertEqual(comment.author, self.user)

    def test_create_comment_on_task(self) -> None:
        response = self.api.post(self.LIST_URL, {
            "content_type": "task",
            "object_id": self.task.id,
            "body": "Working on it",
        })
        self.assert_status(response, status.HTTP_201_CREATED)

    # ── validation ────────────────────────────────────────────────────────
    def test_unknown_content_type_rejected(self) -> None:
        """Only Task / Deal models accept comments — anything else → 400."""
        response = self.api.post(self.LIST_URL, {
            "content_type": "category",  # Not in the allowed queryset.
            "object_id": 1,
            "body": "should fail",
        })
        self.assert_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("content_type", response.data)

    # ── filters ───────────────────────────────────────────────────────────
    def test_filter_by_target_deal(self) -> None:
        ct_deal = ContentType.objects.get_for_model(Deal)
        ct_task = ContentType.objects.get_for_model(Task)
        Comment.objects.create(
            author=self.user, content_type=ct_deal,
            object_id=self.deal.id, body="deal comment",
        )
        Comment.objects.create(
            author=self.user, content_type=ct_task,
            object_id=self.task.id, body="task comment",
        )

        response = self.api.get(self.LIST_URL, {"target": "deal"})
        self.assert_status(response, status.HTTP_200_OK)
        results = self.extract_results(response)
        bodies = {row["body"] for row in results}
        self.assertEqual(bodies, {"deal comment"})

    def test_unknown_target_returns_empty(self) -> None:
        """Unknown ``?target=`` value must yield an empty list, not 500."""
        Comment.objects.create(
            author=self.user,
            content_type=ContentType.objects.get_for_model(Deal),
            object_id=self.deal.id,
            body="x",
        )
        response = self.api.get(self.LIST_URL, {"target": "nonexistent"})
        self.assert_status(response, status.HTTP_200_OK)
        results = self.extract_results(response)
        self.assertEqual(results, [])

    # ── permissions ───────────────────────────────────────────────────────
    def test_non_author_cannot_delete(self) -> None:
        comment = Comment.objects.create(
            author=self.user,
            content_type=ContentType.objects.get_for_model(Deal),
            object_id=self.deal.id,
            body="mine",
        )
        response = self.as_user(self.other_user).delete(
            reverse_detail(BASENAME_COMMENT, comment.id),
        )
        self.assert_status(response, status.HTTP_403_FORBIDDEN)

    def test_author_can_delete(self) -> None:
        comment = Comment.objects.create(
            author=self.user,
            content_type=ContentType.objects.get_for_model(Deal),
            object_id=self.deal.id,
            body="mine",
        )
        response = self.api.delete(reverse_detail(BASENAME_COMMENT, comment.id))
        self.assert_status(response, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Comment.objects.filter(pk=comment.id).exists())

    def test_staff_can_delete_any_comment(self) -> None:
        comment = Comment.objects.create(
            author=self.user,
            content_type=ContentType.objects.get_for_model(Deal),
            object_id=self.deal.id,
            body="someone else's",
        )
        response = self.as_user(self.staff).delete(
            reverse_detail(BASENAME_COMMENT, comment.id),
        )
        self.assert_status(response, status.HTTP_204_NO_CONTENT)


# ════════════════════════════════════════════════════════════════════════════
#  Nested action: /tasks/<pk>/comments/
# ════════════════════════════════════════════════════════════════════════════
class TaskCommentsActionTests(_CrmAPITestCase):
    """The custom ``@action`` on ``TaskViewSet`` for nested comment listing/creation."""

    task: ClassVar[Task]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.task = Task.objects.create(title="T", assigned_to=cls.user)

    def _url(self) -> str:
        """Reverse the nested router URL for ``task-comments``."""
        from django.urls import reverse
        return reverse("task-comments", kwargs={"pk": self.task.id})

    def test_post_creates_comment_attached_to_task(self) -> None:
        response = self.api.post(self._url(), {"body": "first note"})
        self.assert_status(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["body"], "first note")

        # The created comment should be findable via GFK on the task.
        ct_task = ContentType.objects.get_for_model(Task)
        self.assertTrue(
            Comment.objects.filter(
                content_type=ct_task,
                object_id=self.task.id,
                body="first note",
            ).exists(),
        )

    def test_get_returns_only_this_tasks_comments(self) -> None:
        ct_task = ContentType.objects.get_for_model(Task)
        Comment.objects.create(
            author=self.user, content_type=ct_task,
            object_id=self.task.id, body="hers",
        )
        # An unrelated task with its own comment — must not appear in the list.
        other = Task.objects.create(title="Other", assigned_to=self.user)
        Comment.objects.create(
            author=self.user, content_type=ct_task,
            object_id=other.id, body="theirs",
        )

        response = self.api.get(self._url())
        self.assert_status(response, status.HTTP_200_OK)
        bodies = {row["body"] for row in response.data}
        self.assertEqual(bodies, {"hers"})
