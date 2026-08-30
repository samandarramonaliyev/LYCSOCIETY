from __future__ import annotations

from unittest.mock import patch

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
from apps.telegram_integration.models import ClubTelegramGroup, TelegramGroupStatus


class TelegramGroupApiSecurityTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.lyceum = Lyceum.objects.create(name="Telegram API Lyceum", code="tg-api")
        self.owner = self.make_user(903_001, "Owner")
        self.member = self.make_user(903_002, "Member")
        self.other_owner = self.make_user(903_003, "Other Owner")
        self.club = self.make_club(self.owner, "Linked Club")
        self.other_club = self.make_club(self.other_owner, "Other Club")
        ClubMembership.objects.create(
            club=self.club,
            user=self.member,
            role=MembershipRole.MEMBER,
            status=MembershipStatus.ACTIVE,
        )
        ClubTelegramGroup.objects.create(
            club=self.club,
            telegram_chat_id=-1_009_030,
            telegram_chat_title="Private Group",
            status=TelegramGroupStatus.LINKED,
            bot_can_invite_members=True,
            linked_at=timezone.now(),
        )

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

    def test_only_owner_can_view_or_unlink_group_status(self) -> None:
        url = f"/api/v1/clubs/{self.club.pk}/telegram/"
        for user in (self.member, self.other_owner):
            self.client.force_login(user)
            self.assertEqual(self.client.get(url, secure=True).status_code, 404)
            self.assertEqual(self.client.delete(url, secure=True).status_code, 404)

        self.client.force_login(self.owner)
        response = self.client.get(url, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("telegram_chat_id", response.content.decode())
        self.assertNotIn(str(-1_009_030), response.content.decode())

    def test_link_and_invite_actions_reject_client_authority_fields(self) -> None:
        self.client.force_login(self.owner)
        link_response = self.client.post(
            f"/api/v1/clubs/{self.club.pk}/telegram/link/start/",
            {"telegram_chat_id": -999, "owner": str(self.other_owner.pk)},
            format="json",
            secure=True,
        )
        invite_response = self.client.post(
            f"/api/v1/clubs/{self.club.pk}/telegram/invite/",
            {"telegram_chat_id": -999},
            format="json",
            secure=True,
        )
        self.assertEqual(link_response.status_code, 400)
        self.assertEqual(invite_response.status_code, 400)

    @patch("apps.telegram_integration.views.TelegramBotClient")
    def test_active_member_invite_is_scoped_and_not_persisted(self, client_class) -> None:  # type: ignore[no-untyped-def]
        client_class.return_value.create_invite_link.return_value = {
            "invite_link": "https://t.me/+short-lived"
        }
        self.client.force_login(self.member)
        response = self.client.post(
            f"/api/v1/clubs/{self.club.pk}/telegram/invite/",
            {},
            format="json",
            secure=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["invite_link"], "https://t.me/+short-lived")
        self.assertFalse(
            any(
                field.name == "invite_link"
                for field in ClubTelegramGroup._meta.get_fields()
            )
        )

        self.client.force_login(self.other_owner)
        denied = self.client.post(
            f"/api/v1/clubs/{self.club.pk}/telegram/invite/",
            {},
            format="json",
            secure=True,
        )
        self.assertEqual(denied.status_code, 404)
