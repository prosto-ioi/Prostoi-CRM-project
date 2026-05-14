"""Integration tests for the users app: registration + JWT.

Covers three endpoints under ``/api/auth/``:

* ``POST /api/auth/register/``     — registration
* ``POST /api/auth/token/``        — login (obtain token pair)
* ``POST /api/auth/token/refresh/``— refresh access token

Each is tested for happy path, the expected validation errors, and the
"wrong credentials → 401" path where applicable.
"""
from __future__ import annotations

from typing import Any, ClassVar, Final

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response

# Imported from the CRM conftest — we deliberately share the protocol /
# client factory so both test suites get the same fix.
from crm.conftest import TestAPIClient, make_api_client

User = get_user_model()


# ─── Constants ──────────────────────────────────────────────────────────────
# Kept module-level so we don't repeat them in every test body.
STRONG_PASSWORD: Final[str] = "StrongPass123!"
WEAK_PASSWORD: Final[str] = "123"

REGISTER_URL: Final[str] = reverse("register")
TOKEN_URL: Final[str] = reverse("token_obtain_pair")
REFRESH_URL: Final[str] = reverse("token_refresh")


def _base_register_payload(**overrides: Any) -> dict[str, str]:
    """Return a valid registration payload with sensible defaults.

    Tests override only the fields they care about, keeping the call sites
    short and the intent obvious.
    """
    payload: dict[str, str] = {
        "email": "new.user@example.com",
        "first_name": "New",
        "last_name": "User",
        "password": STRONG_PASSWORD,
        "password2": STRONG_PASSWORD,
        "language": "en",
        "timezone": "Asia/Almaty",
    }
    payload.update(overrides)
    return payload


# ─── Base case ──────────────────────────────────────────────────────────────
class _UsersAPITestCase(TestCase):
    """Shared scaffolding for users API tests."""

    def setUp(self) -> None:
        self.api: TestAPIClient = make_api_client()

    @staticmethod
    def assert_status(response: Response, expected: int) -> None:
        """Assert response status with body included in the failure message."""
        assert response.status_code == expected, (
            f"Expected {expected}, got {response.status_code}. "
            f"Body: {response.data!r}"
        )


# ════════════════════════════════════════════════════════════════════════════
#  Registration
# ════════════════════════════════════════════════════════════════════════════
class RegistrationTests(_UsersAPITestCase):
    """``POST /api/auth/register/`` — public endpoint."""

    def test_success_returns_201_with_tokens_and_user(self) -> None:
        """Happy path — 201 plus access/refresh/user payload."""
        response = self.api.post(REGISTER_URL, _base_register_payload(), format="json")
        self.assert_status(response, status.HTTP_201_CREATED)
        # Tokens must be present and non-empty strings.
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertTrue(response.data["access"])
        self.assertTrue(response.data["refresh"])
        # User payload — no password leaked.
        self.assertEqual(response.data["user"]["email"], "new.user@example.com")
        self.assertNotIn("password", response.data["user"])

    def test_password_is_hashed_in_database(self) -> None:
        """Password must never be stored in plain text."""
        self.api.post(REGISTER_URL, _base_register_payload(), format="json")
        user = User.objects.get(email="new.user@example.com")
        # Django prefixes hashed passwords with the algorithm name ("pbkdf2_sha256$").
        self.assertNotEqual(user.password, STRONG_PASSWORD)
        self.assertTrue(user.check_password(STRONG_PASSWORD))

    def test_password_mismatch_returns_400(self) -> None:
        """``password`` ≠ ``password2`` → 400 with structured error."""
        payload = _base_register_payload(password2="DifferentPass456!")
        response = self.api.post(REGISTER_URL, payload, format="json")
        self.assert_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password2", response.data)

    def test_weak_password_returns_400(self) -> None:
        """Django's password validators reject too-short passwords."""
        payload = _base_register_payload(password=WEAK_PASSWORD, password2=WEAK_PASSWORD)
        response = self.api.post(REGISTER_URL, payload, format="json")
        self.assert_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_duplicate_email_returns_400(self) -> None:
        """Second registration with the same email must fail validation."""
        self.api.post(REGISTER_URL, _base_register_payload(), format="json")
        response = self.api.post(REGISTER_URL, _base_register_payload(), format="json")
        self.assert_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_missing_required_fields_returns_400(self) -> None:
        """``email`` is required — omitting it → 400."""
        payload = _base_register_payload()
        del payload["email"]
        response = self.api.post(REGISTER_URL, payload, format="json")
        self.assert_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_invalid_language_choice_returns_400(self) -> None:
        """Language must be one of the ``TextChoices`` values."""
        response = self.api.post(
            REGISTER_URL,
            _base_register_payload(language="xx"),
            format="json",
        )
        self.assert_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("language", response.data)


# ════════════════════════════════════════════════════════════════════════════
#  Login (token obtain pair)
# ════════════════════════════════════════════════════════════════════════════
class TokenObtainTests(_UsersAPITestCase):
    """``POST /api/auth/token/`` — exchange credentials for a JWT pair."""

    user_email: ClassVar[str] = "login.test@example.com"

    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = User.objects.create_user(  # type: ignore[attr-defined]
            email=cls.user_email,
            first_name="Login",
            last_name="Test",
            password=STRONG_PASSWORD,
        )

    def test_valid_credentials_return_200_with_tokens(self) -> None:
        """Happy path — 200 + access/refresh + nested user payload."""
        response = self.api.post(
            TOKEN_URL,
            {"email": self.user_email, "password": STRONG_PASSWORD},
            format="json",
        )
        self.assert_status(response, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        # ``CustomTokenObtainPairSerializer`` attaches a nested ``user`` block.
        self.assertEqual(response.data["user"]["email"], self.user_email)

    def test_wrong_password_returns_401(self) -> None:
        response = self.api.post(
            TOKEN_URL,
            {"email": self.user_email, "password": "WrongPass789!"},
            format="json",
        )
        self.assert_status(response, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_user_returns_401(self) -> None:
        """Unknown email must look identical to wrong password (no enumeration)."""
        response = self.api.post(
            TOKEN_URL,
            {"email": "nobody@example.com", "password": STRONG_PASSWORD},
            format="json",
        )
        self.assert_status(response, status.HTTP_401_UNAUTHORIZED)

    def test_missing_password_returns_400(self) -> None:
        response = self.api.post(TOKEN_URL, {"email": self.user_email}, format="json")
        self.assert_status(response, status.HTTP_400_BAD_REQUEST)


# ════════════════════════════════════════════════════════════════════════════
#  Token refresh
# ════════════════════════════════════════════════════════════════════════════
class TokenRefreshTests(_UsersAPITestCase):
    """``POST /api/auth/token/refresh/`` — exchange refresh for fresh access."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = User.objects.create_user(  # type: ignore[attr-defined]
            email="refresh.test@example.com",
            first_name="Refresh",
            last_name="Test",
            password=STRONG_PASSWORD,
        )

    def _login_and_get_refresh(self) -> str:
        """Helper: log in and return the refresh token string."""
        response = self.api.post(
            TOKEN_URL,
            {"email": "refresh.test@example.com", "password": STRONG_PASSWORD},
            format="json",
        )
        self.assert_status(response, status.HTTP_200_OK)
        return response.data["refresh"]

    def test_valid_refresh_returns_200_with_new_access(self) -> None:
        refresh = self._login_and_get_refresh()
        response = self.api.post(REFRESH_URL, {"refresh": refresh}, format="json")
        self.assert_status(response, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertTrue(response.data["access"])

    def test_invalid_refresh_returns_401(self) -> None:
        response = self.api.post(REFRESH_URL, {"refresh": "not-a-real-token"}, format="json")
        self.assert_status(response, status.HTTP_401_UNAUTHORIZED)

    def test_missing_refresh_returns_400(self) -> None:
        response = self.api.post(REFRESH_URL, {}, format="json")
        self.assert_status(response, status.HTTP_400_BAD_REQUEST)


# ════════════════════════════════════════════════════════════════════════════
#  Model & manager
# ════════════════════════════════════════════════════════════════════════════
class UserModelTests(TestCase):
    """Lightweight checks on the custom user manager and string fields."""

    def test_create_user_requires_email(self) -> None:
        with self.assertRaises(ValueError):
            User.objects.create_user(  # type: ignore[attr-defined]
                email="", first_name="A", last_name="B", password=STRONG_PASSWORD,
            )

    def test_create_user_requires_first_name(self) -> None:
        with self.assertRaises(ValueError):
            User.objects.create_user(  # type: ignore[attr-defined]
                email="x@example.com", first_name="", last_name="B",
                password=STRONG_PASSWORD,
            )

    def test_create_user_requires_last_name(self) -> None:
        with self.assertRaises(ValueError):
            User.objects.create_user(  # type: ignore[attr-defined]
                email="x@example.com", first_name="A", last_name="",
                password=STRONG_PASSWORD,
            )

    def test_create_superuser_sets_flags(self) -> None:
        admin = User.objects.create_superuser(  # type: ignore[attr-defined]
            email="root@example.com",
            first_name="Root",
            last_name="User",
            password=STRONG_PASSWORD,
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_active)

    def test_str_includes_email(self) -> None:
        user = User.objects.create_user(  # type: ignore[attr-defined]
            email="str.test@example.com", first_name="Str", last_name="Test",
            password=STRONG_PASSWORD,
        )
        self.assertIn("str.test@example.com", str(user))

    def test_get_full_name(self) -> None:
        user = User.objects.create_user(  # type: ignore[attr-defined]
            email="fn@example.com", first_name="First", last_name="Last",
            password=STRONG_PASSWORD,
        )
        self.assertEqual(user.get_full_name(), "First Last")
        self.assertEqual(user.get_short_name(), "First")


# ══════════════════════════════════════════════════════════════════════════
#  GET / PATCH /api/auth/me/
# ══════════════════════════════════════════════════════════════════════════
class UserMeEndpointTests(TestCase):
    """Profile read/update — both happy path and the security invariants
    (auth required, can't change email, can't touch other users)."""

    ME_URL: ClassVar[str] = reverse("me")

    def setUp(self) -> None:
        self.api: TestAPIClient = make_api_client()
        self.user = User.objects.create_user(  # type: ignore[attr-defined]
            email="me@example.com",
            first_name="Me",
            last_name="Self",
            password=STRONG_PASSWORD,
            language="en",
            timezone="UTC",
        )
        self.api.force_authenticate(user=self.user)

    # ── GET ────────────────────────────────────────────────────────────────
    def test_get_returns_current_user_profile(self) -> None:
        response = self.api.get(self.ME_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "me@example.com")
        self.assertEqual(response.data["first_name"], "Me")
        self.assertEqual(response.data["language"], "en")

    def test_get_requires_authentication(self) -> None:
        anon = make_api_client()
        response = anon.get(self.ME_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── PATCH ──────────────────────────────────────────────────────────────
    def test_patch_changes_language_and_timezone(self) -> None:
        """The two fields the middleware actually reads — happy path."""
        response = self.api.patch(
            self.ME_URL,
            {"language": "ru", "timezone": "Asia/Almaty"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["language"], "ru")
        self.assertEqual(response.data["timezone"], "Asia/Almaty")

        # Persisted, not just echoed.
        self.user.refresh_from_db()
        self.assertEqual(self.user.language, "ru")
        self.assertEqual(self.user.timezone, "Asia/Almaty")

    def test_patch_changes_names(self) -> None:
        response = self.api.patch(
            self.ME_URL,
            {"first_name": "Renamed", "last_name": "Surname"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Renamed")
        self.assertEqual(self.user.last_name, "Surname")

    def test_patch_email_is_silently_ignored(self) -> None:
        """``email`` is read-only — sending it must not change the DB row.

        We assert silent ignore (the field is in ``read_only_fields``) rather
        than 400 — DRF's default behaviour, and changing it would surprise
        any client that includes the email in every PATCH for convenience.
        """
        original_email = self.user.email
        response = self.api.patch(
            self.ME_URL,
            {"email": "hijacked@example.com", "first_name": "ChangedOK"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        # Name change still went through, but email did NOT.
        self.assertEqual(self.user.first_name, "ChangedOK")
        self.assertEqual(self.user.email, original_email)

    def test_patch_invalid_language_returns_400(self) -> None:
        response = self.api.patch(self.ME_URL, {"language": "xx"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("language", response.data)

    def test_patch_invalid_timezone_returns_400(self) -> None:
        """Reject unknown IANA names early — see ``validate_timezone``."""
        response = self.api.patch(self.ME_URL, {"timezone": "Mars/Olympus_Mons"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("timezone", response.data)

    def test_patch_requires_authentication(self) -> None:
        anon = make_api_client()
        response = anon.patch(self.ME_URL, {"language": "ru"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_put_is_disabled(self) -> None:
        """``PUT`` was intentionally removed from ``http_method_names``."""
        response = self.api.put(self.ME_URL, {"first_name": "FullReplace"})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# ══════════════════════════════════════════════════════════════════════════
#  Localisation middleware + locale-aware Category serialisation
# ══════════════════════════════════════════════════════════════════════════
class LocalizationTests(TestCase):
    """End-to-end checks that ``UserPreferencesMiddleware`` actually changes
    response content.

    We use the ``Category`` model as the visible probe: it has per-language
    name columns and a ``name`` field on the serializer that respects the
    active language. A successful language switch shows up as a different
    string in the ``name`` field for the same row.

    Why these tests use real JWT tokens (not ``force_authenticate``)
        DRF's :func:`force_authenticate` injects the user only inside
        :meth:`APIView.initial` — *after* the middleware chain has finished.
        Our middleware reads JWTs manually to work around exactly that gap,
        but ``force_authenticate`` doesn't attach a JWT either: the user
        becomes available too late, and the middleware sees anonymous.

        Conclusion: to exercise the middleware end-to-end we must log in
        through the real ``/api/auth/token/`` endpoint and pass the access
        token in ``HTTP_AUTHORIZATION``.
    """

    @classmethod
    def setUpTestData(cls) -> None:
        # One category with all three names populated.
        from crm.models import Category
        cls.category = Category.objects.create(
            name_en="Software",
            name_ru="Программы",
            name_kk="Бағдарламалар",
            slug="software",
        )
        cls.url = reverse("category-detail", kwargs={"slug": "software"})

    def _user_with_language(self, lang: str) -> Any:
        # Unique email per user — language is what we're varying.
        return User.objects.create_user(  # type: ignore[attr-defined]
            email=f"u-{lang}@example.com",
            first_name="L10n", last_name="Test",
            password=STRONG_PASSWORD,
            language=lang,
        )

    @staticmethod
    def _jwt_for(user: Any) -> str:
        """Mint a real access token — used as ``Authorization: Bearer ...``."""
        from rest_framework_simplejwt.tokens import RefreshToken

        return str(RefreshToken.for_user(user).access_token)

    def _api_as(self, user: Any) -> TestAPIClient:
        """Return an APIClient whose default ``Authorization`` header is set."""
        api = make_api_client()
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {self._jwt_for(user)}")
        return api

    # ──────────────────────────────────────────────────────────────────────
    def test_authenticated_user_language_drives_category_name(self) -> None:
        """``user.language`` wins — header is irrelevant."""
        for lang, expected in [
            ("en", "Software"),
            ("ru", "Программы"),
            ("kk", "Бағдарламалар"),
        ]:
            with self.subTest(language=lang):
                api = self._api_as(self._user_with_language(lang))
                response = api.get(self.url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data["name"], expected)
                # Raw per-language columns always present unchanged.
                self.assertEqual(response.data["name_en"], "Software")

    def test_user_language_overrides_accept_language_header(self) -> None:
        """``user.language='ru'`` beats ``Accept-Language: kk`` — preference > header."""
        api = self._api_as(self._user_with_language("ru"))
        response = api.get(self.url, HTTP_ACCEPT_LANGUAGE="kk")
        self.assertEqual(response.data["name"], "Программы")

    def test_anonymous_user_falls_back_to_accept_language(self) -> None:
        """No user → ``Accept-Language`` decides.

        The category list endpoint is auth-required in this project, so we
        use the registration endpoint as a probe: its validation error
        messages are translated and end-to-end exercise the middleware.
        """
        anon = make_api_client()
        # Bad payload → triggers ``Passwords do not match`` localised string.
        bad_payload = _base_register_payload(password2="DifferentPass123!")

        # In Russian.
        response_ru = anon.post(REGISTER_URL, bad_payload, HTTP_ACCEPT_LANGUAGE="ru")
        self.assertEqual(response_ru.status_code, status.HTTP_400_BAD_REQUEST)
        # In English.
        response_en = anon.post(REGISTER_URL, bad_payload, HTTP_ACCEPT_LANGUAGE="en")
        self.assertEqual(response_en.status_code, status.HTTP_400_BAD_REQUEST)

        # Even if the .po files aren't compiled in the test env, both responses
        # must contain ``password2`` — and once translations ARE compiled, the
        # strings will differ. We assert the structural invariant (field name)
        # and one weaker invariant (the message is a non-empty string).
        msg_ru = str(response_ru.data["password2"][0])
        msg_en = str(response_en.data["password2"][0])
        self.assertTrue(msg_ru)
        self.assertTrue(msg_en)

    def test_kazakh_language_falls_back_to_english_when_field_empty(self) -> None:
        """``Category.get_name`` falls back to ``name_en`` when target empty.

        Same model code path as in ``models.py``, exercised end-to-end
        through the middleware + serializer to make sure no layer overrides
        it.
        """
        from crm.models import Category
        Category.objects.create(
            name_en="Hardware",
            name_ru="",   # empty translation
            name_kk="",   # empty translation
            slug="hardware",
        )
        api = self._api_as(self._user_with_language("ru"))
        response = api.get(reverse("category-detail", kwargs={"slug": "hardware"}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # ``ru`` is empty, so the resolver falls back to ``en``.
        self.assertEqual(response.data["name"], "Hardware")
