from unittest.mock import Mock
from django.test import TestCase
from django.utils import timezone
from apps.identity.models import User
from apps.lyceums.models import Lyceum, StudentRecord
from apps.clubs.models import Club, ClubStatus, ClubMembership, MembershipRole, MembershipStatus
from apps.clubs.services import moderate_club
from apps.telegram_integration.services import start_link, confirm_link, create_member_invite
from apps.telegram_integration.models import ClubTelegramGroup
from apps.telegram_integration.exceptions import LinkChallengeError

class TelegramIntegrationTests(TestCase):
    def test_unverified_user_cannot_start_link(self):
        user = User.objects.create_user(telegram_user_id=900002)
        with self.assertRaises(Exception):
            start_link(club_id="00000000-0000-0000-0000-000000000000", user=user)

    def setUp(self):
        self.lyceum = Lyceum.objects.create(name="Test Lyceum", code="tg-test")
        self.owner = User.objects.create_user(telegram_user_id=900010)
        StudentRecord.objects.create(lyceum=self.lyceum, first_name="A", last_name="B", group_name="10-A", verified_user=self.owner, verified_at=timezone.now())
        self.club = Club.objects.create(lyceum=self.lyceum, owner=self.owner, name="Club", short_description="Short", description="Description", category="OTHER", status=ClubStatus.ACTIVE)

    def test_link_requires_bot_invite_permission(self):
        token = start_link(club_id=self.club.pk, user=self.owner)
        with self.assertRaises(LinkChallengeError):
            confirm_link(token=token, telegram_chat_id=-1001, can_invite_members=False)
        self.assertFalse(ClubTelegramGroup.objects.exists())

    def test_owner_can_link_and_unlink_only_their_group(self):
        token = start_link(club_id=self.club.pk, user=self.owner)
        group = confirm_link(token=token, telegram_chat_id=-1002, title="Test group", can_invite_members=True)
        self.assertEqual(group.telegram_chat_id, -1002)

    def test_duplicate_chat_linkage_is_rejected(self):
        token = start_link(club_id=self.club.pk, user=self.owner)
        confirm_link(token=token, telegram_chat_id=-1003, can_invite_members=True)
        other = User.objects.create_user(telegram_user_id=900011)
        StudentRecord.objects.create(lyceum=self.lyceum, first_name="C", last_name="D", group_name="10-B", verified_user=other, verified_at=timezone.now())
        other_club = Club.objects.create(lyceum=self.lyceum, owner=other, name="Other", short_description="s", description="d", category="OTHER", status=ClubStatus.ACTIVE)
        token = start_link(club_id=other_club.pk, user=other)
        with self.assertRaises(LinkChallengeError):
            confirm_link(token=token, telegram_chat_id=-1003, can_invite_members=True)

    def test_invite_uses_mocked_client_and_member_scope(self):
        ClubMembership.objects.create(club=self.club, user=self.owner, role=MembershipRole.OWNER, status=MembershipStatus.ACTIVE)
        client = Mock(); client.create_invite_link.return_value = {"invite_link": "https://t.me/+one-use"}
        from apps.telegram_integration.services import create_member_invite
        token = start_link(club_id=self.club.pk, user=self.owner)
        confirm_link(token=token, telegram_chat_id=-1004, can_invite_members=True)
        result = create_member_invite(club_id=self.club.pk, user=self.owner, client=client)
        self.assertEqual(result, "https://t.me/+one-use")
        kwargs = client.create_invite_link.call_args.kwargs
        self.assertTrue(kwargs["creates_join_request"])
        self.assertNotIn("member_limit", kwargs)
        self.assertIn("expire_date", kwargs)

    def test_cross_lyceum_user_cannot_obtain_invite(self):
        from rest_framework.exceptions import NotFound
        other_lyceum = Lyceum.objects.create(name="Other Lyceum", code="tg-other")
        user = User.objects.create_user(telegram_user_id=900012)
        StudentRecord.objects.create(lyceum=other_lyceum, first_name="E", last_name="F", group_name="10-C", verified_user=user, verified_at=timezone.now())
        client = Mock()
        from apps.telegram_integration.services import create_member_invite
        with self.assertRaises(NotFound):
            create_member_invite(club_id=self.club.pk, user=user, client=client)
        client.create_invite_link.assert_not_called()

    def test_cross_lyceum_owner_cannot_manage_foreign_club_group(self):
        from rest_framework.exceptions import PermissionDenied
        other_lyceum = Lyceum.objects.create(name="Foreign Lyceum", code="tg-foreign")
        foreign = User.objects.create_user(telegram_user_id=900013)
        StudentRecord.objects.create(lyceum=other_lyceum, first_name="G", last_name="H", group_name="10-D", verified_user=foreign, verified_at=timezone.now())
        foreign_club = Club.objects.create(lyceum=other_lyceum, owner=foreign, name="Foreign", short_description="s", description="d", category="OTHER", status=ClubStatus.ACTIVE)
        with self.assertRaises(PermissionDenied):
            start_link(club_id=foreign_club.pk, user=self.owner)

