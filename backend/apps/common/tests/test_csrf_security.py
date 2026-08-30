from __future__ import annotations

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.clubs.models import (
    Club,
    ClubMembership,
    ClubStatus,
    MembershipRole,
    MembershipStatus,
)
from apps.identity.models import User
from apps.lyceums.models import Lyceum, StudentRecord


class SessionCsrfSecurityTests(TestCase):
    def setUp(self) -> None:
        self.lyceum = Lyceum.objects.create(name="CSRF Lyceum", code="csrf")
        self.owner = self.make_user(870_000_001, "Owner")
        self.student = self.make_user(870_000_002, "Student")
        self.club = Club.objects.create(
            lyceum=self.lyceum,
            owner=self.owner,
            name="CSRF Club",
            short_description="Short",
            description="Description",
            category="OTHER",
            status=ClubStatus.ACTIVE,
        )
        ClubMembership.objects.create(
            club=self.club,
            user=self.owner,
            role=MembershipRole.OWNER,
            status=MembershipStatus.ACTIVE,
        )
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.force_login(self.student)

    def make_user(self, telegram_id: int, first_name: str) -> User:
        user = User.objects.create_user(telegram_user_id=telegram_id)
        StudentRecord.objects.create(
            lyceum=self.lyceum,
            first_name=first_name,
            last_name="Student",
            group_name="10-A",
            verified_user=user,
            verified_at=timezone.now(),
        )
        return user

    def csrf_token(self) -> str:
        response = self.client.get("/api/v1/auth/csrf/", secure=True)
        self.assertEqual(response.status_code, 200)
        return response.json()["csrf_token"]

    def request_kwargs(self, token: str) -> dict[str, object]:
        return {
            "secure": True,
            "HTTP_REFERER": "https://testserver/",
            "HTTP_X_CSRFTOKEN": token,
        }

    def test_safe_get_does_not_require_csrf(self) -> None:
        self.assertEqual(self.client.get("/api/v1/profile/", secure=True).status_code, 200)

    def test_session_post_requires_csrf(self) -> None:
        url = f"/api/v1/clubs/{self.club.pk}/join-requests/"
        self.assertEqual(self.client.post(url, {}, format="json", secure=True).status_code, 403)
        self.assertEqual(
            self.client.post(
                url,
                {},
                format="json",
                **self.request_kwargs(self.csrf_token()),
            ).status_code,
            201,
        )

    def test_session_patch_requires_csrf(self) -> None:
        self.assertEqual(
            self.client.patch(
                "/api/v1/profile/",
                {"about": "blocked"},
                format="json",
                secure=True,
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(
                "/api/v1/profile/",
                {"about": "allowed"},
                format="json",
                **self.request_kwargs(self.csrf_token()),
            ).status_code,
            200,
        )

    def test_session_delete_requires_csrf(self) -> None:
        self.client.force_login(self.owner)
        url = f"/api/v1/clubs/{self.club.pk}/telegram/"
        self.assertEqual(self.client.delete(url, secure=True).status_code, 403)
        self.assertEqual(
            self.client.delete(url, **self.request_kwargs(self.csrf_token())).status_code,
            204,
        )
