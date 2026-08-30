from __future__ import annotations

from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
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
from apps.telegram_integration.models import ClubTelegramGroup
from apps.common.throttling import (
    JoinRequestThrottle,
    ReportSubmissionThrottle,
    TelegramInviteThrottle,
)


THROTTLED_REST_FRAMEWORK = {
    **settings.REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {
        **settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],
        "join_request": "1/hour",
        "report_submission": "1/hour",
        "telegram_invite": "1/hour",
    },
}


@override_settings(REST_FRAMEWORK=THROTTLED_REST_FRAMEWORK)
class SensitiveActionThrottleTests(TestCase):
    def setUp(self) -> None:
        cache.clear()
        self.client = APIClient()
        self.lyceum = Lyceum.objects.create(name="Throttle Lyceum", code="throttles")
        self.owner = self.make_user(889_001, "Owner")
        self.student = self.make_user(889_002, "Student")
        self.club = self.make_club(self.owner, "First Club")

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

    def make_club(self, owner: User, name: str) -> Club:
        club = Club.objects.create(
            lyceum=self.lyceum,
            owner=owner,
            name=name,
            short_description="Short",
            description="Description",
            category="OTHER",
            status=ClubStatus.ACTIVE,
        )
        ClubMembership.objects.create(
            club=club,
            user=owner,
            role=MembershipRole.OWNER,
            status=MembershipStatus.ACTIVE,
        )
        return club

    @patch.object(JoinRequestThrottle, "get_rate", return_value="1/hour")
    def test_join_request_submission_is_user_throttled(self, get_rate) -> None:  # type: ignore[no-untyped-def]
        other_owner = self.make_user(889_003, "Other Owner")
        other_club = self.make_club(other_owner, "Second Club")
        self.client.force_login(self.student)
        first = self.client.post(
            f"/api/v1/clubs/{self.club.pk}/join-requests/",
            {},
            format="json",
            secure=True,
        )
        second = self.client.post(
            f"/api/v1/clubs/{other_club.pk}/join-requests/",
            {},
            format="json",
            secure=True,
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 429)

    @patch.object(ReportSubmissionThrottle, "get_rate", return_value="1/hour")
    def test_report_submission_is_user_throttled(self, get_rate) -> None:  # type: ignore[no-untyped-def]
        self.client.force_login(self.student)
        payload = {
            "target_type": "CLUB",
            "target_id": str(self.club.pk),
            "reason": "SPAM",
        }
        first = self.client.post("/api/v1/reports/", payload, format="json", secure=True)
        second = self.client.post("/api/v1/reports/", payload, format="json", secure=True)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 429)

    @patch.object(TelegramInviteThrottle, "get_rate", return_value="1/hour")
    @patch("apps.telegram_integration.views.TelegramBotClient")
    def test_invite_generation_is_user_throttled(self, client_class, get_rate) -> None:  # type: ignore[no-untyped-def]
        ClubTelegramGroup.objects.create(
            club=self.club,
            telegram_chat_id=-1_008_890,
            bot_can_invite_members=True,
        )
        client_class.return_value.create_invite_link.return_value = {
            "invite_link": "https://t.me/+short"
        }
        self.client.force_login(self.owner)
        url = f"/api/v1/clubs/{self.club.pk}/telegram/invite/"
        first = self.client.post(url, {}, format="json", secure=True)
        second = self.client.post(url, {}, format="json", secure=True)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
