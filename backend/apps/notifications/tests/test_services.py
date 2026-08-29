from django.test import TestCase
from apps.identity.models import User
from apps.notifications.models import Notification, NotificationType
from apps.notifications.services import create_notification
from apps.notifications.services import deliver_notification
from apps.notifications.models import DeliveryStatus
from unittest.mock import Mock
from apps.clubs.models import Club, ClubStatus
from apps.clubs.services import moderate_club
from apps.lyceums.models import Lyceum, StudentRecord
from django.utils import timezone

class NotificationServiceTests(TestCase):
    def test_dedupe_key_is_idempotent(self):
        user = User.objects.create_user(telegram_user_id=900001)
        a = create_notification(recipient=user, type=NotificationType.CLUB_APPROVED, title="Approved", body="ok", dedupe_key="event-1")
        b = create_notification(recipient=user, type=NotificationType.CLUB_APPROVED, title="Approved", body="ok", dedupe_key="event-1")
        self.assertEqual(a.pk, b.pk)
        self.assertEqual(Notification.objects.count(), 1)

    def test_successful_telegram_delivery_marks_sent(self):
        user = User.objects.create_user(telegram_user_id=900003)
        notification = Notification.objects.create(recipient=user, type=NotificationType.CLUB_APPROVED, title="Approved", body="ok")
        client = Mock()
        self.assertTrue(deliver_notification(notification, client))
        notification.refresh_from_db()
        self.assertEqual(notification.delivery_status, DeliveryStatus.SENT)
        client.send_message.assert_called_once_with(900003, "Approved\n\nok")

    def test_failed_delivery_is_recorded_without_raising(self):
        user = User.objects.create_user(telegram_user_id=900004)
        notification = Notification.objects.create(recipient=user, type=NotificationType.CLUB_APPROVED, title="Approved", body="ok")
        client = Mock(); client.send_message.side_effect = RuntimeError("network down")
        self.assertFalse(deliver_notification(notification, client))
        notification.refresh_from_db()
        self.assertEqual(notification.delivery_status, DeliveryStatus.FAILED)
        self.assertEqual(notification.delivery_attempts, 1)

    def test_delivery_failure_does_not_undo_club_moderation(self):
        lyceum = Lyceum.objects.create(name="Notify Lyceum", code="notify")
        owner = User.objects.create_user(telegram_user_id=900005)
        StudentRecord.objects.create(lyceum=lyceum, first_name="A", last_name="B", group_name="10-A", verified_user=owner, verified_at=timezone.now())
        club = Club.objects.create(lyceum=lyceum, owner=owner, name="Club", short_description="s", description="d", category="OTHER")
        moderate_club(club_id=club.pk, action="approve")
        notification = Notification.objects.get(recipient=owner, type=NotificationType.CLUB_APPROVED)
        client = Mock(); client.send_message.side_effect = RuntimeError("offline")
        deliver_notification(notification, client)
        club.refresh_from_db()
        self.assertEqual(club.status, ClubStatus.ACTIVE)
