from __future__ import annotations

import json
from datetime import timedelta
from unittest.mock import Mock, patch

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
from apps.identity.models import AccountStatus, User
from apps.lyceums.models import Lyceum, StudentRecord
from apps.telegram_integration.exceptions import TelegramAPIError
from apps.telegram_integration.models import (
    ClubTelegramGroup,
    TelegramGroupStatus,
    TelegramLinkChallenge,
    TelegramWebhookUpdate,
)
from apps.telegram_integration.services import start_link


WEBHOOK_URL = "/api/v1/telegram/webhook/"
WEBHOOK_SECRET = "test-webhook-secret"


@override_settings(TELEGRAM_WEBHOOK_ENABLED=True, TELEGRAM_WEBHOOK_SECRET=WEBHOOK_SECRET)
class TelegramWebhookTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.lyceum = Lyceum.objects.create(name="Webhook Lyceum", code="webhook")
        self.owner = self.make_verified_user(940_001, "Owner")
        self.member = self.make_verified_user(940_002, "Member")
        self.club = self.make_club(self.owner, "Webhook Club")
        ClubMembership.objects.create(
            club=self.club,
            user=self.member,
            role=MembershipRole.MEMBER,
            status=MembershipStatus.ACTIVE,
        )

    def make_verified_user(self, telegram_id: int, first_name: str) -> User:
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

    def post(self, update: dict[object, object], *, secret: str = WEBHOOK_SECRET):
        return self.client.post(
            WEBHOOK_URL,
            data=json.dumps(update),
            content_type="application/json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=secret,
        )

    def connect_update(
        self, *, update_id: int, token: str, telegram_user_id: int | None = None
    ) -> dict[object, object]:
        return {
            "update_id": update_id,
            "message": {
                "text": f"/connect {token}",
                "from": {"id": telegram_user_id or self.owner.telegram_user_id},
                "chat": {"id": -100_940_001, "type": "supergroup"},
            },
        }

    def join_update(self, *, update_id: int, telegram_user_id: int, chat_id: int = -100_940_001):
        return {
            "update_id": update_id,
            "chat_join_request": {
                "from": {"id": telegram_user_id},
                "chat": {"id": chat_id, "type": "supergroup"},
            },
        }

    def bot_client(self) -> Mock:
        client = Mock()
        client.get_chat.return_value = {
            "id": -100_940_001,
            "type": "supergroup",
            "title": "Webhook Group",
        }
        client.get_me.return_value = {"id": 777_001}
        client.get_chat_member.return_value = {
            "status": "administrator",
            "can_invite_users": True,
            "user": {"id": 777_001},
        }
        return client

    def test_post_only_and_missing_or_incorrect_secret_are_rejected(self) -> None:
        self.assertEqual(self.client.get(WEBHOOK_URL).status_code, 405)
        missing = self.client.post(WEBHOOK_URL, data="{}", content_type="application/json")
        incorrect = self.post({"update_id": 1}, secret="wrong-secret")
        self.assertEqual(missing.status_code, 403)
        self.assertEqual(incorrect.status_code, 403)
        self.assertNotIn(WEBHOOK_SECRET, missing.content.decode())
        self.assertNotIn(WEBHOOK_SECRET, incorrect.content.decode())

    def test_correct_secret_accepts_unsupported_update_without_provider_call(self) -> None:
        with patch("apps.telegram_integration.views.TelegramBotClient") as client_class:
            response = self.post({"update_id": 2, "my_chat_member": {"ignored": True}})
        self.assertEqual(response.status_code, 204)
        client_class.assert_called_once()
        self.assertTrue(TelegramWebhookUpdate.objects.filter(update_id=2, processed_at__isnull=False).exists())

    def test_malformed_json_and_update_are_safe(self) -> None:
        malformed_json = self.client.post(
            WEBHOOK_URL,
            data="{not-json",
            content_type="application/json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=WEBHOOK_SECRET,
        )
        malformed_update = self.post({"message": {}})
        self.assertEqual(malformed_json.status_code, 400)
        self.assertEqual(malformed_update.status_code, 400)
        self.assertNotIn(WEBHOOK_SECRET, malformed_json.content.decode())

    def test_provider_failure_returns_generic_retry_response_without_secret_logs(self) -> None:
        token = start_link(club_id=self.club.pk, user=self.owner)
        client = self.bot_client()
        client.get_chat.side_effect = TelegramAPIError()
        with patch("apps.telegram_integration.views.TelegramBotClient", return_value=client), self.assertLogs(
            "apps.telegram_integration.views", level="WARNING"
        ) as logs:
            response = self.post(self.connect_update(update_id=3, token=token))
        self.assertEqual(response.status_code, 503)
        self.assertFalse(ClubTelegramGroup.objects.exists())
        self.assertFalse(TelegramWebhookUpdate.objects.filter(update_id=3).exists())
        self.assertNotIn(WEBHOOK_SECRET, response.content.decode())
        self.assertNotIn(WEBHOOK_SECRET, "\n".join(logs.output))

    def test_valid_challenge_links_group_once_from_expected_owner(self) -> None:
        token = start_link(club_id=self.club.pk, user=self.owner)
        client = self.bot_client()
        with patch("apps.telegram_integration.views.TelegramBotClient", return_value=client):
            response = self.post(self.connect_update(update_id=4, token=token))
        self.assertEqual(response.status_code, 204)
        group = ClubTelegramGroup.objects.get(club=self.club)
        self.assertEqual(group.telegram_chat_id, -100_940_001)
        self.assertTrue(group.bot_can_invite_members)
        self.assertIsNotNone(TelegramLinkChallenge.objects.get(token_hash__isnull=False).used_at)

    def test_expired_or_consumed_challenge_cannot_link(self) -> None:
        expired_token = start_link(club_id=self.club.pk, user=self.owner)
        challenge = TelegramLinkChallenge.objects.get(club=self.club)
        challenge.expires_at = timezone.now() - timedelta(seconds=1)
        challenge.save(update_fields=("expires_at", "updated_at"))
        client = self.bot_client()
        with patch("apps.telegram_integration.views.TelegramBotClient", return_value=client):
            self.assertEqual(self.post(self.connect_update(update_id=5, token=expired_token)).status_code, 204)
        self.assertFalse(ClubTelegramGroup.objects.exists())

        consumed_token = start_link(club_id=self.club.pk, user=self.owner)
        consumed = TelegramLinkChallenge.objects.get(
            token_hash__isnull=False, used_at__isnull=True
        )
        consumed.used_at = timezone.now()
        consumed.save(update_fields=("used_at", "updated_at"))
        with patch("apps.telegram_integration.views.TelegramBotClient", return_value=client):
            self.assertEqual(self.post(self.connect_update(update_id=6, token=consumed_token)).status_code, 204)
        self.assertFalse(ClubTelegramGroup.objects.exists())

    def test_wrong_owner_duplicate_chat_or_missing_bot_permission_do_not_link(self) -> None:
        wrong_owner = self.make_verified_user(940_003, "Wrong")
        token = start_link(club_id=self.club.pk, user=self.owner)
        client = self.bot_client()
        with patch("apps.telegram_integration.views.TelegramBotClient", return_value=client):
            self.assertEqual(
                self.post(
                    self.connect_update(
                        update_id=7, token=token, telegram_user_id=wrong_owner.telegram_user_id
                    )
                ).status_code,
                204,
            )
        self.assertFalse(ClubTelegramGroup.objects.exists())

        other_owner = self.make_verified_user(940_004, "Other")
        other_club = self.make_club(other_owner, "Other Club")
        ClubTelegramGroup.objects.create(
            club=other_club,
            telegram_chat_id=-100_940_001,
            status=TelegramGroupStatus.LINKED,
            bot_can_invite_members=True,
            linked_at=timezone.now(),
        )
        duplicate_token = start_link(club_id=self.club.pk, user=self.owner)
        with patch("apps.telegram_integration.views.TelegramBotClient", return_value=self.bot_client()):
            self.assertEqual(self.post(self.connect_update(update_id=8, token=duplicate_token)).status_code, 204)
        self.assertFalse(ClubTelegramGroup.objects.filter(club=self.club).exists())

        ClubTelegramGroup.objects.filter(club=other_club).delete()
        permission_token = start_link(club_id=self.club.pk, user=self.owner)
        no_permission = self.bot_client()
        no_permission.get_chat_member.return_value["can_invite_users"] = False
        with patch("apps.telegram_integration.views.TelegramBotClient", return_value=no_permission):
            self.assertEqual(self.post(self.connect_update(update_id=9, token=permission_token)).status_code, 204)
        self.assertFalse(ClubTelegramGroup.objects.filter(club=self.club).exists())

    def test_duplicate_update_does_not_duplicate_link(self) -> None:
        token = start_link(club_id=self.club.pk, user=self.owner)
        client = self.bot_client()
        update = self.connect_update(update_id=10, token=token)
        with patch("apps.telegram_integration.views.TelegramBotClient", return_value=client):
            self.assertEqual(self.post(update).status_code, 204)
            self.assertEqual(self.post(update).status_code, 204)
        self.assertEqual(ClubTelegramGroup.objects.filter(club=self.club).count(), 1)
        self.assertEqual(client.get_chat.call_count, 1)

    def link_group(self, *, chat_id: int = -100_940_001, club: Club | None = None) -> ClubTelegramGroup:
        return ClubTelegramGroup.objects.create(
            club=club or self.club,
            telegram_chat_id=chat_id,
            status=TelegramGroupStatus.LINKED,
            bot_can_invite_members=True,
            linked_at=timezone.now(),
        )

    def test_active_member_is_approved_and_duplicate_is_idempotent(self) -> None:
        self.link_group()
        provider = Mock()
        update = self.join_update(update_id=20, telegram_user_id=self.member.telegram_user_id)
        with patch("apps.telegram_integration.views.TelegramBotClient", return_value=provider):
            self.assertEqual(self.post(update).status_code, 204)
            self.assertEqual(self.post(update).status_code, 204)
        provider.approve_chat_join_request.assert_called_once_with(-100_940_001, self.member.telegram_user_id)
        provider.decline_chat_join_request.assert_not_called()

    def test_non_member_removed_unverified_and_suspended_users_are_declined(self) -> None:
        self.link_group()
        non_member = self.make_verified_user(940_010, "NonMember")
        removed = self.make_verified_user(940_011, "Removed")
        removed_membership = ClubMembership.objects.create(
            club=self.club,
            user=removed,
            role=MembershipRole.MEMBER,
            status=MembershipStatus.ACTIVE,
        )
        removed_membership.status = MembershipStatus.REMOVED
        removed_membership.left_at = timezone.now()
        removed_membership.save(update_fields=("status", "left_at", "updated_at"))
        unverified = User.objects.create_user(telegram_user_id=940_012)
        suspended = self.make_verified_user(940_013, "Suspended")
        ClubMembership.objects.create(
            club=self.club,
            user=suspended,
            role=MembershipRole.MEMBER,
            status=MembershipStatus.ACTIVE,
        )
        suspended.status = AccountStatus.SUSPENDED
        suspended.save(update_fields=("status", "updated_at"))

        provider = Mock()
        with patch("apps.telegram_integration.views.TelegramBotClient", return_value=provider):
            for offset, user in enumerate((non_member, removed, unverified, suspended), start=21):
                self.assertEqual(
                    self.post(self.join_update(update_id=offset, telegram_user_id=user.telegram_user_id)).status_code,
                    204,
                )
        self.assertEqual(provider.decline_chat_join_request.call_count, 4)
        provider.approve_chat_join_request.assert_not_called()

    def test_cross_club_paused_or_archived_club_never_authorizes(self) -> None:
        other_owner = self.make_verified_user(940_020, "Other")
        other_club = self.make_club(other_owner, "Other Group")
        self.link_group(club=other_club)
        provider = Mock()
        with patch("apps.telegram_integration.views.TelegramBotClient", return_value=provider):
            self.assertEqual(
                self.post(self.join_update(update_id=30, telegram_user_id=self.member.telegram_user_id)).status_code,
                204,
            )
        provider.decline_chat_join_request.assert_called_once()

        ClubTelegramGroup.objects.all().delete()
        self.link_group()
        self.club.status = ClubStatus.PAUSED
        self.club.save(update_fields=("status", "updated_at"))
        provider = Mock()
        with patch("apps.telegram_integration.views.TelegramBotClient", return_value=provider):
            self.assertEqual(
                self.post(self.join_update(update_id=31, telegram_user_id=self.member.telegram_user_id)).status_code,
                204,
            )
        provider.decline_chat_join_request.assert_called_once()
        provider.approve_chat_join_request.assert_not_called()

        self.club.status = ClubStatus.ARCHIVED
        self.club.save(update_fields=("status", "updated_at"))
        provider = Mock()
        with patch("apps.telegram_integration.views.TelegramBotClient", return_value=provider):
            self.assertEqual(
                self.post(self.join_update(update_id=32, telegram_user_id=self.member.telegram_user_id)).status_code,
                204,
            )
        provider.decline_chat_join_request.assert_called_once()
        provider.approve_chat_join_request.assert_not_called()

    def test_join_provider_failure_is_safe_and_retriable(self) -> None:
        self.link_group()
        provider = Mock()
        provider.approve_chat_join_request.side_effect = TelegramAPIError()
        with patch("apps.telegram_integration.views.TelegramBotClient", return_value=provider):
            response = self.post(self.join_update(update_id=40, telegram_user_id=self.member.telegram_user_id))
        self.assertEqual(response.status_code, 503)
        self.assertFalse(TelegramWebhookUpdate.objects.filter(update_id=40).exists())
        self.assertNotIn(str(self.member.telegram_user_id), response.content.decode())
