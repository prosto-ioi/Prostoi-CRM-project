"""Per-request localisation overlay driven by user preferences.

Combines two responsibilities into a single middleware because both live on
the user profile and resolve from the same source of truth:

* **Language** — what locale to translate ``gettext_lazy`` strings into.
* **Timezone** — what local time to render aware datetimes in.

Resolution order
    1. Authenticated user → ``user.language`` / ``user.timezone``. The user
       is resolved by trying, in order, (a) ``request.user`` (already set by
       Django's :class:`AuthenticationMiddleware` for session-auth flows)
       and (b) the JWT in ``Authorization: Bearer …``. Step (b) exists
       because DRF's :class:`JWTAuthentication` normally runs only inside
       :meth:`APIView.initial`, i.e. *after* the whole middleware chain —
       so without manual decoding here we would see ``AnonymousUser`` for
       every JWT request and never honour the user preference.
    2. Anonymous request → ``Accept-Language`` header (RFC 7231), parsed by
       Django's built-in :func:`django.utils.translation.get_language_from_request`.
    3. Falls back to ``settings.LANGUAGE_CODE`` / ``settings.TIME_ZONE``.

Why a single middleware rather than two
    They are activated and deactivated together. Two separate middlewares
    would need duplicate ordering rules in ``MIDDLEWARE`` and would both have
    to run after ``AuthenticationMiddleware``. Folding them into one keeps
    the ``MIDDLEWARE`` list shorter and the lifecycle obvious.

Placement
    Must run AFTER ``AuthenticationMiddleware`` (we read ``request.user``).
    See ``settings/base.py`` for the exact order.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils import timezone, translation

logger = logging.getLogger(__name__)


class UserPreferencesMiddleware:
    """Activate per-user ``language`` + ``timezone`` for the duration of a request.

    Always deactivates both at the end of the request, even on exceptions, so
    one request's preferences never bleed into another worker thread's
    request.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        # Standard new-style Django middleware signature. ``get_response`` is
        # the next callable in the chain (could be another middleware or the
        # view itself).
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = self._get_request_user(request)
        language = self._resolve_language(request, user)
        tz_name = self._resolve_timezone(user)

        # Activate both for the duration of this request.
        translation.activate(language)
        request.LANGUAGE_CODE = language  # type: ignore[attr-defined]
        tz_activated = self._activate_timezone(tz_name)

        try:
            return self.get_response(request)
        finally:
            # CRITICAL: deactivate in ``finally`` — Django's thread-local
            # state would otherwise leak into the next request this worker
            # serves, giving e.g. a Kazakh response to a user who asked for
            # English.
            translation.deactivate()
            if tz_activated:
                timezone.deactivate()

    # ─── user resolution ───────────────────────────────────────────────────
    @staticmethod
    def _get_request_user(request: HttpRequest) -> Any | None:
        """Return the authenticated user for this request, or ``None``.

        Tries session auth first (free — already done by Django), then JWT.
        JWT requires manually invoking SimpleJWT's authenticator because DRF
        only runs it inside :meth:`APIView.initial`, *after* all middleware.

        Test note
            DRF's :func:`force_authenticate` bypasses both code paths — it
            injects the user inside ``initial()`` only. Tests that need to
            exercise the middleware must therefore issue real JWT tokens via
            ``POST /api/auth/token/`` and pass them in ``Authorization``,
            not rely on ``force_authenticate``.
        """
        # 1. Session auth (set by ``AuthenticationMiddleware``).
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            return user

        # 2. JWT auth — manual decode of the Authorization header.
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return None
        try:
            # Imported lazily so the middleware module stays cheap to load
            # in management commands and tests that don't touch JWT.
            from rest_framework_simplejwt.authentication import JWTAuthentication

            jwt_auth = JWTAuthentication()
            result = jwt_auth.authenticate(request)  # type: ignore[arg-type]
        except Exception:
            # Any decoding/expiration error → treat as anonymous. The actual
            # auth attempt that DRF runs later in the view will surface the
            # error to the client (401 + a descriptive message). We don't
            # want to duplicate that here.
            return None

        if result is None:
            return None
        # ``authenticate`` returns ``(user, validated_token)`` on success.
        return result[0]

    # ─── resolvers ─────────────────────────────────────────────────────────
    def _resolve_language(self, request: HttpRequest, user: Any | None) -> str:
        """Pick the language code for this request.

        User preference wins over the request header; the header wins over
        the project default.
        """
        if user is not None and user.is_authenticated:
            user_lang: str | None = getattr(user, "language", None)
            if user_lang and self._is_supported(user_lang):
                return user_lang

        # Anonymous or no preference saved: parse ``Accept-Language``.
        # Django returns ``settings.LANGUAGE_CODE`` when the header is
        # missing or unparseable, so this also covers the final fallback.
        return translation.get_language_from_request(request, check_path=False)

    def _resolve_timezone(self, user: Any | None) -> str:
        """Pick the IANA timezone name for this request.

        We do not honour any client header here — there is no standard one —
        so anonymous users always see ``settings.TIME_ZONE``.
        """
        if user is not None and user.is_authenticated:
            user_tz: str | None = getattr(user, "timezone", None)
            if user_tz:
                return user_tz
        return settings.TIME_ZONE

    # ─── helpers ───────────────────────────────────────────────────────────
    @staticmethod
    def _is_supported(language_code: str) -> bool:
        """``True`` if ``language_code`` is in ``settings.LANGUAGES``."""
        supported = {code for code, _name in settings.LANGUAGES}
        return language_code in supported

    @staticmethod
    def _activate_timezone(tz_name: str) -> bool:
        """Activate the timezone if valid; return whether activation happened.

        We swallow invalid names rather than raising — a user with a typo'd
        ``timezone`` field should still get served, just in UTC. Logged at
        WARNING for visibility.
        """
        try:
            timezone.activate(ZoneInfo(tz_name))
        except ZoneInfoNotFoundError:
            logger.warning("Unknown user timezone %r — falling back to default.", tz_name)
            return False
        return True
